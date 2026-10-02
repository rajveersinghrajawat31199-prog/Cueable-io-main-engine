#!/usr/bin/env python3
"""Rank candidate music beds by measurement (you cannot listen): steadiness, pulse density, brightness, tempo,
and the best steady window of the needed length. With --ref (an mp3/mp4 whose sound you like) candidates are ranked by
distance to it; without, by suitability for a voice-over launch video.

usage: measure_music.py [--ref reference.mp4] [--len 58] cand1.mp3 cand2.mp3 ...
Needs ffmpeg + numpy. Numbers are evidence, not taste: always say "unverified by ear" when recommending.
"""
import subprocess, sys, numpy as np

SR, HOP = 22050, 512

def load(path, limit=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR)] + (["-t", str(limit)] if limit else []) + ["-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, dtype=np.float32)

def features(path, need=58):
    x = load(path); dur = len(x) / SR
    sec = np.array([20 * np.log10(np.sqrt(np.mean(x[i*SR:(i+1)*SR] ** 2)) + 1e-9) for i in range(int(dur))])
    seg = x[:SR * 60]; fr = len(seg) // HOP
    S = np.abs(np.fft.rfft(np.stack([seg[i*HOP:i*HOP+1024] * np.hanning(1024) for i in range(fr - 2)]), axis=1))
    fl = np.maximum(0, np.diff(np.log1p(S), axis=0)).sum(1); fl = fl - fl.mean()
    ac = np.correlate(fl, fl, "full")[len(fl) - 1:]; fps = SR / HOP
    cand = sorted(((ac[int(round(60 / b * fps))] + 0.5 * ac[min(len(ac) - 1, int(round(120 / b * fps)))], b) for b in range(80, 180)), reverse=True)
    freqs = np.fft.rfftfreq(1024, 1 / SR)
    thr = fl.mean() + fl.std()
    onsets = ((fl[1:-1] > fl[:-2]) & (fl[1:-1] > fl[2:]) & (fl[1:-1] > thr)).sum() / (len(seg) / SR)
    body = sec[8:] if len(sec) > 20 else sec
    win = None
    if dur > need + 8:
        win = min(((sec[t:t+need].std() + abs(sec[t:t+need].mean() - body.mean()) * 0.3, t) for t in range(0, int(dur - need))))
    return dict(dur=dur, bpm=cand[0][1], onsets=onsets, mean=float(body.mean()), std=float(body.std()),
                centroid=float(np.median((S * freqs).sum(1) / (S.sum(1) + 1e-9))), intro=float(sec[:10].mean() - body.mean()),
                win_start=(win[1] if win else 0), win_std=(float(sec[win[1]:win[1]+need].std()) if win else float(body.std())))

def main():
    a = sys.argv[1:]; ref = None; need = 58
    if "--ref" in a: i = a.index("--ref"); ref = a[i+1]; del a[i:i+2]
    if "--len" in a: i = a.index("--len"); need = int(a[i+1]); del a[i:i+2]
    rf = features(ref, need) if ref else None
    if rf: print(f"REFERENCE {ref.split('/')[-1][:40]}: pulse {rf['onsets']:.1f}/s  steadiness(std) {rf['std']:.1f} dB  brightness {rf['centroid']:.0f} Hz  tempo ~{rf['bpm']}(unreliable if edge)")
    rows = []
    for c in a:
        try: f = features(c, need)
        except Exception as e: print("skip", c, e); continue
        # lower = better. With a reference: distance in normalised units. Without: prefer steady + moderate pulse + long enough.
        if rf: score = abs(f["onsets"] - rf["onsets"]) / 2 + abs(f["win_std"] - rf["std"]) / 3 + abs(f["centroid"] - rf["centroid"]) / 2000
        else:  score = f["win_std"] / 3 + abs(f["onsets"] - 4.2) / 3 + (0 if f["dur"] >= need + 8 else 2)
        rows.append((score, c, f))
    rows.sort()
    print(f"\n{'score':>6}  {'track':44} {'len':>6} {'bpm':>4} {'pulse/s':>7} {'std dB':>6} {'bright Hz':>9} {'intro dB':>8}  best {need}s window")
    for s, c, f in rows:
        print(f"{s:6.2f}  {c.split('/')[-1][:44]:44} {f['dur']:5.0f}s {f['bpm']:4d} {f['onsets']:7.1f} {f['win_std']:6.1f} {f['centroid']:9.0f} {f['intro']:8.1f}  start {f['win_start']}s")
    if rows: print("\nTop pick by measurement (UNVERIFIED BY EAR): " + rows[0][1].split('/')[-1] + f"  -> start {rows[0][2]['win_start']}s")

main()
