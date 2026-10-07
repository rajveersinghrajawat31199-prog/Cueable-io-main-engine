#!/usr/bin/env python3
"""Render gate for Hairline beats. FAILs a figure that is off-frame, never moves, or only moves in the first frames.

  check_figures.py <render.mp4> <project_dir> [assets/hairline | assets/orbs]

Reads <project>/assets/hairline/*.json (written by hairline_scene.py), grabs frames at start+0.05 s, mid-beat and
end-0.3 s, and counts changed pixels inside each figure's box. Needs ffmpeg and Pillow.
"""
import glob, json, subprocess, sys, tempfile, os
from PIL import Image, ImageChops

mp4, proj = sys.argv[1], sys.argv[2]
sub = sys.argv[3] if len(sys.argv) > 3 else "assets/hairline"
W, H = 1920, 1080
bad = 0
for jf in sorted(glob.glob(os.path.join(proj, sub, "*.json"))):
    m = json.load(open(jf)); b = m["box"]; name = os.path.basename(jf)[:-5]
    x0, y0, x1, y1 = int(b["x"]), int(b["y"]), int(b["x"] + b["w"]), int(b["y"] + b["h"])
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
        print(f"[FAIL] {name} ({m['figure']}): box {x0},{y0}-{x1},{y1} leaves the {W}x{H} frame"); bad += 1; continue
    ts = [m["start"] + .05, m["start"] + m["dur"] * .5, m["start"] + m["dur"] - .3]
    ims = []
    for t in ts:
        f = tempfile.mktemp(suffix=".png")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", mp4, "-frames:v", "1", f], check=True)
        ims.append(Image.open(f).convert("L").crop((x0, y0, x1, y1))); os.remove(f)
    ink = sum(1 for p in ims[0].getdata() if p > 60)
    ch = [sum(1 for p in ImageChops.difference(ims[0], im).getdata() if p > 40) for im in ims[1:]]
    if ink < 200:
        print(f"[FAIL] {name} ({m['figure']}): nothing drawn in its box (ink px {ink})"); bad += 1
    elif max(ch) < 150:
        print(f"[FAIL] {name} ({m['figure']}): figure never moves (changed px {ch}); check the pointer path / state timeline"); bad += 1
    else:
        print(f"[PASS] {name} ({m['figure']}): ink {ink}px, changed {ch}")
sys.exit(1 if bad else 0)
