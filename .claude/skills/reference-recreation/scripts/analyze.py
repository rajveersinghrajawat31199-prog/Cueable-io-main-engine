#!/usr/bin/env python3
"""Reference video analyzer: one pass, deterministic, no model calls.

  analyze.py VIDEO [--out DIR] [--ocr auto|on|off] [--width 256] [--max-seconds N]

Writes DIR/reference-style.json (everything a recreation needs), DIR/sheet-N.png (what an LLM looks at, one image per
~10 scenes), DIR/keyframes/*.png (native-resolution frames used for OCR / measurement) and prints a summary.

What it measures (all from pixels and samples; nothing is guessed):
  cuts + scenes (frame-exact), per scene: background colour, palette (exact colours), motion signature (static / bursts /
  loop period / step cadence / effective fps), activity box, fade-in, non-background regions (hero / cards / circles),
  text lines with box, size estimate, colour, alignment (macOS Vision OCR when available);
  audio: loudness, tempo + beat phase + which cuts land on the beat, strongest sound events by band, speech likelihood,
  how much the sound dips; and a feasibility tier (type-graphics / mixed / footage) with a target time band.
It does NOT understand meaning: the sheet is for the model/human to name what each scene IS (a chat bubble, a halftone hero).
"""
import argparse
import collections
import json
import math
import os
import re
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

try:
    from scipy import ndimage as ndi
except Exception:  # scipy is optional: regions are skipped without it
    ndi = None

HERE = os.path.dirname(os.path.abspath(__file__))
OCR_BIN = os.path.join(HERE, "..", "bin", "ocr")
T0 = time.time()
TIMES = collections.OrderedDict()


def tick(name, t):
    TIMES[name] = round(time.time() - t, 2)


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def hexc(c):
    return "#%02X%02X%02X" % tuple(int(round(float(x))) for x in c)


def probe(path):
    r = sh(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path], text=True)
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    au = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den or 1)
    return dict(width=v["width"], height=v["height"], fps=round(fps, 3), duration=float(d["format"].get("duration") or 0),
                audio=bool(au), size_bytes=int(d["format"].get("size") or 0), codec=v.get("codec_name"))


def decode(path, width, max_seconds):
    info = probe(path)
    h = int(round(info["height"] * width / info["width"] / 2.0)) * 2
    cmd = ["ffmpeg", "-v", "error", "-i", path]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    cmd += ["-vf", "scale=%d:%d:flags=area" % (width, h), "-pix_fmt", "rgb24", "-fps_mode", "passthrough", "-f", "rawvideo", "-"]
    raw = sh(cmd).stdout
    n = len(raw) // (width * h * 3)
    fr = np.frombuffer(raw, dtype=np.uint8)[: n * width * h * 3].reshape(n, h, width, 3)
    return info, fr


def ring_mask(h, w, frac=0.07):
    m = np.zeros((h, w), bool)
    t, s = max(1, int(h * frac)), max(1, int(w * frac))
    m[:t, :] = m[-t:, :] = True
    m[:, :s] = m[:, -s:] = True
    return m


# ------------------------------------------------------------------ cuts + scenes
def detect_cuts(fr):
    n, h, w, _ = fr.shape
    g = fr.astype(np.float32).mean(axis=3)
    d = np.abs(g[1:] - g[:-1]).mean(axis=(1, 2))
    ring = ring_mask(h, w)
    ring_px = fr[:, ring, :]  # (n,k,3)
    bc = np.median(ring_px, axis=1)
    bflat = ring_px.astype(np.float32).std(axis=1).max(axis=1) < 7
    bshift = np.linalg.norm(bc[1:] - bc[:-1], axis=1)
    # 8-bin per channel histogram distance
    q = (fr // 32).astype(np.int32)
    idx = q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]
    hist = np.zeros((n, 512), np.float32)
    for i in range(n):
        hist[i] = np.bincount(idx[i].ravel(), minlength=512)
    hist /= float(h * w)
    hd = 0.5 * np.abs(hist[1:] - hist[:-1]).sum(axis=1)
    score = np.maximum.reduce([d / 28.0, bshift / 45.0, hd / 0.45])
    cuts = []
    i = 0
    while i < len(score):
        if score[i] >= 1.0:
            j = min(len(score), i + 3)
            k = i + int(np.argmax(score[i:j]))
            if d[k] > 12 or bshift[k] > 30:
                cuts.append(dict(frame=int(k + 1), score=round(float(score[k]), 2), diff=round(float(d[k]), 1), bg_shift=round(float(bshift[k]), 1), hist=round(float(hd[k]), 2)))
            i = j
        else:
            i += 1
    return cuts, d, bc, bflat, g


def periodicity(x, lo=2, hi=60):
    x = np.asarray(x, np.float32)
    if len(x) < 2 * lo + 2:
        return None, 0.0
    x = x - x.mean()
    ac = np.correlate(x, x, "full")[len(x) - 1:]
    if ac[0] <= 1e-6:
        return None, 0.0
    ac = ac / ac[0]
    hi = min(hi, len(x) // 2)
    if hi <= lo:
        return None, 0.0
    lag = lo + int(np.argmax(ac[lo:hi + 1]))
    return lag, float(ac[lag])


def content_period(gs, box, lo=6, hi=60):
    """Loop length from CONTENT repetition (frame i vs i+L inside the activity box): returns (lag, ratio) with ratio = best/median diff."""
    m, h, w = gs.shape
    if m < 2 * lo + 4:
        return None, 1.0
    if box:
        x0, y0, x1, y1 = int(box[0] * w), int(box[1] * h), max(int(box[2] * w), int(box[0] * w) + 4), max(int(box[3] * h), int(box[1] * h) + 4)
        gs = gs[:, y0:y1, x0:x1]
    gs = gs[:, ::2, ::2]
    hi = min(hi, m // 2)
    if hi <= lo:
        return None, 1.0
    sims = np.array([np.abs(gs[L:] - gs[:-L]).mean() for L in range(lo, hi + 1)])
    for i in range(1, len(sims) - 1):
        if sims[i] < sims[i - 1] and sims[i] <= sims[i + 1]:
            peak = float(sims[:i].max())
            if peak > 1.0 and sims[i] < 0.6 * peak:
                return lo + i, float(sims[i] / peak)
    return None, 1.0


def top_colors(arr, k=4, min_share=0.02):
    """exact most common colours of an (h,w,3) uint8 image, near-duplicates merged."""
    flat = arr.reshape(-1, 3)
    vals, cnt = np.unique(flat, axis=0, return_counts=True)
    order = np.argsort(-cnt)
    out = []
    total = float(len(flat))
    for i in order[:400]:
        c = vals[i].astype(int)
        if cnt[i] / total < min_share / 4:
            break
        for o in out:
            if np.abs(np.array(o["rgb"]) - c).sum() < 36:
                o["share"] += cnt[i] / total
                break
        else:
            out.append(dict(rgb=[int(x) for x in c], share=cnt[i] / total))
    out = [o for o in out if o["share"] >= min_share][:k]
    return [dict(hex=hexc(o["rgb"]), share=round(o["share"], 3)) for o in out]


def native_frames(path, wanted, out_dir):
    """one ffmpeg pass for all wanted frame numbers -> {frame: png path}"""
    wanted = sorted(set(int(f) for f in wanted))
    if not wanted:
        return {}
    tmp = os.path.join(out_dir, "_tmp_%03d.png")
    expr = "+".join("eq(n\\,%d)" % f for f in wanted)
    sh(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", "select='%s'" % expr, "-fps_mode", "passthrough", "-frames:v", str(len(wanted)), tmp])
    res = {}
    for i, f in enumerate(wanted, start=1):
        src = tmp % i
        if os.path.exists(src):
            dst = os.path.join(out_dir, "f%06d.png" % f)
            os.replace(src, dst)
            res[f] = dst
    return res


def regions(png, bg, min_area=0.0015):
    if ndi is None:
        return []
    im = np.array(Image.open(png).convert("RGB")).astype(np.int32)
    H, W = im.shape[:2]
    mask = np.abs(im - np.array(bg)[None, None, :]).sum(axis=2) > 60
    mask = ndi.binary_closing(mask, structure=np.ones((9, 9)))
    lab, k = ndi.label(mask)
    out = []
    for i, sl in enumerate(ndi.find_objects(lab), start=1):
        if sl is None:
            continue
        ys, xs = sl
        area = int((lab[sl] == i).sum())
        if area / float(H * W) < min_area:
            continue
        sub = im[sl][lab[sl] == i]
        c = np.median(sub, axis=0)
        out.append(dict(x=int(xs.start), y=int(ys.start), w=int(xs.stop - xs.start), h=int(ys.stop - ys.start),
                        area_pct=round(100 * area / float(H * W), 2), fill=round(area / float((xs.stop - xs.start) * (ys.stop - ys.start)), 2),
                        color=hexc(c), colors_in_region=int(len(np.unique((sub // 16), axis=0)))))
    out.sort(key=lambda r: -r["area_pct"])
    return out[:8]


def ocr(pngs):
    if not pngs or not os.path.exists(OCR_BIN):
        return {}
    r = sh([OCR_BIN] + pngs, text=True)
    try:
        data = json.loads(r.stdout)
    except Exception:
        return {}
    return {d["image"]: d["lines"] for d in data}


# ------------------------------------------------------------------ audio
def audio_analysis(path, cut_times, max_seconds):
    sr = 22050
    cmd = ["ffmpeg", "-v", "error", "-i", path]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    raw = sh(cmd + ["-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]).stdout
    y = np.frombuffer(raw, dtype=np.float32)
    if len(y) < sr:
        return None
    cmd2 = ["ffmpeg", "-hide_banner", "-i", path]
    if max_seconds:
        cmd2 += ["-t", str(max_seconds)]
    ebu = sh(cmd2 + ["-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], text=True).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", ebu)
    lra = re.findall(r"LRA:\s+(-?[\d.]+) LU", ebu)
    pk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebu)
    n_fft, hop = 1024, 256
    win = np.hanning(n_fft).astype(np.float32)
    frames = 1 + (len(y) - n_fft) // hop
    S = np.empty((frames, n_fft // 2 + 1), np.float32)
    for i in range(frames):
        S[i] = np.abs(np.fft.rfft(y[i * hop:i * hop + n_fft] * win))
    L = np.log1p(S * 50)
    flux = np.maximum(0, np.diff(L, axis=0)).sum(1)
    t = (np.arange(len(flux)) + 1) * hop / float(sr)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

    def band(lo, hi):
        m = (freqs >= lo) & (freqs < hi)
        return np.maximum(0, np.diff(L[:, m], axis=0)).sum(1)

    low, mid, high = band(30, 200), band(200, 3000), band(3000, 11000)
    # tempo + phase
    f = flux - flux.mean()
    ac = np.correlate(f, f, "full")[len(f) - 1:]
    cands = []
    for bpm in range(60, 181):
        i = int(round(60.0 / bpm * sr / hop))
        if i < len(ac):
            cands.append((float(ac[i] / ac[0]), bpm))
    cands.sort(reverse=True)
    bpm, conf = (cands[0][1], cands[0][0]) if cands else (0, 0.0)
    # fold into 80..160
    while bpm and bpm < 80:
        bpm *= 2
    while bpm > 160:
        bpm /= 2.0
    period = 60.0 / bpm if bpm else 0
    best_off, best_val = 0.0, -1.0
    if period:
        for off in np.arange(0, period, 0.01):
            beats = np.arange(off, t[-1], period)
            val = float(np.interp(beats, t, flux).sum())
            if val > best_val:
                best_val, best_off = val, off
    on_beat = []
    phases = []
    for ct in cut_times:
        if period:
            ph = (((ct - best_off) / period) + 0.5) % 1.0 - 0.5
            phases.append(ph)
            on_beat.append(dict(t=round(ct, 3), off_ms=int(round(ph * period * 1000)), on_beat=bool(abs(ph) * period * 1000 < 70)))
    lock = None
    if len(phases) >= 3:
        offs = [p * period * 1000 for p in phases]
        best = (0, 0.0)
        for c in offs:
            members = [o for o in offs if abs(((o - c) + period * 500) % (period * 1000) - period * 500) <= 45]
            if len(members) > best[0]:
                best = (len(members), float(np.mean(members)))
        share = best[0] / float(len(offs))
        lock = dict(locked=bool(share >= 0.6), locked_cuts=int(best[0]), of=len(offs), offset_ms=int(round(best[1])),
                    note="the largest group of cuts that share one offset to the beat; negative = cuts land that many ms BEFORE the beat (editors cut early)")
    # strongest events
    thr = np.percentile(flux, 97)
    ev = []
    last = -1
    for i in range(1, len(flux) - 1):
        if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] > flux[i + 1] and t[i] - last > 0.06:
            b = int(np.argmax([low[i], mid[i], high[i] * 1.3]))
            ev.append(dict(t=round(float(t[i]), 3), strength=round(float(flux[i] / thr), 2), band=("low", "mid", "high")[b]))
            last = t[i]
    ev = sorted(ev, key=lambda e: -e["strength"])[:40]
    ev.sort(key=lambda e: e["t"])
    # per-second level + dips
    secs = int(len(y) / sr)
    rms = np.array([np.sqrt(np.mean(y[i * sr:(i + 1) * sr] ** 2) + 1e-12) for i in range(secs)])
    db = 20 * np.log10(rms + 1e-9)
    dips = float(np.median(db) - np.percentile(db, 10)) if secs >= 4 else 0.0
    silent = [round(float(i), 1) for i, v in enumerate(db) if v < -60]
    # speech likelihood: syllable-rate modulation of the 300..3400 Hz envelope + pauses
    m = (freqs >= 300) & (freqs < 3400)
    env = np.log1p(S[:, m].sum(1))
    env = env - np.convolve(env, np.ones(40) / 40.0, "same")
    fr_rate = sr / float(hop)
    seg = int(4 * fr_rate)
    ratios = []
    for s0 in range(0, max(1, len(env) - seg), seg // 2):
        e = env[s0:s0 + seg]
        if len(e) < seg:
            break
        sp = np.abs(np.fft.rfft(e * np.hanning(len(e)))) ** 2
        fq = np.fft.rfftfreq(len(e), 1.0 / fr_rate)
        tot = sp[(fq >= 0.5) & (fq <= 16)].sum() + 1e-9
        ratios.append(sp[(fq >= 3) & (fq <= 6)].sum() / tot)
    syl = float(np.mean(ratios)) if ratios else 0.0
    bandE = S[:, m].sum(1)
    pause = float(np.mean(bandE < np.percentile(bandE, 90) * 0.02))
    speech = "prior-only"
    return dict(loudness_lufs=float(lufs[-1]) if lufs else None, lra_lu=float(lra[-1]) if lra else None, true_peak_dbfs=float(pk[-1]) if pk else None,
                tempo=dict(bpm=round(bpm, 1), confidence=round(conf, 2), beat_offset_s=round(float(best_off), 3), beat_period_s=round(period, 3), has_beat=bool(conf > 0.30)),
                cuts_vs_beat=on_beat, cut_beat_lock=lock, cuts_on_beat=int(sum(1 for o in on_beat if o["on_beat"])), events=ev,
                level=dict(median_db=round(float(np.median(db)), 1), dip_db=round(dips, 1), silent_seconds=silent[:20],
                           continuous=bool(dips < 12 and not silent)),
                speech=dict(likelihood="unknown", prior=dict(syllable_ratio=round(syl, 3), pause_share=round(pause, 3)), note="heuristics cannot tell a beat from speech; Whisper decides"))


def asr(video, model_name, seconds):
    """detect with the tiny multilingual model first; only transcribe with model_name when speech is present."""
    first = _asr(video, "tiny", seconds)
    if first is None or not first["present"]:
        return first
    full = _asr(video, model_name, seconds)
    if full is not None:
        full["seconds"] = round(full["seconds"] + first["seconds"], 1)
    return full or first


def _asr(video, model_name, seconds):
    """Local Whisper (no network). Returns dict(present, words, text, share, segments) or None if whisper is unavailable."""
    try:
        import whisper  # noqa
    except Exception:
        return None
    wav = os.path.join("/tmp", "ref_asr_%d.wav" % os.getpid())
    sh(["ffmpeg", "-v", "error", "-y", "-i", video, "-t", str(seconds), "-vn", "-ac", "1", "-ar", "16000", wav])
    if not os.path.exists(wav):
        return None
    t = time.time()
    m = whisper.load_model(model_name)
    r = m.transcribe(wav, word_timestamps=True, language="en" if model_name.endswith(".en") else None, condition_on_previous_text=False, fp16=False)
    os.remove(wav)
    words, segs, spoken = [], [], 0.0
    for sg in r.get("segments", []):
        ok = sg.get("no_speech_prob", 1) < 0.6 and sg.get("avg_logprob", -9) > -1.0 and sg.get("compression_ratio", 9) < 2.4
        segs.append(dict(start=round(sg["start"], 2), end=round(sg["end"], 2), ok=bool(ok), no_speech=round(float(sg.get("no_speech_prob", 1)), 2), logprob=round(float(sg.get("avg_logprob", -9)), 2)))
        if ok:
            spoken += sg["end"] - sg["start"]
            for w in sg.get("words", []):
                words.append(dict(word=w["word"].strip(), start=round(float(w["start"]), 2), end=round(float(w["end"]), 2)))
    dur = float(seconds)
    present = len(words) >= 6 and spoken / max(1.0, dur) >= 0.08
    allseg = r.get("segments", [])
    wsum = sum(max(0.01, sg["end"] - sg["start"]) for sg in allseg) or 1.0
    ns = sum(sg.get("no_speech_prob", 1) * max(0.01, sg["end"] - sg["start"]) for sg in allseg) / wsum if allseg else 1.0
    lp = sum(sg.get("avg_logprob", -9) * max(0.01, sg["end"] - sg["start"]) for sg in allseg) / wsum if allseg else -9.0
    return dict(present=bool(present), model=model_name, words=words if present else [], text=" ".join(w["word"] for w in words) if present else "", spoken_share=round(spoken / max(1.0, dur), 2),
                mean_no_speech=round(float(ns), 2), mean_logprob=round(float(lp), 2), segments=segs[:60], seconds=round(time.time() - t, 1))


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out")
    ap.add_argument("--ocr", default="auto", choices=["auto", "on", "off"])
    ap.add_argument("--width", type=int, default=256)
    ap.add_argument("--max-seconds", type=float, default=None)
    ap.add_argument("--asr", default="auto", choices=["auto", "off"], help="local Whisper transcript + speech detection (auto = on when there is audio)")
    ap.add_argument("--asr-model", default="base.en")
    a = ap.parse_args()
    out = a.out or os.path.join(os.getcwd(), "analysis", os.path.splitext(os.path.basename(a.video))[0])
    kf = os.path.join(out, "keyframes")
    os.makedirs(kf, exist_ok=True)

    import concurrent.futures as cf
    pool = cf.ThreadPoolExecutor(max_workers=1)
    pinfo = probe(a.video)
    asr_future = pool.submit(asr, a.video, a.asr_model, min(pinfo["duration"], a.max_seconds or 1e9, 120)) if (pinfo["audio"] and a.asr != "off") else None
    t = time.time()
    info, fr = decode(a.video, a.width, a.max_seconds)
    n, H, W, _ = fr.shape
    fps = info["fps"]
    tick("decode", t)

    t = time.time()
    cuts, d, bc, bflat, g = detect_cuts(fr)
    tick("cuts", t)
    bounds = [0] + [c["frame"] for c in cuts] + [n]
    scenes = []
    transitions = []
    min_scene = max(3, int(round(0.3 * fps)))
    t = time.time()
    for si, (a0, b0) in enumerate(zip(bounds, bounds[1:])):
        if b0 - a0 < 1:
            continue
        if (b0 - a0) < min_scene and si not in (0, len(bounds) - 2):
            transitions.append(dict(start_frame=int(a0), end_frame=int(b0 - 1), frames=int(b0 - a0), bg=hexc(np.median(bc[a0:b0], axis=0)), kind="flash/dip between scenes"))
            continue
        bgc = np.median(bc[a0:b0], axis=0)
        ds = d[a0:b0 - 1] if b0 - a0 > 1 else np.array([0.0])
        act = ds > 0.6
        bursts = []
        i = 0
        while i < len(ds):
            if ds[i] > 0.6:
                j = i
                while j + 1 < len(ds) and ds[j + 1] > 0.6:
                    j += 1
                bursts.append([int(a0 + i), int(a0 + j + 1), round(float(ds[i:j + 1].max()), 1)])
                i = j + 1
            else:
                i += 1
        lag, acv = periodicity(ds)
        # a REAL stepped animation (on twos, on threes, 8 fps ...) alternates a spike of change with 1-3 near-repeat frames, all the way through its motion. A periodic pattern alone
        # (compression, easing) is not stepping, and soft low-contrast motion must not read as stepping either. Everything is relative to the scene's own p90 (noise differs per encode).
        p90_ = float(np.percentile(ds, 90)) if len(ds) else 0.0
        repeat_share, stepped = None, False
        if len(ds) >= 12 and p90_ >= 0.3:
            sm_ = np.convolve(ds, np.ones(9) / 9, mode="same")
            act_ = sm_ > 0.25 * p90_
            if int(act_.sum()) >= 9:
                low_ = ds[act_] < 0.4 * p90_
                repeat_share = float(low_.mean())
                trans_ = float(np.abs(np.diff(low_.astype(int))).sum() / max(1, len(low_) - 1))
                run_ = best_ = 0
                for v_ in low_:
                    run_ = run_ + 1 if v_ else 0
                    best_ = max(best_, run_)
                stepped = bool(repeat_share >= 0.30 and trans_ >= 0.35 and best_ <= 5)
        changed_frac = float((ds > 0.2).mean()) if len(ds) else 0.0
        # activity box
        if b0 - a0 > 1:
            ch = (np.abs(g[a0 + 1:b0] - g[a0:b0 - 1]) > 24).any(axis=0)
            ys, xs = np.where(ch)
            abox = [round(float(xs.min()) / W, 3), round(float(ys.min()) / H, 3), round(float(xs.max() + 1) / W, 3), round(float(ys.max() + 1) / H, 3)] if len(xs) else None
        else:
            abox = None
        ink = np.abs(fr[a0:b0].astype(np.float32) - bgc[None, None, None, :]).sum(axis=3).mean(axis=(1, 2))
        fade_in = bool(len(ink) > 6 and ink[0] < 0.5 * ink[min(len(ink) - 1, 8)] and ink[min(len(ink) - 1, 8)] > 3)
        best = int(a0 + np.argmax(ink)) if len(ink) else a0
        last = int(b0 - 1)
        tags = []
        static = len(ds) and float((ds < 0.6).mean()) >= 0.9
        if static:
            tags.append("static-hold")
        loop_lag, loop_ratio = (None, 1.0) if static else content_period(g[a0:b0], abox)
        if loop_lag and loop_ratio < 0.6:
            tags.append("loop(period=%df=%.2fs)" % (loop_lag, loop_lag / fps))
        if not static and stepped and lag and acv > 0.3 and 2 <= lag <= 4 and changed_frac < 0.7 and float(ds.max()) > 0.6:
            tags.append("step-cadence(%dfps)" % round(fps / lag))
        if bursts and "static-hold" not in tags:
            tags.append("%d-burst(s)" % len(bursts))
        if fade_in:
            tags.append("fade-in")
        palette = top_colors(fr[min(b0 - 1, a0 + (b0 - a0) // 2)], 4)
        scenes.append(dict(index=len(scenes) + 1, start_frame=int(a0), end_frame=int(b0 - 1), frames=int(b0 - a0), start_s=round(a0 / fps, 3),
                           duration_s=round((b0 - a0) / fps, 3), bg=hexc(bgc), bg_flat=bool(bflat[a0:b0].mean() > 0.8),
                           brightness=round(float(g[a0:b0].mean()), 1), palette=palette,
                           motion=dict(mean_diff=round(float(ds.mean()), 2), p90_diff=round(float(np.percentile(ds, 90)), 2), static_share=round(float((ds < 0.6).mean()), 2),
                                       effective_fps=round(fps * changed_frac, 1), step_period_frames=lag if (stepped and lag and acv > 0.3 and lag <= 4) else None, repeat_share_in_motion=None if repeat_share is None else round(repeat_share, 2),
                                       loop_period_frames=loop_lag if (loop_lag and loop_ratio < 0.6) else None, loop_ratio=round(loop_ratio, 2), bursts=bursts[:12], activity_box=abox, fade_in=fade_in),
                           tags=tags, key_frames=dict(best=best, last=last)))
    merged = []
    for tr_ in transitions:
        if merged and tr_["start_frame"] <= merged[-1]["end_frame"] + 2:
            m_ = merged[-1]
            m_["end_frame"] = tr_["end_frame"]
            m_["frames"] = m_["end_frame"] - m_["start_frame"] + 1
            m_["count"] += 1
            m_["kind"] = "rapid-change cluster (scroll / whip / strobe), not scenes"
        else:
            merged.append(dict(tr_, count=1))
    transitions = merged
    tick("scenes", t)

    # native keyframes, regions, OCR
    t = time.time()
    pngs = []
    want = []
    for s in scenes:
        want.append(s["key_frames"]["best"])
        if len(scenes) <= 16:
            want.append(s["key_frames"]["last"])
    got = native_frames(a.video, want, kf)
    for s in scenes:
        for label in ("best", "last"):
            fno = s["key_frames"][label]
            p = got.get(fno)
            if p is None:
                continue
            s["key_frames"][label + "_png"] = os.path.relpath(p, out)
            if label == "best":
                s["regions"] = regions(p, [int(x) for x in np.array([int(s["bg"][i:i + 2], 16) for i in (1, 3, 5)])])
            pngs.append(p)
        s.setdefault("regions", [])
    tick("keyframes+regions", t)
    t = time.time()
    lines_by = {}
    if a.ocr != "off" and os.path.exists(OCR_BIN):
        lines_by = ocr([p for p in pngs if os.path.exists(p)][:80])
    for s in scenes:
        txt = []
        seen = set()
        for label in ("last", "best"):
            p = os.path.join(out, s["key_frames"].get(label + "_png", ""))
            for ln in lines_by.get(p, []):
                key = ln["text"].strip().lower()
                if key in seen or not key:
                    continue
                seen.add(key)
                im = Image.open(p)
                Wn, Hn = im.size
                px = np.array(im.convert("RGB")).astype(np.int32)
                x0, y0 = int(ln["x"] * Wn), int(ln["y"] * Hn)
                x1, y1 = int((ln["x"] + ln["w"]) * Wn), int((ln["y"] + ln["h"]) * Hn)
                crop = px[max(0, y0):y1, max(0, x0):x1]
                bgc = np.array([int(s["bg"][i:i + 2], 16) for i in (1, 3, 5)])
                col = "n/a"
                if crop.size:
                    dd = np.abs(crop - bgc).sum(axis=2)
                    sel = crop[dd > dd.max() * 0.7] if dd.max() > 60 else crop.reshape(-1, 3)
                    col = hexc(np.median(sel, axis=0)) if len(sel) else "n/a"
                cx = (ln["x"] + ln["w"] / 2.0)
                txt.append(dict(text=ln["text"], frame=s["key_frames"][label], x=x0, y=y0, w=x1 - x0, h=y1 - y0, color=col,
                                align="center" if abs(cx - 0.5) < 0.04 else ("left" if cx < 0.5 else "right"), size_est_px=round((y1 - y0) / 0.92, 1),
                                conf=round(float(ln["conf"]), 2)))
        s["text"] = txt
    tick("ocr", t)

    # audio
    audio = None
    if info["audio"]:
        t = time.time()
        audio = audio_analysis(a.video, [c["frame"] / fps for c in cuts], a.max_seconds)
        tick("audio", t)
        if audio and asr_future is not None:
            t = time.time()
            tr = asr_future.result()
            tick("asr (waited after the video pass)", t)
            if tr is None:
                audio["speech"].update(likelihood="unknown", note="whisper not available: ask the user whether the reference has a voice-over")
            else:
                if not tr["present"]:
                    kind = "none"
                elif tr["mean_no_speech"] < 0.2:
                    kind = "voice-over" if tr["spoken_share"] >= 0.35 else "sparse voice-over"
                else:
                    kind = "sung vocals / lyrics (suspected: speech competes with music, no_speech %.2f)" % tr["mean_no_speech"]
                audio["speech"].update(likelihood="yes" if tr["present"] else "no", kind=kind,
                                       asr=dict(model=tr["model"], seconds=tr["seconds"], spoken_share=tr["spoken_share"], mean_no_speech=tr["mean_no_speech"], mean_logprob=tr["mean_logprob"], text=tr["text"][:400]),
                                       words=len(tr["words"]))
                if tr["present"]:
                    json.dump(tr["words"], open(os.path.join(out, "transcript.json"), "w"), indent=0)

    # feasibility
    conc = []
    for s_ in scenes:
        f_ = s_["key_frames"]["best"]
        q_ = (fr[f_] // 16).reshape(-1, 3).astype(np.int32)
        k_ = q_[:, 0] * 256 + q_[:, 1] * 16 + q_[:, 2]
        cnt_ = np.sort(np.bincount(k_))[::-1]
        conc.append(float(cnt_[:8].sum()) / len(k_))
        s_["color_concentration"] = round(conc[-1], 2)
    concentration = float(np.median(conc)) if conc else 0.0
    flat_ratio = float(bflat.mean())
    diversity = [max((r["colors_in_region"] for r in s.get("regions", [])), default=0) for s in scenes]
    div_med = float(np.median(diversity)) if diversity else 0
    text_scenes = sum(1 for s in scenes if s["text"]) / max(1, len(scenes))
    cuts_per_min = len(cuts) / max(1e-6, n / fps) * 60
    reasons = ["%d%% of frames have a flat border colour" % round(100 * flat_ratio), "median distinct-colour richness of the biggest region: %d" % div_med,
               "%d%% of scenes contain readable text" % round(100 * text_scenes), "%.0f cuts per minute" % cuts_per_min]
    reasons.append("colour concentration %.2f (share of pixels in the 8 most common colours; flat graphics ~0.9, gradients/UI 0.5-0.85, photos/footage < 0.4)" % concentration)
    if concentration >= 0.85 and text_scenes >= 0.6:
        tier, eta = "type-graphics", "3-6 min (target)"
    elif concentration >= 0.45 and text_scenes >= 0.4:
        tier, eta = "ui-graphics", "10-15 min (target): UI screens / gradients / motion graphics, rebuild as HTML"
    elif concentration >= 0.45 and flat_ratio >= 0.4:
        tier, eta = "graphics-no-text", "8-12 min (target)"
    else:
        tier, eta = "footage", "no clone promised: copy pace, captions and overlays onto the customer's own footage; 10-20 min (target)"
    if tier in ("type-graphics", "ui-graphics"):
        tier_conf = "high" if text_scenes >= 0.8 else "medium"
    elif tier == "footage":
        tier_conf = "high" if (text_scenes == 0 and flat_ratio < 0.1) else "low: abstract motion graphics without text also land here, check the sheet"
    else:
        tier_conf = "medium"
    photo_scenes = [s_["index"] for s_ in scenes if any(r_["colors_in_region"] >= 120 and r_["area_pct"] >= 8 for r_ in s_.get("regions", []))]
    cad = [round(fps / s_["motion"]["step_period_frames"]) for s_ in scenes if any(t_.startswith("step-cadence") for t_ in s_["tags"]) and s_["motion"].get("step_period_frames")]
    cadence = collections.Counter(cad).most_common(1)[0][0] if cad else None
    sheets = make_sheets(fr, scenes, out, fps)
    summary = dict(schema="reference-style/1", source=dict(path=os.path.abspath(a.video), **info, frames=n, analyzed_frames=n), cuts=cuts,
                   transitions=transitions, scenes=scenes, audio=audio, feasibility=dict(tier=tier, tier_confidence=tier_conf, eta_target=eta, flat_border_ratio=round(flat_ratio, 2), color_concentration=round(concentration, 2), region_color_richness=div_med,
                                                               text_scene_share=round(text_scenes, 2), cuts_per_min=round(cuts_per_min, 1), reasons=reasons),
                   style=dict(cadence_fps=cadence, cadence_note=("animation is stepped at %s fps on a %s fps file ('on twos'): quantise motion time in the build" % (cadence, round(fps))) if cadence and cadence < fps - 1 else None,
                              imagery=dict(photo_like_scenes=photo_scenes, note="possible photographs or rich gradients in these scenes (colour-count heuristic, can false-positive): check the sheet; real photos are sourced or generated (stock or /pollo-generate), UI and text are rebuilt as HTML") if photo_scenes else None),
                   sheets=sheets, timings=dict(TIMES, total=round(time.time() - T0, 2)))
    json.dump(summary, open(os.path.join(out, "reference-style.json"), "w"), indent=1)
    print_summary(summary, out)


def make_sheets(fr, scenes, out, fps):
    n, H, W, _ = fr.shape
    paths = []
    if len(scenes) <= 10:
        cw = W
        ch = H
        rows = []
        for s in scenes:
            a0, b0 = s["start_frame"], s["end_frame"]
            picks = sorted(set([min(b0, a0 + 2), a0 + (b0 - a0) // 3, a0 + 2 * (b0 - a0) // 3, max(a0, b0 - 2)]))
            while len(picks) < 4:
                picks.append(picks[-1])
            rows.append((s, picks[:4]))
        sheet = Image.new("RGB", (4 * cw + 5 * 4 + 130, len(rows) * (ch + 4) + 4), (50, 50, 50))
        d = ImageDraw.Draw(sheet)
        for r, (s, picks) in enumerate(rows):
            y = 4 + r * (ch + 4)
            d.text((6, y + 6), "scene %d" % s["index"], fill=(255, 255, 0))
            d.text((6, y + 22), "f%d-%d" % (s["start_frame"], s["end_frame"]), fill=(255, 255, 255))
            d.text((6, y + 38), "%.2fs" % s["duration_s"], fill=(255, 255, 255))
            d.text((6, y + 54), s["bg"], fill=(200, 200, 200))
            for c, f in enumerate(picks):
                x = 130 + 4 + c * (cw + 4)
                sheet.paste(Image.fromarray(fr[f]), (x, y))
                d.rectangle([x, y, x + 44, y + 12], fill=(0, 0, 0))
                d.text((x + 2, y + 1), "f%d" % f, fill=(255, 255, 0))
        p = os.path.join(out, "sheet-1.png")
        sheet.save(p)
        paths.append(os.path.relpath(p, out))
    else:
        cols, per = 8, 40
        cw, ch = 160, int(160 * H / float(W))
        for k in range(0, len(scenes), per):
            chunk = scenes[k:k + per]
            rows = (len(chunk) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * (cw + 3) + 3, rows * (ch + 3) + 3), (50, 50, 50))
            d = ImageDraw.Draw(sheet)
            for i, s in enumerate(chunk):
                f = (s["start_frame"] + s["end_frame"]) // 2
                im = Image.fromarray(fr[f]).resize((cw, ch), Image.LANCZOS)
                x, y = 3 + (i % cols) * (cw + 3), 3 + (i // cols) * (ch + 3)
                sheet.paste(im, (x, y))
                d.rectangle([x, y, x + 62, y + 12], fill=(0, 0, 0))
                d.text((x + 2, y + 1), "s%d f%d" % (s["index"], f), fill=(255, 255, 0))
            p = os.path.join(out, "sheet-%d.png" % (k // per + 1))
            sheet.save(p)
            paths.append(os.path.relpath(p, out))
    return paths


def print_summary(s, out):
    src = s["source"]
    print("REFERENCE %s  %dx%d  %.2f fps  %d frames = %.3f s   analyzed in %.1f s" % (os.path.basename(src["path"]), src["width"], src["height"], src["fps"], src["frames"],
                                                                                    src["frames"] / src["fps"], s["timings"]["total"]))
    print("  cuts at frames: %s" % [c["frame"] for c in s["cuts"]][:60])
    if s.get("transitions"):
        print("  transitions (not scenes): %s" % [(t_["start_frame"], t_["frames"], t_.get("count", 1)) for t_ in s["transitions"]][:12])
    print("  scenes:")
    for sc in s["scenes"][:14]:
        txt = " | ".join(t["text"] for t in sc["text"][:3])
        print("   %2d  f%-4d-%-4d %5.2fs  bg %s %-4s  %-34s %s" % (sc["index"], sc["start_frame"], sc["end_frame"], sc["duration_s"], sc["bg"], "flat" if sc["bg_flat"] else "",
                                                               ", ".join(sc["tags"])[:34], ("text: " + txt[:60]) if txt else ""))
    if len(s["scenes"]) > 14:
        print("   ... %d more scenes in the json" % (len(s["scenes"]) - 14))
    au = s["audio"]
    if au:
        tp = au["tempo"]
        lk = au.get("cut_beat_lock")
        print("  audio: %.1f LUFS | tempo %.0f bpm (confidence %.2f, beat=%s) | cuts %s | continuous sound: %s | speech: %s%s"
              % (au["loudness_lufs"] if au["loudness_lufs"] is not None else float("nan"), tp["bpm"], tp["confidence"], tp["has_beat"],
                 ("locked to the beat: %d of %d cuts at %+d ms" % (lk["locked_cuts"], lk["of"], lk["offset_ms"]) if lk and lk["locked"] else ("not locked to the beat" + (" (best group %d of %d)" % (lk["locked_cuts"], lk["of"]) if lk else ""))),
                 au["level"]["continuous"], au["speech"].get("kind", au["speech"]["likelihood"]), (" (%d words)" % au["speech"].get("words", 0)) if au["speech"]["likelihood"] == "yes" else ""))
    else:
        print("  audio: none")
    f = s["feasibility"]
    print("  feasibility: %s [confidence %s], target %s  (%s)" % (f["tier"], f["tier_confidence"], f["eta_target"], "; ".join(f["reasons"])))
    st = s.get("style") or {}
    if st.get("cadence_fps"):
        print("  style: stepped cadence %s fps%s" % (st["cadence_fps"], "" if not st.get("cadence_note") else " (on twos)"))
    if st.get("imagery"):
        print("  style: possible photo / rich-gradient regions in scenes %s (heuristic: check the sheet)" % st["imagery"]["photo_like_scenes"])
    print("  timings (s): %s" % dict(s["timings"]))
    print("  wrote %s/reference-style.json, %s" % (out, ", ".join(s["sheets"])))


if __name__ == "__main__":
    main()
