#!/usr/bin/env python3
"""Beat grid for a supplied music track (use ONLY when the user supplies music or asks for a music-driven film).

usage: beat_grid.py track.mp3 [--out grid.json] [--bpm-range 70 180]
Fits a constant-tempo grid (bpm + phase) to the onset curve, scores each bar by energy, picks the downbeat phase
(strongest of 4 beats), lists section changes, and proposes bar-aligned loop splice points for lengthening.
Numbers are evidence, not taste: always say "unverified by ear".
"""
import argparse, json, subprocess, numpy as np

SR, HOP, N = 22050, 256, 1024

def load(path):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, dtype=np.float32)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("track"); ap.add_argument("--out"); ap.add_argument("--bpm-range", nargs=2, type=float, default=[70, 180])
    a = ap.parse_args()
    x = load(a.track); dur = len(x) / SR; fps = SR / HOP
    win = np.hanning(N)
    fr = (len(x) - N) // HOP
    S = np.abs(np.fft.rfft(np.stack([x[i * HOP:i * HOP + N] * win for i in range(fr)]), axis=1))
    L = np.log1p(S * 20)
    flux = np.maximum(0, np.diff(L, axis=0)).sum(1)                      # onset strength per frame
    flux = flux - np.convolve(flux, np.ones(43) / 43, "same")
    flux = np.maximum(flux, 0); flux /= (flux.max() + 1e-9)
    rms = np.sqrt(np.convolve(x ** 2, np.ones(HOP * 4) / (HOP * 4), "same"))[::HOP][:len(flux)]

    best = (-1, None, None)
    for bpm in np.arange(a.bpm_range[0], a.bpm_range[1], 0.1):
        period = 60.0 / bpm * fps
        for ph in np.arange(0, period, 0.5):
            idx = np.round(np.arange(ph, len(flux) - 1, period)).astype(int)
            sc = flux[idx].sum() / len(idx)
            if sc > best[0]: best = (sc, bpm, ph)
    score, bpm, ph = best
    # prefer the half/double tempo that sits in a musical range 90-140 if it scores almost as well
    beat_s = 60.0 / bpm
    beats = np.arange(ph / fps, dur, beat_s)
    # downbeat: which of 4 phases carries the most low-frequency energy + flux
    low = L[:, :20].sum(1)
    bi = np.round(beats * fps).astype(int); bi = bi[bi < len(low)]
    strength = np.array([flux[min(i, len(flux) - 1)] + 0.02 * low[i] / (low.max() + 1e-9) for i in bi])
    down = int(np.argmax([strength[k::4].sum() for k in range(4)]))
    bars = beats[down::4]
    bar_rms = np.array([rms[int(t * fps):int((t + 4 * beat_s) * fps)].mean() if int(t * fps) < len(rms) else 0 for t in bars])
    bar_db = 20 * np.log10(bar_rms + 1e-9)
    # sections: contiguous bars within 2.5 dB of a running level
    sections, start = [], 0
    for i in range(1, len(bars)):
        if abs(bar_db[i] - bar_db[start:i].mean()) > 2.5:
            sections.append((round(float(bars[start]), 3), round(float(bars[i]), 3), round(float(bar_db[start:i].mean()), 1))); start = i
    sections.append((round(float(bars[start]), 3), round(float(dur), 3), round(float(bar_db[start:].mean()), 1)))
    # loop splice candidates: pairs of bar starts with similar spectrum, 8-16 bars apart (for lengthening)
    spec = []
    for t in bars:
        i0, i1 = int(t * fps), int((t + 4 * beat_s) * fps)
        spec.append(L[i0:max(i1, i0 + 1)].mean(0) if i0 < len(L) else np.zeros(L.shape[1]))
    spec = np.array(spec); splices = []
    for i in range(len(bars)):
        for j in range(i + 4, min(len(bars), i + 17)):
            d = float(np.linalg.norm(spec[i] - spec[j]) / (np.linalg.norm(spec[i]) + 1e-9))
            splices.append((d, round(float(bars[i]), 3), round(float(bars[j]), 3), j - i))
    splices.sort()
    out = dict(track=a.track, duration=round(dur, 3), bpm=round(float(bpm), 2), beat_s=round(beat_s, 4), fit_score=round(float(score), 3),
               first_beat=round(float(beats[0]), 3), downbeat_phase=down, beats=[round(float(t), 3) for t in beats],
               bars=[round(float(t), 3) for t in bars], bar_db=[round(float(d), 1) for d in bar_db], sections=sections,
               splice_candidates=[dict(from_bar_t=s[1], to_bar_t=s[2], bars=s[3], mismatch=round(s[0], 3)) for s in splices[:8]])
    if a.out: json.dump(out, open(a.out, "w"), indent=1)
    print(f"{dur:.1f}s  bpm {bpm:.1f}  beat {beat_s*1000:.0f} ms  bar {4*beat_s:.2f}s  first beat {beats[0]:.3f}s  fit {score:.2f}")
    print("sections (start, end, dB):", *sections)
    print("loudness per bar (dB):", " ".join(f"{d:.0f}" for d in bar_db))
    print("splice candidates (lengthen by repeating a section):", *[f"{s[1]}->{s[2]} ({s[3]} bars, mism {s[0]:.2f})" for s in splices[:4]])

main()
