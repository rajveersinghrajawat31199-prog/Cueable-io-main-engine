#!/usr/bin/env python3
"""Element-level fidelity check: measure a RENDER with the same tool as the reference and diff the two motion specs.

  python3 fidelity.py --ref REF-motion-spec.json --render render.mp4 --out DIR [--warp 0:0,90:90,...] [--render-spec existing.json] [--frames A:B] [--crops 6]

For every reference element (flat region, photo-like region, text line) it finds the render element with the best box overlap over the shared frames (through the beat warp)
and reports centre error, size error, lifetime offset and the integer frame lag that would fit best; it lists elements MISSING in the render and EXTRA ones; compares the pointer path,
presses and typing frames. Output: fidelity.json, a printed failure list (worst first), fidelity-crops.png (reference | render crops of the worst elements).
Brand changes (colours, fonts, photos) do not matter: matching is by geometry and timing only.
"""
import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from refkit import video  # noqa: E402


def parse_warp(s):
    if not s:
        return None
    if os.path.exists(s):
        return json.load(open(s))
    return [[float(a) for a in p.split(":")] for p in s.split(",")]


def make_map(pts):
    if not pts:
        return lambda f: float(f)
    xs = np.array([p[0] for p in pts], float)
    ys = np.array([p[1] for p in pts], float)
    return lambda f: float(np.interp(f, xs, ys, left=ys[0] + (f - xs[0]), right=ys[-1] + (f - xs[-1])))


def box_dict(t):
    f0 = t["frames"][0]
    return {f0 + i: b for i, b in enumerate(t["boxes"])}


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def center(b):
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


def compare(rt, qt, fmap, lag=0):
    """rt: reference track, qt: render track. Returns metrics over shared frames (render frame = round(fmap(f)) + lag)."""
    rb, qb = box_dict(rt), box_dict(qt)
    ious, cerr, serr = [], [], []
    for f, b in rb.items():
        g = int(round(fmap(f))) + lag
        if g in qb:
            q = qb[g]
            ious.append(iou(b, q))
            (cx, cy), (qx, qy) = center(b), center(q)
            cerr.append(math.hypot(cx - qx, cy - qy))
            w, h, qw, qh = b[2] - b[0], b[3] - b[1], q[2] - q[0], q[3] - q[1]
            serr.append(max(abs(math.log(max(qw, 1) / max(w, 1))), abs(math.log(max(qh, 1) / max(h, 1)))))
    return ious, cerr, serr


def area0(t):
    b = t["boxes"][0]
    return (b[2] - b[0]) * (b[3] - b[1])


def significant(t, min_area=2500, min_len=12):
    return not t.get("junk") and t["cls"] in ("flat", "photo", "ink") and (t["frames"][1] - t["frames"][0] + 1 >= min_len) and (max((b[2] - b[0]) * (b[3] - b[1]) for b in t["boxes"][::max(1, len(t["boxes"]) // 8)]) >= (min_area if t["cls"] != "ink" else 150))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--render", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--warp")
    ap.add_argument("--render-spec")
    ap.add_argument("--frames", help="reference frame range A:B to check")
    ap.add_argument("--ignore-box", action="append", default=[])
    ap.add_argument("--crops", type=int, default=6)
    ap.add_argument("--tol-px", type=float, default=5.0)
    ap.add_argument("--tol-size", type=float, default=0.06)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ref = json.load(open(a.ref))
    if a.render_spec:
        ren = json.load(open(a.render_spec))
    else:
        cmd = [sys.executable, os.path.join(HERE, "measure.py"), a.render, "--out", os.path.join(a.out, "render")] + sum([["--ignore-box", b] for b in a.ignore_box], [])
        subprocess.run(cmd, check=True, capture_output=True)
        ren = json.load(open(os.path.join(a.out, "render", "motion-spec.json")))
    fmap = make_map(parse_warp(a.warp))
    r0, r1 = (ref["measured"][0], ref["measured"][1])
    if a.frames:
        r0, r1 = [int(v) for v in a.frames.split(":")]
    rts = [t for t in ref["tracks"] if significant(t) and t["frames"][1] >= r0 and t["frames"][0] <= r1]
    qts = [t for t in ren["tracks"] if significant(t)]
    compat = lambda x, y: x["cls"] == y["cls"] or {x["cls"], y["cls"]} <= {"flat", "photo"}
    # greedy best match by mean IoU over shared frames
    cand = []
    for i, rt in enumerate(rts):
        for j, qt in enumerate(qts):
            if not compat(rt, qt):
                continue
            ious, _, _ = compare(rt, qt, fmap)
            if len(ious) >= 4:
                cand.append((float(np.mean(ious)) * min(1.0, len(ious) / 12.0), i, j))
    cand.sort(reverse=True)
    used_r, used_q, pairs = set(), set(), []
    for s, i, j in cand:
        if s < 0.2 or i in used_r or j in used_q:
            continue
        used_r.add(i)
        used_q.add(j)
        pairs.append((i, j))
    rows = []
    for i, j in pairs:
        rt, qt = rts[i], qts[j]
        ious, cerr, serr = compare(rt, qt, fmap)
        best_lag, best_c = 0, float(np.mean(cerr))
        for lg in range(-6, 7):
            _, ce, _ = compare(rt, qt, fmap, lg)
            if len(ce) >= 4 and float(np.mean(ce)) < best_c - 0.75:
                best_lag, best_c = lg, float(np.mean(ce))
        life = (int(round(fmap(rt["frames"][0]))) - qt["frames"][0], int(round(fmap(rt["frames"][1]))) - qt["frames"][1])
        row = dict(ref=rt["id"], render=qt["id"], cls=rt["cls"], role=rt.get("role"), frames=rt["frames"], iou=round(float(np.mean(ious)), 2), center_err_mean=round(float(np.mean(cerr)), 1),
                   center_err_max=round(float(np.max(cerr)), 1), size_err_pct=round(100 * float(np.mean(serr)), 1), size_err_max_pct=round(100 * float(np.max(serr)), 1),
                   best_lag=best_lag, lifetime_offset=list(life), shared=len(ious))
        row["flags"] = [f for f, bad in (("position", row["center_err_mean"] > a.tol_px or row["center_err_max"] > 3 * a.tol_px), ("size", row["size_err_pct"] > 100 * a.tol_size),
                                          ("timing", row["best_lag"] != 0), ("lifetime", max(abs(life[0]), abs(life[1])) > 3)) if bad]
        row["severity"] = round(row["center_err_mean"] / a.tol_px + row["size_err_pct"] / (100 * a.tol_size) + abs(best_lag) * 0.7 + (1.0 if "lifetime" in row["flags"] else 0.0), 2)
        rows.append(row)
    missing = [dict(ref=rts[i]["id"], cls=rts[i]["cls"], role=rts[i].get("role"), frames=rts[i]["frames"], box=rts[i]["boxes"][len(rts[i]["boxes"]) // 2]) for i in range(len(rts)) if i not in used_r]
    extra = [dict(render=qts[j]["id"], cls=qts[j]["cls"], role=qts[j].get("role"), frames=qts[j]["frames"], box=qts[j]["boxes"][len(qts[j]["boxes"]) // 2]) for j in range(len(qts)) if j not in used_q]
    # pointer
    cur = None
    if ref.get("cursor") and ren.get("cursor"):
        rc = {int(t[0]): t for t in ref["cursor"]["track"]}
        qc = {int(t[0]): t for t in ren["cursor"]["track"]}
        err, serr = [], []
        for f, t in rc.items():
            g = int(round(fmap(f)))
            if g in qc:
                err.append(math.hypot(t[1] - qc[g][1], t[2] - qc[g][2]))
                serr.append(abs(t[3] / max(qc[g][3], 1e-3) - 1))
        iv = lambda d: [[a_, b_] for a_, b_ in _intervals(sorted(d))]
        cur = dict(ref_visible=iv(rc), render_visible=iv(qc), shared=len(err), tip_err_median=round(float(np.median(err)), 1) if err else None, tip_err_p90=round(float(np.percentile(err, 90)), 1) if err else None,
                   scale_err_median_pct=round(100 * float(np.median(serr)), 1) if serr else None, ref_presses=ref["cursor"].get("presses"), render_presses=ren["cursor"].get("presses"))
    elif ref.get("cursor") and not ren.get("cursor"):
        cur = dict(note="render has no pointer", ref_visible=_intervals(sorted(int(t[0]) for t in ref["cursor"]["track"])))
    typing = []
    ev_r = [e for e in ref["events"] if e["kind"] == "typing"]
    ev_q = [e for e in ren["events"] if e["kind"] == "typing"]
    for e in ev_r:
        best = None
        for q in ev_q:
            d = abs(int(round(fmap(e["frames"][0]))) - q["frames"][0])
            if best is None or d < best[0]:
                best = (d, q)
        if best:
            q = best[1]
            n = min(len(e["frames"]), len(q["frames"]))
            offs = [int(round(fmap(e["frames"][k]))) - q["frames"][k] for k in range(n)]
            typing.append(dict(ref_chars=len(e["frames"]), render_chars=len(q["frames"]), offset_median=int(np.median(offs)), offset_max=int(np.max(np.abs(offs)))))
        else:
            typing.append(dict(ref_chars=len(e["frames"]), render_chars=0))
    rows.sort(key=lambda r: -r["severity"])
    out = dict(ref=os.path.abspath(a.ref), render=os.path.abspath(a.render), matched=rows, missing=missing, extra=extra, cursor=cur, typing=typing,
               summary=dict(ref_elements=len(rts), matched=len(rows), missing=len(missing), extra=len(extra), flagged=sum(1 for r in rows if r["flags"]),
                            center_err_median=round(float(np.median([r["center_err_mean"] for r in rows])), 1) if rows else None))
    json.dump(out, open(os.path.join(a.out, "fidelity.json"), "w"), indent=1)
    print("FIDELITY  reference elements %d | matched %d | missing %d | extra %d | flagged %d | median centre error %s px" % (len(rts), len(rows), len(missing), len(extra), out["summary"]["flagged"], out["summary"]["center_err_median"]))
    for r in rows[:14]:
        if r["flags"]:
            print("  %-5s %-6s %-6s f%3d-%3d  %s | centre %.1f/%.1f px, size %.1f%%, lag %+d, life %s" % (r["ref"], r["cls"], r["role"], r["frames"][0], r["frames"][1], "+".join(r["flags"]), r["center_err_mean"], r["center_err_max"], r["size_err_pct"], r["best_lag"], r["lifetime_offset"]))
    for m in sorted(missing, key=lambda m: -(m["box"][2] - m["box"][0]) * (m["box"][3] - m["box"][1]))[:8]:
        print("  MISSING %-5s %-6s %-6s f%3d-%3d box %s" % (m["ref"], m["cls"], m["role"], m["frames"][0], m["frames"][1], m["box"]))
    for m in sorted(extra, key=lambda m: -(m["box"][2] - m["box"][0]) * (m["box"][3] - m["box"][1]))[:5]:
        print("  EXTRA   %-5s %-6s %-6s f%3d-%3d box %s" % (m["render"], m["cls"], m["role"], m["frames"][0], m["frames"][1], m["box"]))
    if cur:
        print("  pointer:", {k: v for k, v in cur.items() if k in ("ref_visible", "render_visible", "tip_err_median", "tip_err_p90", "scale_err_median_pct", "ref_presses", "render_presses", "note")})
    if typing:
        print("  typing:", typing)
    if a.crops:
        crops(a, ref, ren, rows, missing, fmap, out)


def _intervals(fr):
    iv, s0, p = [], None, None
    for f in fr:
        if s0 is None:
            s0 = p = f
        elif f - p > 3:
            iv.append((s0, p))
            s0 = p = f
        else:
            p = f
    if s0 is not None:
        iv.append((s0, p))
    return iv


def crops(a, ref, ren, rows, missing, fmap, out):
    from PIL import Image, ImageDraw
    tracks = {t["id"]: t for t in ref["tracks"]}
    rtracks = {t["id"]: t for t in ren["tracks"]}
    items = []
    for r in rows:
        if r["flags"]:
            rt, qt = tracks[r["ref"]], rtracks[r["render"]]
            rb, qb = box_dict(rt), box_dict(qt)
            worst, wf = -1, None
            for f, b in rb.items():
                g = int(round(fmap(f)))
                if g in qb:
                    e = math.hypot(center(b)[0] - center(qb[g])[0], center(b)[1] - center(qb[g])[1])
                    if e > worst:
                        worst, wf = e, f
            if wf is not None:
                items.append((r["ref"] + " " + (r["role"] or ""), wf, int(round(fmap(wf))), rb[wf]))
        if len(items) >= a.crops:
            break
    for m in missing:
        if len(items) >= a.crops:
            break
        rt = tracks[m["ref"]]
        f = rt["frames"][0] + len(rt["boxes"]) // 2
        items.append(("MISSING " + m["ref"], f, int(round(fmap(f))), m["box"]))
    if not items:
        return
    ri, qi = video.probe(ref["source"]["path"]), video.probe(a.render)
    tiles = []
    for name, rf, qf, b in items:
        x0, y0, x1, y1 = max(0, b[0] - 24), max(0, b[1] - 24), min(ri["width"], b[2] + 24), min(ri["height"], b[3] + 24)
        try:
            A = Image.fromarray(video.read_frame(ref["source"]["path"], rf, ri)).crop((x0, y0, x1, y1))
            B = Image.fromarray(video.read_frame(a.render, qf, qi)).crop((x0, y0, x1, y1))
        except Exception:
            continue
        sc = min(1.0, 520.0 / max(A.width, 1))
        A, B = A.resize((int(A.width * sc), int(A.height * sc))), B.resize((int(B.width * sc), int(B.height * sc)))
        t = Image.new("RGB", (A.width * 2 + 8, A.height + 16), (40, 40, 40))
        t.paste(A, (0, 16))
        t.paste(B, (A.width + 8, 16))
        ImageDraw.Draw(t).text((3, 2), "%s  ref f%d | render f%d" % (name, rf, qf), fill=(255, 255, 0))
        tiles.append(t)
    if not tiles:
        return
    cols = 2
    rows_ = (len(tiles) + 1) // 2
    tw, th = max(t.width for t in tiles), max(t.height for t in tiles)
    sheet = Image.new("RGB", (cols * (tw + 6) + 6, rows_ * (th + 6) + 6), (20, 20, 20))
    for k, t in enumerate(tiles):
        sheet.paste(t, (6 + (k % cols) * (tw + 6), 6 + (k // cols) * (th + 6)))
    sheet.save(os.path.join(a.out, "fidelity-crops.png"))
    print("  crops:", os.path.join(a.out, "fidelity-crops.png"))


if __name__ == "__main__":
    main()
