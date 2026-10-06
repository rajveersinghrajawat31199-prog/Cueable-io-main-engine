#!/usr/bin/env python3
"""Snapshot scenes of a recomposed project at scene-relative times and tile them into one sheet.
  snap.py --dst videos/P-9x16 [--scene 04 ...] [--rel 0.5,2,3.9 | --n 3] [--out DIR]
Default: every scene, 3 evenly spaced times (15%, 55%, 95%). Prints the sheet path; look at it."""
import argparse, glob, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from recompose import scenes_of
ap = argparse.ArgumentParser(); ap.add_argument("--dst", required=True); ap.add_argument("--scene", nargs="*"); ap.add_argument("--rel"); ap.add_argument("--out", default="/tmp/aspect-snap")
a = ap.parse_args()
idx = open(f"{a.dst}/index.html").read()
rows = []
for s, st, du in scenes_of(idx):
    n = os.path.basename(s)[:-5]
    if a.scene and not any(n.startswith(x) for x in a.scene): continue
    rel = [float(x) for x in a.rel.split(",")] if a.rel else [du*.15, du*.55, du*.95]
    rows.append((n, [round(st + min(r, du - .05), 3) for r in rel], rel))
os.makedirs(a.out, exist_ok=True)
for f in glob.glob(a.out + "/*.png"): os.remove(f)
allt = sorted({t for _, ts, _ in rows for t in ts})
subprocess.run(["npx", "--yes", "hyperframes@0.8.72", "snapshot", a.dst, "--at", ",".join(map(str, allt)), "--no-end", "-o", a.out, "--describe", "false"], capture_output=True)
files = {}
for f in glob.glob(a.out + "/*.png"):
    m = re.search(r"([\d.]+)s?\.png$", f) or re.search(r"(\d+(?:\.\d+)?)", os.path.basename(f))
    files[f] = float(m.group(1))
def find(t):
    return min(files, key=lambda f: abs(files[f] - t))
from PIL import Image, ImageDraw
for n, ts, rel in rows:
    ims = [Image.open(find(t)).convert("RGB") for t in ts]
    h = 960; ims = [i.resize((int(i.width * h / i.height), h)) for i in ims]
    W = sum(i.width for i in ims) + 12 * (len(ims) - 1)
    sh = Image.new("RGB", (W, h), (60, 60, 60)); x = 0
    for i, r in zip(ims, rel):
        sh.paste(i, (x, 0)); ImageDraw.Draw(sh).text((x + 8, 6), f"{n} @{r:.2f}s", fill=(255, 0, 0)); x += i.width + 12
    p = f"{a.out}/sheet_{n}.jpg"; sh.save(p, quality=88); print(p)
