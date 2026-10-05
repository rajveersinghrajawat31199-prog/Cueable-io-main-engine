#!/usr/bin/env python3
"""Structure of a music file: loudness per 4 s, vocal-band centre/side ratio, tempo + beat grid (numpy only)."""
import subprocess
import sys

import numpy as np

SR = 22050
path = sys.argv[1]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2)
n = len(x)
mid, side = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2
hop, win = 512, 2048
w = np.hanning(win)
frames = (n - win) // hop
S_m = np.abs(np.array([np.fft.rfft(mid[i * hop:i * hop + win] * w) for i in range(frames)]))
S_s = np.abs(np.array([np.fft.rfft(side[i * hop:i * hop + win] * w) for i in range(frames)]))
fr = np.fft.rfftfreq(win, 1 / SR)
band = lambda S, a, b: (S[:, (fr >= a) & (fr < b)] ** 2).sum(1)   # noqa: E731
fps = SR / hop
rms = 10 * np.log10(band(S_m, 20, 11000) + 1e-9)
vocal = 10 * np.log10((band(S_m, 300, 3500) + 1e-9) / (band(S_s, 300, 3500) + 1e-9))   # centre-heavy mid band ~ vocals
low = 10 * np.log10(band(S_m, 20, 200) + 1e-9)
# tempo: autocorrelation of spectral flux
flux = np.maximum(0, np.diff(np.log1p(S_m), axis=0)).sum(1)
flux = flux - flux.mean()
ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
lo, hi = int(fps * 60 / 200), int(fps * 60 / 60)
lag = lo + int(np.argmax(ac[lo:hi]))
bpm = 60 * fps / lag
print("duration %.1fs  tempo ~%.1f BPM (beat %.3fs)" % (n / SR, bpm, lag / fps))
print(" t(s)   level  vocal-ratio(dB)  low")
for t in range(0, int(n / SR) - 3, 4):
    a, b = int(t * fps), int((t + 4) * fps)
    print("%5d  %6.1f  %6.1f  %6.1f" % (t, rms[a:b].mean(), vocal[a:b].mean(), low[a:b].mean()))
# beat phase: strongest offset of the flux grid
P = lag
phase = int(np.argmax([flux[k::P].sum() for k in range(P)]))
print("beat phase %.3fs (first beat); beats every %.3fs" % (phase / fps, P / fps))
