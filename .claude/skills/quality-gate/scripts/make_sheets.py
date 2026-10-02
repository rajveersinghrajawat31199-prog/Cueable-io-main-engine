#!/usr/bin/env python3
"""Make the images a reviewer must LOOK at (true aspect, unlike the old 16:9-cell critic sheets). Writes quality/sheets/:
  hook.png      first 2 s at 6 fps            -> axis first_2s
  phone.png     1 fps at 360 px wide          -> axis phone_readability
  contact.png   2 fps overview                -> axes composition, brand_accuracy, message_clarity
  strip-N.png   12 consecutive frames around the 3 biggest moments -> axis motion_quality
  seam.png      last 3 frames + first 3 frames (loop films)
usage: make_sheets.py renders/final.mp4 [--project .] [--bpm 120]
"""
import argparse, math, os, subprocess
import numpy as np
from qg_common import load_gray, activity

ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--project", default="."); ap.add_argument("--bpm", type=float); a = ap.parse_args()
out = os.path.join(os.path.abspath(a.project), "quality", "sheets"); os.makedirs(out, exist_ok=True)
F, fps, info = load_gray(a.video); N = len(F); dur = N / fps
frac, _ = activity(F, fps)
def ff(args, dst):
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + args + ["-frames:v", "1", "-vsync", "0", dst], check=True); print(dst)
def tile(cols, count): return f"tile={cols}x{max(1, math.ceil(count / cols))}"
cw = 270 if info["h"] >= info["w"] else 400
ff(["-t", "2", "-i", a.video, "-vf", f"fps=6,scale={cw}:-1,tile=6x2"], f"{out}/hook.png")
ff(["-i", a.video, "-vf", f"fps=1,scale=360:-1,{tile(5, math.ceil(dur))}"], f"{out}/phone.png")
ff(["-i", a.video, "-vf", f"fps=2,scale={cw}:-1,{tile(8, math.ceil(dur * 2))}"], f"{out}/contact.png")
# 3 biggest moments, at least 1.5 s apart (smoothed activity)
sm = np.convolve(frac, np.ones(max(1, int(fps * 0.15))) / max(1, int(fps * 0.15)), mode="same"); picks = []
for i in np.argsort(sm)[::-1]:
    if all(abs(i - j) / fps > 1.5 for j in picks): picks.append(int(i))
    if len(picks) == 3: break
for n, i in enumerate(sorted(picks), 1):
    t0 = max(0.0, i / fps - 0.1)
    ff(["-ss", f"{t0:.3f}", "-i", a.video, "-vf", f"scale={cw}:-1,tile=6x2"], f"{out}/strip-{n}.png")
    print(f"   strip-{n}: {t0:.2f}-{t0 + 12 / fps:.2f} s")
ff(["-i", a.video, "-vf", f"select='lt(n\\,3)+gte(n\\,{N - 3})',scale={cw}:-1,tile=6x1"], f"{out}/seam.png")
