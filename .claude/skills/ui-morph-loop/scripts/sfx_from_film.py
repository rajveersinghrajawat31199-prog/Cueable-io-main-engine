#!/usr/bin/env python3
"""Build the sound track for a ui-morph-loop from the SAME score as the picture (film.js): one cue per click, plus each state's
`sfx:[{dt,name,vol}]`. Sounds come from the studio's curated, level-capped palette (launch-video/scripts/sfx_palette.json,
files under ~/hyperframes-assets/sfx). Light UI taps/pops/slides only; nothing at t=0; no music (ask first, use measure_music.py).

usage: sfx_from_film.py [--project .] [--mount]
  writes assets/sfx/mix.wav (silent-padded to the film length) and prints the cue table.
  --mount adds <audio id="sfx-mix" ...> to index.html's root so render + critic see it.
"""
import argparse, glob, json, os, re, subprocess, sys
ap = argparse.ArgumentParser(); ap.add_argument("--project", default="."); ap.add_argument("--mount", action="store_true"); a = ap.parse_args()
ROOT = os.path.abspath(a.project); HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.expanduser("~/hyperframes-assets/sfx")
PAL = None
for cand in [os.path.join(HERE, "sfx_palette.json"), os.path.join(HERE, "../../launch-video/scripts/sfx_palette.json"), os.path.join(ROOT, "../../.claude/skills/launch-video/scripts/sfx_palette.json")]:
    if os.path.exists(cand): PAL = json.load(open(cand))["palette"]; break
if PAL is None: sys.exit("sfx_palette.json not found (expected in launch-video/scripts)")

def chrome():
    if os.environ.get("HF_CHROME"): return os.environ["HF_CHROME"]
    c = sorted(glob.glob(os.path.expanduser("~/.cache/puppeteer/chrome-headless-shell/*/*/chrome-headless-shell")))
    return c[-1] if c else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
out = subprocess.run([chrome(), "--headless", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files", "--virtual-time-budget=4000", "--dump-dom",
                      f"file://{ROOT}/index.html?report=1"], capture_output=True, text=True, timeout=60).stdout
m = re.search(r'<pre id="morph-report">(.*?)</pre>', out, re.S)
if not m: sys.exit("no report from the page")
R = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")); cues = R["cues"]; DUR = R["dur"]
if not cues: sys.exit("film has no cues: add sfx:[...] to states / cursor.clickSfx")
bad = [c for c in cues if c["t"] < 0.05 or c["t"] > DUR - 0.05]
if bad: sys.exit(f"cue outside 0.05..DUR-0.05 s (no SFX at t=0, none across the loop point): {bad}")

def resolve(e):
    p = os.path.join(LIB, e["file"]) if "file" in e else (glob.glob(os.path.join(LIB, e["glob"])) or [None])[0]
    if not p or not os.path.exists(p): sys.exit(f"SFX file missing: {e}")
    return p
os.makedirs(os.path.join(ROOT, "assets", "sfx"), exist_ok=True)
inputs, filters, labels = [], [], []
for i, c in enumerate(cues):
    e = PAL.get(c["name"]) or sys.exit(f"unknown SFX name '{c['name']}' (palette: {', '.join(PAL)})")
    vol = min(float(c.get("vol") or 0.3), e["cap"]); pitch = e.get("pitch", 1.0)
    inputs += ["-t", str(e.get("dur", 0.9)), "-i", resolve(e)]
    ms = int(round(c["t"] * 1000))
    af = (f"asetrate=44100*{pitch},aresample=44100," if pitch != 1.0 else "") + f"aformat=channel_layouts=mono:sample_rates=44100,afade=t=out:st={e.get('fade_st', 0.5)}:d={e.get('fade_d', 0.4)},volume={vol},adelay={ms}|{ms}"
    filters.append(f"[{i}:a]{af}[a{i}]"); labels.append(f"[a{i}]")
graph = ";".join(filters) + f";{''.join(labels)}amix=inputs={len(cues)}:normalize=0,apad=whole_dur={DUR},atrim=0:{DUR}[m]"
dst = os.path.join(ROOT, "assets", "sfx", "mix.wav")
subprocess.check_call(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", graph, "-map", "[m]", "-ar", "44100", "-ac", "1", dst])
pk = re.search(r"max_volume: ([-\d.]+) dB", subprocess.run(["ffmpeg", "-hide_banner", "-i", dst, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr)
print(f"{len(cues)} cues -> {dst}  (peak {pk.group(1) if pk else '?'} dBFS)")
for c in cues: print(f"  {c['t']:7.3f}s  {c['name']:7}  vol {c.get('vol')}")
if a.mount:
    p = os.path.join(ROOT, "index.html"); h = open(p).read()
    if 'id="sfx-mix"' not in h:
        tag = f'  <audio id="sfx-mix" src="assets/sfx/mix.wav" data-start="0" data-duration="{DUR}" data-volume="1"></audio>\n'
        h = h.replace('  <div id="stage">', tag + '  <div id="stage">', 1); open(p, "w").write(h); print("mounted <audio id=sfx-mix> in index.html")
