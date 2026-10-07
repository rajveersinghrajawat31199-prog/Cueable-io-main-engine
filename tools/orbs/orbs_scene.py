#!/usr/bin/env python3
"""thinking-orbs beats for launch/demo films of AI / agent products. No manual steps.

  orbs_scene.py pick "<brief text>"
      Needs an AI/agent/automation story (ai_gate words), else prints 'no orb'. Then ranks the 9 states and
      suggests a 3-state sequence (what the agent is doing, in story order).

  orbs_scene.py make --project videos/<p> --states "searching:0,solving:2.4,composing:4.8" --start 12 --dur 7 \
        --box 760,250,420 --ink "#ffffff" --bg "#0b0b0e" [--size 64|20] [--fade 0.3] [--id orb1]
      Installs assets/orbs.bundle.js and writes assets/orbs/<id>.html + <id>.json (box, timing). Paste the fragment
      into the beat's composition, load the bundle in <head> after GSAP, call window.__ORBS.bind(tl, TOTAL) ONCE last.
      --box is x,y,px (square, frame pixels). bg must be the colour behind the orb (far dots fade into it).
"""
import argparse, json, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "states.json").read_text())


def hit(f, words):
    """exact word, or a shared 5-letter stem (searches~search, reasons~reasoning, drafts~draft)"""
    return any(w == f or (len(w) >= 5 and len(f) >= 5 and w[:5] == f[:5]) for w in words)


def pick(text):
    low = text.lower(); words = set(re.findall(r"[a-z0-9-]+", low))
    if not any((g in words) or (" " in g and g in low) for g in D["ai_gate"]):
        print("no orb: not an AI / agent / automation story (the orb says 'something is thinking').")
        return
    rows = []
    for n, s in D["states"].items():
        sc = sum(1 for f in s["fits"] if hit(f, words)) + (2 if n in words else 0)
        rows.append((sc, n, s["says"]))
    rows.sort(key=lambda r: (-r[0], r[1]))
    top = [r for r in rows if r[0] >= 1][:4] or [(0, "working", D["states"]["working"]["says"])]
    for sc, n, says in top:
        print(f"{n:10s} score {sc}  {says}")
    seq = [r[1] for r in top[:3]]
    print("suggested sequence:", " -> ".join(seq), "(reorder to the story; 2-3 states, ~2.4 s each)")


def make(a):
    proj = Path(a.project)
    if not proj.is_dir():
        sys.exit(f"no such project {proj}")
    states = []
    for part in a.states.split(","):
        n, _, t = part.partition(":")
        if n not in D["states"]:
            sys.exit(f"unknown state {n}; known: {', '.join(D['states'])}")
        states.append({"t": float(t or 0), "state": n})
    (proj / "assets" / "orbs").mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "dist" / "orbs.bundle.js", proj / "assets" / "orbs.bundle.js")
    x, y, px = [float(v) for v in a.box.split(",")]
    i = a.id or "orb-" + states[0]["state"]
    html = f"""<!-- thinking-orb: {' -> '.join(s['state'] for s in states)} -->
<style>#{i}{{position:absolute;left:{x:g}px;top:{y:g}px;width:{px:g}px;height:{px:g}px}}</style>
<div id="{i}" class="clip" data-start="{a.start:g}" data-duration="{a.dur:g}"></div>
<script>
  // needs assets/orbs.bundle.js loaded before this block (a script tag in the page head)
  window.__ORBS = window.__ORBS || Orbs.scene();   // ONE scene per composition
  window.__ORBS.add("#{i}", {{ states:{json.dumps([{"t": round(a.start + s["t"], 3), "state": s["state"]} for s in states])},
    size:{a.size}, px:{px:g}, ink:"{a.ink}", bg:"{a.bg}", fade:{a.fade}, at:0 }});
  // after ALL beats are added, once: window.__ORBS.bind(tl, TOTAL_SECONDS)
</script>
"""
    (proj / "assets" / "orbs" / f"{i}.html").write_text(html)
    (proj / "assets" / "orbs" / f"{i}.json").write_text(json.dumps(
        {"figure": "orb:" + "+".join(s["state"] for s in states), "box": {"x": x, "y": y, "w": px, "h": px},
         "start": a.start, "dur": a.dur, "states": states}, indent=1))
    print(f"installed assets/orbs.bundle.js; wrote assets/orbs/{i}.html (+ .json)")


ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
p = sub.add_parser("pick"); p.add_argument("text")
m = sub.add_parser("make")
for k in ("project", "states", "box", "ink", "bg"): m.add_argument("--" + k, required=True)
m.add_argument("--start", type=float, required=True); m.add_argument("--dur", type=float, required=True)
m.add_argument("--size", type=int, default=64, choices=[64, 20]); m.add_argument("--fade", type=float, default=0.3)
m.add_argument("--id")
a = ap.parse_args()
pick(a.text) if a.cmd == "pick" else make(a)
