#!/usr/bin/env python3
"""Paint any instants of a ui-morph-loop as PNGs in ~1 s each, with NO video render (the film is a pure function of t).
Use it for the storyboard/still gate, for checking a fix, and to look at exact frames around a click or a morph.

usage: still.py [--project .] (--t 9.5 ... | --beat 17 ...) [--out snapshots] [--sheet]
  --t / --beat accept several values; --sheet also tiles all of them into snapshots/stills-sheet.png (needs ffmpeg)
"""
import argparse, glob, json, os, re, subprocess, sys
ap = argparse.ArgumentParser()
ap.add_argument("--project", default="."); ap.add_argument("--t", type=float, nargs="*", default=[]); ap.add_argument("--beat", type=float, nargs="*", default=[])
ap.add_argument("--out", default="snapshots"); ap.add_argument("--sheet", action="store_true"); ap.add_argument("--bpm", type=float)
a = ap.parse_args()
ROOT = os.path.abspath(a.project); OUT = os.path.join(ROOT, a.out); os.makedirs(OUT, exist_ok=True)
html = open(os.path.join(ROOT, "index.html")).read()
W = int(re.search(r'data-width="(\d+)"', html).group(1)); H = int(re.search(r'data-height="(\d+)"', html).group(1))
film = open(os.path.join(ROOT, "film.js")).read()
bpm = a.bpm or float(re.search(r"bpm:\s*([0-9.]+)", film).group(1))
off = float((re.search(r"offset:\s*([0-9.]+)", film) or [0, 0])[1]) if re.search(r"offset:\s*([0-9.]+)", film) else 0.0
times = list(a.t) + [off + b * 60.0 / bpm for b in a.beat]
if not times: sys.exit("give --t or --beat")
def chrome():
    if os.environ.get("HF_CHROME"): return os.environ["HF_CHROME"]
    c = sorted(glob.glob(os.path.expanduser("~/.cache/puppeteer/chrome-headless-shell/*/*/chrome-headless-shell")))
    return c[-1] if c else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
files = []
for t in times:
    f = os.path.join(OUT, f"still-{t:07.3f}.png")
    subprocess.run([chrome(), "--headless", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files", "--hide-scrollbars", f"--window-size={W},{H}",
                    "--virtual-time-budget=3000", f"--screenshot={f}", f"file://{ROOT}/index.html?t={t}"], capture_output=True, timeout=60)
    print(f); files.append(f)
if a.sheet and len(files) > 1:
    cols = min(8, len(files)); rows = (len(files) + cols - 1) // cols
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for f in files: cmd += ["-i", f]
    inputs = "".join(f"[{i}:v]scale=240:-1[s{i}];" for i in range(len(files)))
    lay = "|".join(f"{(i % cols) * 240}_{(i // cols) * int(240 * H / W)}" for i in range(len(files)))
    cmd += ["-filter_complex", f"{inputs}" + "".join(f"[s{i}]" for i in range(len(files))) + f"xstack=inputs={len(files)}:layout={lay}", "-frames:v", "1", os.path.join(OUT, "stills-sheet.png")]
    subprocess.run(cmd); print(os.path.join(OUT, "stills-sheet.png"))
