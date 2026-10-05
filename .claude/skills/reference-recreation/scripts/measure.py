#!/usr/bin/env python3
"""Element-level measuring of a reference video -> motion-spec.json (+ a short spec-summary.md). Deterministic, no model calls.

  python3 measure.py REF.mp4 --out DIR [--analysis reference-style.json] [--frames A:B] [--ignore-box x0,y0,x1,y1 ...] [--cursor hand|none] [--learn-cursor FRAME,X,Y,NAME]

What it measures per segment (a segment = between two hard cuts): flat UI regions (cards, pills, circles, bands, buttons, photo windows' frames) with box, colour, corner radius per frame;
photo-like regions (textured / gradient / glow, non-flat); dark ink lines (text, digits, icons) with typing cadence; the pointer sprite (tip, scale, presses); keyframes with named eases
for every box coordinate. What it does NOT model is listed under `unmodelled` (non-flat backgrounds, globes, 3D type, blurred effects): handle those by hand.
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from refkit import video, components as comp, cursor as cur, ease  # noqa: E402


def detect_cuts(path, info, extra=()):
    gray, border = video.small_series(path, info)
    d = np.abs(np.diff(gray, axis=0)).mean(axis=(1, 2))
    cuts = set(int(c) for c in extra)
    for i in range(1, len(d) - 1):
        nb = float(np.median(np.r_[d[max(0, i - 2):i], d[i + 1:i + 3]]))
        if d[i] > 8 and d[i] > 3 * max(nb, 0.3):
            cuts.add(i + 1)
    out = []
    for c in sorted(cuts):
        if c > 0 and (not out or c - out[-1] >= 4):
            out.append(c)
    return out


def role_of(w, h, fill, r):
    big_r = r is not None and r >= 0.4 * min(w, h)
    square = abs(w - h) / max(w, h) < 0.14
    if square and (big_r if r is not None else 0.5 < fill < 0.9) and max(w, h) < 400:
        return "circle"
    if w / h > 2.4 and h < 130 and (big_r or r is None):
        return "pill"
    if min(w, h) < 14:
        return "line"
    if w > 150 and h > 150:
        return "card"
    return "box"


def series_keys(frames, vals):
    k, err = ease.keyframes(frames, vals)
    return dict(keys=k, max_err=err)


def build_track(t, W, H, seg_id, tid, bg):
    ff, bb = comp.fill_gaps(t["frames"], t["boxes"])
    B = np.array(bb, float)
    cx, cy = (B[:, 0] + B[:, 2]) / 2, (B[:, 1] + B[:, 3]) / 2
    w, h = B[:, 2] - B[:, 0], B[:, 3] - B[:, 1]
    clipped = [bool(b[0] <= 0 or b[1] <= 0 or b[2] >= W or b[3] >= H) for b in bb]
    d = dict(id=tid, cls=t["cls"], segment=seg_id, frames=[ff[0], ff[-1]], observed=len(t["frames"]),
             boxes=[[int(v) for v in b] for b in bb], clipped_frames=[f for f, c in zip(ff, clipped) if c][:200])
    d["keys"] = dict(cx=series_keys(ff, cx), cy=series_keys(ff, cy), w=series_keys(ff, w), h=series_keys(ff, h))
    mw, mh = float(np.median(w)), float(np.median(h))
    if t["cls"] == "flat":
        cols = [c for c in t["colors"] if c is not None]
        d["color"] = "#%02X%02X%02X" % tuple(int(v) for v in np.median(np.array(cols), axis=0)) if cols else None
        ars = np.array(t["areas"], float)
        fill = float(np.median(ars / np.maximum(1.0, (np.array([b[2] - b[0] for b in t["boxes"]]) * np.array([b[3] - b[1] for b in t["boxes"]])))))
        rr = t.get("radii") or []
        rmed = float(np.median(rr)) if rr else None
        d["role"] = role_of(mw, mh, fill, rmed)
        d["fill"] = round(fill, 2)
        d["radius"] = round(min(mw, mh) / 2, 1) if d["role"] in ("circle", "pill") else (round(rmed, 1) if rmed is not None else None)
        if d["color"] and len(cols) > 4:
            c0 = np.array(cols[0], float); bgv = np.array(bg, float)
            d["opacity_track"] = None
    elif t["cls"] == "photo":
        d["role"] = "photo"
    else:
        d["role"] = "text"
        right = B[:, 2]
        steps = [int(ff[i]) for i in range(1, len(ff)) if right[i] - right[i - 1] >= 2.0 and abs(B[i, 0] - B[i - 1, 0]) <= 1.5]
        if len(steps) >= 3:
            d["typing_frames"] = ([int(ff[0])] if (B[0, 2] - B[0, 0]) <= 1.6 * (B[0, 3] - B[0, 1]) else []) + steps
    return d


def containment(tracks):
    """parent = the smallest flat/photo track whose box contains the child's box for >= 80% of their shared frames."""
    idx = {t["id"]: t for t in tracks}
    for c in tracks:
        best, barea = None, 1e18
        cf = dict(zip(range(c["frames"][0], c["frames"][1] + 1), c["boxes"]))
        for p in tracks:
            if p is c or p["cls"] not in ("flat", "photo") or p["segment"] != c["segment"]:
                continue
            pf = dict(zip(range(p["frames"][0], p["frames"][1] + 1), p["boxes"]))
            shared = [f for f in cf if f in pf]
            if len(shared) < 3:
                continue
            ins = 0
            for f in shared:
                a, b = cf[f], pf[f]
                if a[0] >= b[0] - 2 and a[1] >= b[1] - 2 and a[2] <= b[2] + 2 and a[3] <= b[3] + 2:
                    ins += 1
            area = (pf[shared[0]][2] - pf[shared[0]][0]) * (pf[shared[0]][3] - pf[shared[0]][1])
            if ins >= 0.8 * len(shared) and area < barea and (c["cls"] != "flat" or area > (cf[shared[0]][2] - cf[shared[0]][0]) * (cf[shared[0]][3] - cf[shared[0]][1]) * 1.15):
                best, barea = p["id"], area
        c["parent"] = best



def text_pass(a, spec, info, ign):
    """OCR text, ink colour and an estimated font size for every ink track (macOS Vision via ../bin/ocr; skipped when the binary is missing)."""
    import subprocess
    import tempfile
    from PIL import Image
    ocr_bin = os.path.join(HERE, "..", "bin", "ocr")
    ink = [t for t in spec["tracks"] if t["cls"] == "ink"]
    if not ink:
        return
    want = {}
    for t in ink:
        ws = [b[2] - b[0] for b in t["boxes"]]
        f_best = t["frames"][0] + int(np.argmax(ws))
        want.setdefault(f_best, []).append(t)
    tmp = tempfile.mkdtemp(prefix="msocr_")
    crops = []
    for f, fr in video.iter_frames(a.video, min(want), max(want), info=info):
        if f not in want:
            continue
        g = comp.gray(fr)
        for t in want[f]:
            b = t["boxes"][f - t["frames"][0]]
            x0, y0, x1, y1 = max(0, b[0] - 6), max(0, b[1] - 6), min(fr.shape[1], b[2] + 6), min(fr.shape[0], b[3] + 6)
            sub, gs = fr[y0:y1, x0:x1], g[y0:y1, x0:x1]
            m = gs < 120
            t["ink_color"] = "#%02X%02X%02X" % tuple(int(v) for v in np.median(sub[m], axis=0)) if m.sum() >= 6 else None
            hh = b[3] - b[1]
            t["_crop"] = (x0, y0, f)
            im = Image.fromarray(sub).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.LANCZOS)
            pth = os.path.join(tmp, "%s.png" % t["id"])
            im.save(pth)
            crops.append((t, pth, hh))
    if os.path.exists(ocr_bin) and crops:
        res = []
        for i in range(0, len(crops), 60):
            r = subprocess.run([ocr_bin] + [c[1] for c in crops[i:i + 60]], capture_output=True, text=True)
            try:
                res += json.loads(r.stdout)
            except Exception:
                res += [dict(lines=[]) for _ in crops[i:i + 60]]
        for (t, pth, hh), r in zip(crops, res):
            lines = sorted([l for l in r.get("lines", []) if l.get("conf", 0) >= 0.3], key=lambda l: l["y"])
            x0, y0, f = t["_crop"]
            if lines:
                t["text"] = " ".join(l["text"] for l in lines)
                l0 = lines[0]
                cw, ch = (t["boxes"][f - t["frames"][0]][2] - t["boxes"][f - t["frames"][0]][0] + 12), (t["boxes"][f - t["frames"][0]][3] - t["boxes"][f - t["frames"][0]][1] + 12)
                t["text_box"] = [int(x0 + l0["x"] * cw), int(y0 + l0["y"] * ch), int(x0 + (l0["x"] + l0["w"]) * cw), int(y0 + (l0["y"] + l0["h"]) * ch)]
                desc = any(c in t["text"] for c in "gjpqy,;")
                t["font_px_est"] = round(hh / (0.93 if desc else 0.72), 1)
            t.pop("_crop", None)
    for t in ink:
        t.pop("_crop", None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--analysis")
    ap.add_argument("--frames")
    ap.add_argument("--ignore-box", action="append", default=[])
    ap.add_argument("--cursor", default=None, help="sprite name from refkit/sprites (default: the first one), or 'none'")
    ap.add_argument("--learn-cursor", help="FRAME,X,Y,NAME: cut a new pointer sprite from that frame (tip at X,Y) before measuring")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    info = video.probe(a.video)
    W, H = info["width"], info["height"]
    if a.learn_cursor:
        fr_, x_, y_, nm = a.learn_cursor.split(",")
        cur.learn_sprite(video.read_frame(a.video, int(fr_), info), int(x_), int(y_), nm)
        print("learned sprite", nm)
    f0, f1 = (0, info["frames"] - 1)
    if a.frames:
        f0, f1 = [int(v) for v in a.frames.split(":")]
    ign = [tuple(int(v) for v in b.split(",")) for b in a.ignore_box]
    extra = []
    if a.analysis and os.path.exists(a.analysis):
        extra = [c["frame"] for c in json.load(open(a.analysis)).get("cuts", [])]
    cuts = [c for c in detect_cuts(a.video, info, extra) if f0 < c <= f1]
    bounds = [f0] + cuts + [f1 + 1]
    segs = [(bounds[i], bounds[i + 1] - 1) for i in range(len(bounds) - 1)]
    seg_of = {}
    for si, (s0, s1) in enumerate(segs):
        for f in range(s0, s1 + 1):
            seg_of[f] = si
    names = cur.available()
    sprite_name = None if a.cursor == "none" else (a.cursor or (names[0] if names else None))
    ctrack = cur.CursorTracker(cur.load_sprite(sprite_name)) if sprite_name else None

    from collections import deque
    ghist = deque(maxlen=6)
    trackers = {}
    seg_info = {si: dict(frames=[s0, s1], bg=[], photo_area=[]) for si, (s0, s1) in enumerate(segs)}
    radii = {}
    for f, fr in video.iter_frames(a.video, f0, f1, info=info):
        si = seg_of[f]
        if si not in trackers:
            trackers[si] = comp.Tracker()
        bg = comp.frame_bg(fr)
        seg_info[si]["bg"].append(bg)
        work = fr
        for (x0, y0, x1, y1) in ign:
            if work is fr:
                work = fr.copy()
            work[max(0, y0):y1, max(0, x0):x1] = bg
        g = comp.gray(work)
        cb = None
        if ctrack is not None:
            res = ctrack.update(f, g)
            if res and ctrack.fresh:                       # acquired just now: walk back over the frames the coarse scan skipped
                nxt = res
                for pf, pg in reversed(list(ghist)):
                    nxt = ctrack.back_fill(pf, pg, nxt)
                    if nxt is None:
                        break
            ghist.append((f, g))
            cb = ctrack.bbox(res) if res else None
            if cb is not None:
                if work is fr:
                    work = fr.copy()
                work[max(0, cb[1]):cb[3], max(0, cb[0]):cb[2]] = bg
                g = comp.gray(work)
        flat, union = comp.detect_regions(work, bg)
        ph, _ = comp.detect_photo(work, g, union, bg)
        ink = comp.detect_ink(g, [d["box"] for d in ph] + ([cb] if cb else []))
        seg_info[si]["photo_area"].append(sum(d["area"] for d in ph) / float(W * H))
        trackers[si].update(f, flat + ph + ink)
        for d in flat:
            if d.get("r") is not None:
                radii.setdefault((si, id(None)), [])
        if f % 60 == 0:
            print("  frame", f, "segment", si, "flat", len(flat), "photo", len(ph), "ink", len(ink), flush=True)
    if ctrack is not None:
        ctrack.clean()
    tracks = []
    tid = 0
    for si, tr in sorted(trackers.items()):
        bg = np.median(np.array(seg_info[si]["bg"]), axis=0)
        for t in tr.finish(min_len=3):
            tid += 1
            tracks.append(build_track(t, W, H, si, "t%03d" % tid, bg))
    containment(tracks)
    # (text pass runs after the spec skeleton exists)
    by_id = {t["id"]: t for t in tracks}
    for t in tracks:                                    # smooth patches inside a photo (sky, glow) are texture of the photo, not UI
        p_ = by_id.get(t.get("parent"))
        if t["cls"] == "flat" and p_ is not None and p_["cls"] == "photo":
            b, pb = t["boxes"][0], p_["boxes"][0]
            if (b[2] - b[0]) * (b[3] - b[1]) < 0.25 * max(1, (pb[2] - pb[0]) * (pb[3] - pb[1])):
                t["junk"] = True
    spec = dict(schema="motion-spec/1", source=dict(path=os.path.abspath(a.video), width=W, height=H, fps=info["fps"], frames=info["frames"]),
                measured=[f0, f1], segments=[], cursor=None, events=[], tracks=tracks)
    for si, (s0, s1) in enumerate(segs):
        bgs = np.array(seg_info[si]["bg"]) if seg_info[si]["bg"] else np.zeros((1, 3))
        pa = seg_info[si]["photo_area"]
        spec["segments"].append(dict(index=si, frames=[s0, s1], bg="#%02X%02X%02X" % tuple(int(v) for v in np.median(bgs, axis=0)), bg_flat=bool((np.abs(bgs - np.median(bgs, axis=0)).max(axis=1) < 6).mean() >= 0.9),
                                     photo_area_share=round(float(np.mean(pa)) if pa else 0.0, 3)))
        if si > 0:
            spec["events"].append(dict(frame=s0, kind="cut"))
    if ctrack is not None and ctrack.track:
        spec["cursor"] = dict(sprite=sprite_name, track=[list(t) for t in ctrack.track], presses=ctrack.presses())
        for p in spec["cursor"]["presses"]:
            spec["events"].append(dict(frame=p[0], kind="press", to=p[1]))
        tr_ = ctrack.track
        spec["cursor"]["keys"] = dict(x=series_keys([t[0] for t in tr_], [t[1] for t in tr_]), y=series_keys([t[0] for t in tr_], [t[2] for t in tr_]), scale=series_keys([t[0] for t in tr_], [t[3] for t in tr_]))
    for t in tracks:
        if t.get("typing_frames"):
            spec["events"].append(dict(frame=t["typing_frames"][0], kind="typing", track=t["id"], frames=t["typing_frames"]))
        if t["cls"] in ("flat", "photo") and t["frames"][0] > f0 and not (t["frames"][0] in [s[0] for s in segs]):
            x0, y0, x1, y1 = t["boxes"][0]
            if (x1 - x0) * (y1 - y0) > 6000:
                spec["events"].append(dict(frame=t["frames"][0], kind="appear", track=t["id"], role=t["role"]))
    spec["events"].sort(key=lambda e: e["frame"])
    if os.path.exists(os.path.join(HERE, "..", "bin", "ocr")) and not os.environ.get("MEASURE_NO_OCR"):
        text_pass(a, spec, info, ign)
    json.dump(spec, open(os.path.join(a.out, "motion-spec.json"), "w"))
    # short summary for the model: numbers only
    lines = ["# spec-summary (measure.py)", "", "source %s %dx%d %.2f fps, frames measured %d-%d" % (os.path.basename(a.video), W, H, info["fps"], f0, f1), ""]
    for sg in spec["segments"]:
        ts = [t for t in tracks if t["segment"] == sg["index"]]
        lines.append("segment %d  f%d-%d  bg %s%s  photo-like area %.0f%%%s" % (sg["index"], sg["frames"][0], sg["frames"][1], sg["bg"], "" if sg["bg_flat"] else " (NOT flat)", 100 * sg["photo_area_share"],
                                                                                 "  -> mostly non-flat: hero/type/footage, not modelled" if sg["photo_area_share"] > 0.35 or not sg["bg_flat"] else ""))
        for cls in ("flat", "photo", "text"):
            tt = sorted([t for t in ts if t["role" if cls != "flat" else "cls"] in ((cls,) if cls == "flat" else (cls,))] if cls == "flat" else [t for t in ts if t["role"] == cls], key=lambda t: -(t["boxes"][0][2] - t["boxes"][0][0]) * (t["boxes"][0][3] - t["boxes"][0][1]))
            if tt:
                roles = {}
                for t in tt:
                    roles[t.get("role", cls)] = roles.get(t.get("role", cls), 0) + 1
                lines.append("   %-6s %3d tracks  %s" % (cls, len(tt), ", ".join("%s x%d" % (k, v) for k, v in sorted(roles.items()))))
    if spec["cursor"]:
        c = spec["cursor"]["track"]
        lines.append("")
        lines.append("cursor '%s': %d frames seen (f%d-f%d), presses %s" % (sprite_name, len(c), c[0][0], c[-1][0], spec["cursor"]["presses"]))
    lines.append("typing events: %s" % [(e["frame"], len(e["frames"])) for e in spec["events"] if e["kind"] == "typing"])
    lines.append("hard cuts: %s" % [e["frame"] for e in spec["events"] if e["kind"] == "cut"])
    open(os.path.join(a.out, "spec-summary.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("wrote", os.path.join(a.out, "motion-spec.json"))


if __name__ == "__main__":
    main()
