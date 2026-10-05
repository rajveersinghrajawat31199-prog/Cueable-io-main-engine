#!/usr/bin/env python3
"""Build the audio tracks. voice / sfx / bgm stay SEPARATE <audio> tags in the composition (the critic classifies them by tag):
  assets/audio/sfx.wav   cue-timed soft sounds (build/schedule.json)
  assets/audio/bgm.wav   music bed, 3-band carved + ducked under the voice, faded in/out   (if assets/audio/bgm_src.mp3 exists)
  assets/audio/mix.wav   all three summed, for loudness numbers only
usage: python3 scripts/build_audio.py [--bgm path | --no-bgm] [--bgm-db -13] [--bgm-from SECONDS]
BGM level = dB of the music's average level relative to the voice's. By default the excerpt starts on a beat so that a downbeat
lands on the hook -> story transition (beat grid measured with scripts/bgm_analyze.py)."""
import argparse
import json
import os
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
SR = 48000
DEFAULT_BGM = os.path.join(ROOT, "assets", "audio", "bgm_src.mp3")
ap = argparse.ArgumentParser()
ap.add_argument("--bgm", default=DEFAULT_BGM if os.path.exists(DEFAULT_BGM) else None)
ap.add_argument("--no-bgm", action="store_true")
ap.add_argument("--bgm-db", type=float, default=-9.5)
ap.add_argument("--bgm-from", type=float, default=None, help="REQUIRED with a song: excerpt start = the song's drum/beat entrance minus ~0.5 s (see analysis/bgm_analysis.txt), so the beat lands ~0.5 s into the video")
ap.add_argument("--beat", type=float, default=0.859, help="beat period of the song (s)")
ap.add_argument("--phase", type=float, default=0.348, help="time of a beat in the song (s)")
ap.add_argument("--song-end", type=float, default=1e9, help="music body ends here (set it if the file has a fade-out/outro/skit)")
A = ap.parse_args()


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def write(name, arr):
    with wave.open(os.path.join(ROOT, "assets", "audio", name), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(arr, -1, 1) * 32767).astype("<i2").tobytes())


sched = json.load(open(os.path.join(ROOT, "build", "schedule.json")))
meta = json.load(open(os.path.join(ROOT, "assets", "sfx", "_meta.json")))
vo = decode(os.path.join(ROOT, "assets", "audio", "vo.wav"))
DUR = sched["duration"]
n = int((DUR + 0.6) * SR)
mix = np.zeros((n, 2), np.float32)
mix[:min(n, len(vo))] += vo[:n]
cache, placed, dropped = {}, 0, 0
for k, e in enumerate(sched["sfx"]):
    x = cache.setdefault(e["name"], decode(os.path.join(ROOT, "assets", "sfx", e["name"] + ".wav")))
    f = 1 + 0.035 * np.sin(k * 2.1)                       # tiny deterministic pitch/length variation so repeats don't machine-gun
    xs = np.stack([np.interp(np.arange(0, len(x) - 1, f), np.arange(len(x)), x[:, c]) for c in (0, 1)], 1).astype(np.float32)
    start = e["t"] - (meta[e["name"]]["apex"] / f if e.get("align") == "apex" else 0.0)
    if start < 0.15 or start * SR >= n:                    # never put a sound at t=0 / past the end
        dropped += 1
        continue
    s = int(start * SR)
    seg = xs[:max(0, min(len(xs), n - s))] * (10 ** (e["gain"] / 20))
    mix[s:s + len(seg)] += seg
    placed += 1
sfx_only = mix.copy()
sfx_only[:min(n, len(vo))] -= vo[:n]
write("sfx.wav", sfx_only[:int(DUR * SR)])

bgm_path = os.path.join(ROOT, "assets", "audio", "bgm.wav")
if os.path.exists(bgm_path):
    os.remove(bgm_path)
if A.bgm and not A.no_bgm:
    song = decode(A.bgm)
    if A.bgm_from is None:
        raise SystemExit("pass --bgm-from <seconds>: the song's drum/beat entrance minus ~0.5 s (analysis/bgm_analysis.txt)")
    start = A.bgm_from
    if start + DUR + 0.4 > A.song_end:
        raise SystemExit("excerpt would run into the song's outro: lower --bgm-from")
    b = song[int(start * SR):int(start * SR) + n].copy()
    if len(b) < n:
        b = np.pad(b, ((0, n - len(b)), (0, 0)))
    # --- 3-band split (zero-phase FFT, raised-cosine crossovers at 250 Hz and 3.5 kHz)
    N = 1 << int(np.ceil(np.log2(n)))
    X = np.fft.rfft(b, n=N, axis=0)
    fq = np.fft.rfftfreq(N, 1 / SR)

    def lp(fc, w=0.6):
        x = (np.clip(np.log2(np.maximum(fq, 1.0) / fc), -w, w) + w) / (2 * w)
        return 0.5 * (1 + np.cos(np.pi * x))
    lo_m, hi_m = lp(250), 1 - lp(3500)
    masks = [lo_m, 1 - lo_m - hi_m, hi_m]
    lo, mid, hi = [np.fft.irfft(X * m[:, None], n=N, axis=0)[:n].astype(np.float32) for m in masks]
    # --- voice activity (10 ms frames) -> smooth 0..1 curve at sample rate
    vm = np.abs(vo).max(1)
    nf = len(vm) // 480
    rms = np.sqrt((vm[:nf * 480].reshape(nf, 480) ** 2).mean(1))
    act = np.clip((20 * np.log10(rms + 1e-9) + 40) / 9, 0, 1)
    dil = (np.convolve((act > 0.5).astype(float), np.ones(25), "same") > 0).astype(float)   # hold 0.25 s
    kern = np.hanning(41); kern /= kern.sum()
    sm = np.convolve(dil, kern, "same")                                                    # 0.4 s attack/release
    a = np.interp(np.arange(n) / SR * 100, np.arange(len(sm)), sm)
    # while the voice speaks: mids (where speech lives) go down hard, lows/highs only a little
    g = lambda dB: 1 - a * (1 - 10 ** (dB / 20))   # noqa: E731
    bed = lo * g(-4.5)[:, None] + mid * g(-14)[:, None] + hi * g(-5.5)[:, None]
    t = np.arange(n) / SR
    fade = np.clip((t - 0.12) / 0.2, 0, 1) * np.clip((DUR + 0.3 - t) / 2.4, 0, 1)         # in from silence, out over the last 2.4 s
    bed *= fade[:, None]
    L = int(DUR * SR)
    vo_rms = float(np.sqrt((vo[:L] ** 2).mean()))
    G = vo_rms * 10 ** (A.bgm_db / 20) / (float(np.sqrt((bed[:L] ** 2).mean())) + 1e-9)
    bgm = (bed * G).astype(np.float32)
    write("bgm.wav", bgm[:L])
    mix += bgm
    print("bgm: song %.1fs-%.1fs, %.1f dB under the voice on average, mids ducked 14 dB while he speaks" % (start, start + DUR, A.bgm_db))

pk = float(np.abs(mix).max())
if pk > 0.89:
    mix *= 0.89 / pk
out = os.path.join(ROOT, "assets", "audio", "mix.wav")
write("mix.wav", mix)
print("mix.wav %.2fs, %d sfx placed (%d dropped), peak %.1f dBFS" % (n / SR, placed, dropped, 20 * np.log10(min(pk, 0.89) + 1e-9)))
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
tail = r[r.rfind("Integrated loudness"):]
print(" ".join(l.strip() for l in tail.splitlines() if "I:" in l or "Peak:" in l))
