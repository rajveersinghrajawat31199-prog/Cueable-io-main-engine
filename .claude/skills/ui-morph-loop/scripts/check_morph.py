#!/usr/bin/env python3
"""Structural check of a ui-morph-loop project BEFORE rendering (no video needed, ~2 s).

Loads index.html in headless Chrome with ?report, reads window.__morphReport from lib/morph.js and grades it:
  loop:   first state == last state (geometry, fill, layer); last morph has settled by t=DUR (residual);
          cursor parked off-screen at both ends; shape ends match to sub-pixel
  grid:   states on half-beat boundaries; every click has a state change on the same beat

usage: check_morph.py [--project .]           exit 1 on any FAIL
"""
import glob, json, os, re, subprocess, sys

args = sys.argv[1:]
ROOT = os.path.abspath(args[args.index("--project") + 1]) if "--project" in args else os.getcwd()
fails = warns = 0

def say(level, msg):
    global fails, warns
    fails += level == "FAIL"; warns += level == "WARN"
    print(f"{level:4}  {msg}")

def chrome():
    if os.environ.get("HF_CHROME"): return os.environ["HF_CHROME"]
    c = sorted(glob.glob(os.path.expanduser("~/.cache/puppeteer/chrome-headless-shell/*/*/chrome-headless-shell")))
    if c: return c[-1]
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    return mac if os.path.exists(mac) else None

bin_ = chrome()
if not bin_: sys.exit("no headless Chrome found (set HF_CHROME, or run: npx hyperframes browser ensure)")
url = "file://" + os.path.join(ROOT, "index.html") + "?report=1"
out = subprocess.run([bin_, "--headless", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files",
                      "--virtual-time-budget=4000", "--dump-dom", url], capture_output=True, text=True, timeout=60).stdout
m = re.search(r'<pre id="morph-report">(.*?)</pre>', out, re.S)
if not m: sys.exit("no report in the page: did film.js call HFMorph.build(FILM)? (open index.html?report in a browser and read the console)")
R = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&"))
L = R["loop"]

print(f"{R['states']} states · {R['dur']} s · {R['bpm']} bpm · {'measured' if R['measuredGrid'] else 'nominal'} beat grid")
say("PASS" if L["sameGeometry"] else "FAIL", "last state has the SAME geometry + fill as the first (the loop closes)" if L["sameGeometry"] else "last state geometry/fill differs from the first: the loop will pop")
say("PASS" if L["sameLayer"] else "FAIL", "last state reuses the first state's content layer" if L["sameLayer"] else "last state uses a different content layer than the first")
res = L["lastMorphResidual"]
say("PASS" if res < 0.005 else "WARN" if res < 0.02 else "FAIL", f"last morph residual at t=DUR is {res*100:.2f}% (want < 0.5%: start the last morph earlier if not)")
say("PASS" if L["cursorOffscreenAtStart"] and L["cursorOffscreenAtEnd"] else "FAIL", "cursor is off-screen at both ends" if L["cursorOffscreenAtStart"] and L["cursorOffscreenAtEnd"] else "cursor is on-screen at the start or end of the loop")
d = L["endsDelta"]; mx = max(d.values())
say("PASS" if mx < 0.5 else "FAIL", f"shape at t=0 vs t=DUR differs by {mx:.2f}px (want < 0.5)")
say("PASS" if not R["offBeatStates"] else "WARN", "every state starts on a half-beat" if not R["offBeatStates"] else f"states off the half-beat grid: {', '.join(R['offBeatStates'])}")
say("PASS" if R["clicksBeforeMorph"] is True else "FAIL", "every click ignites a state change on its beat" if R["clicksBeforeMorph"] is True else str(R["clicksBeforeMorph"]))
print(f"\nSUMMARY: {fails} FAIL, {warns} WARN")
sys.exit(1 if fails else 0)
