#!/usr/bin/env python3
"""Measure a real music track into a beat grid the film can lock to (numpy + ffmpeg only, no librosa).

  beats      every beat (seconds)                -> state changes / morphs land here
  downbeats  every 4th beat from the best phase  -> big moments / bar starts
  hits       onset peaks (seconds)               -> SFX / accents

usage:
  beat_grid.py track.mp3 [--start 0] [--len 20] [--out beats]     measure (writes beats.json + beats.js)
  beat_grid.py --bpm 120 --bars 8 [--offset 0] [--out beats]       nominal grid, no track (the film's default)

beats.js defines window.BEATS; load it BEFORE film.js and HFMorph.T(beat) then uses the measured times
(beat 0 = the first detected downbeat). Tempo/phase are estimated on a uniform grid: solid for steady tracks,
approximate for rubato. Numbers are evidence, not taste: pick the track by ear, then verify the lock in the render.
"""
import argparse, json, subprocess, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("track", nargs="?"); ap.add_argument("--start", type=float, default=0.0); ap.add_argument("--len", type=float, default=None)
ap.add_argument("--bpm", type=float); ap.add_argument("--bars", type=int, default=8); ap.add_argument("--offset", type=float, default=0.0)
ap.add_argument("--out", default="beats")
a = ap.parse_args()

if not a.track:
    if not a.bpm: sys.exit("give a track, or --bpm for a nominal grid")
    spb = 60.0 / a.bpm; n = a.bars * 4
    beats = [round(a.offset + i * spb, 4) for i in range(n + 1)]
    out = {"bpm": a.bpm, "offset": a.offset, "confidence": None, "source": "nominal", "beats": beats, "downbeats": beats[::4], "hits": beats}
else:
    SR, HOP, NFFT = 22050, 256, 1024
    cmd = ["ffmpeg", "-v", "error", "-ss", str(a.start)] + (["-t", str(a.len)] if a.len else []) + ["-i", a.track, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, dtype=np.float32)
    if len(x) < SR * 4: sys.exit("track too short to measure")
    win = np.hanning(NFFT); fr = (len(x) - NFFT) // HOP
    S = np.abs(np.fft.rfft(np.stack([x[i * HOP:i * HOP + NFFT] * win for i in range(fr)]), axis=1))
    S = np.log1p(10 * S)
    flux = np.maximum(0, np.diff(S, axis=0)).sum(1); flux = np.concatenate([[0], flux])
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    fps = SR / HOP
    def comb(bpm, ph):   # mean onset strength on a beat grid, with a half-beat penalty (prefers the true pulse over its double-time)
        spb = 60.0 / bpm * fps; t = np.arange(ph, len(flux) - 1, spb)
        on = np.interp(t, np.arange(len(flux)), flux); half = np.interp(t[:-1] + spb / 2, np.arange(len(flux)), flux)
        return on.mean() - 0.35 * max(0.0, half.mean())
    best = (-9, 0, 0)
    for bpm in np.arange(70, 181, 0.5):
        spb = 60.0 / bpm * fps
        for ph in np.arange(0, spb, max(1.0, spb / 24)):
            sc = comb(bpm, ph)
            if sc > best[0]: best = (sc, bpm, ph)
    _, bpm0, ph0 = best
    for bpm in np.arange(bpm0 - 0.6, bpm0 + 0.61, 0.05):          # refine
        spb = 60.0 / bpm * fps
        for ph in np.arange(max(0, ph0 - 3), ph0 + 3, 0.25):
            sc = comb(bpm, ph)
            if sc > best[0]: best = (sc, bpm, ph)
    sc, bpm, ph = best
    LAT = (NFFT / 2) / SR                      # a flux frame's onset sits ~half a window after the frame start
    spb_s = 60.0 / bpm; t0 = ph / fps + LAT
    n = int((len(x) / SR - t0) / spb_s)
    bt = t0 + np.arange(n + 1) * spb_s
    # downbeat phase: which of 4 positions carries the most low-frequency energy (kick) + onset strength
    lo = S[:, :12].sum(1); lo = np.concatenate([[0], np.maximum(0, np.diff(lo))]) if len(lo) else lo
    scores = [np.interp((bt[k::4] - LAT) * fps, np.arange(len(flux)), flux + lo / (lo.std() + 1e-9)).mean() for k in range(4)]
    k0 = int(np.argmax(scores))
    beats = bt[k0:] + a.start
    thr = flux.mean() + 1.0
    pk = [i for i in range(2, len(flux) - 2) if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] > flux[i + 1] and flux[i] >= flux[i - 2] and flux[i] > flux[i + 2]]
    hits = [round(i / fps + LAT + a.start, 3) for i in pk]
    conf = float(sc)
    out = {"bpm": round(float(bpm), 2), "offset": round(float(beats[0]), 4), "confidence": round(conf, 2), "source": a.track,
           "beats": [round(float(v), 4) for v in beats], "downbeats": [round(float(v), 4) for v in beats[::4]], "hits": hits}
    print(f"{out['bpm']} bpm, first downbeat {out['offset']} s, confidence {out['confidence']} (>~0.8 = clear pulse, <0.4 = unreliable), {len(beats)} beats, {len(hits)} hits")

json.dump(out, open(a.out + ".json", "w"), indent=1)
open(a.out + ".js", "w").write("window.BEATS = " + json.dumps(out) + ";\n")
print(f"wrote {a.out}.json and {a.out}.js")
