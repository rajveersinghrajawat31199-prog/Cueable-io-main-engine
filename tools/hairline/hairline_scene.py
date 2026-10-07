#!/usr/bin/env python3
"""Hairline figure beats for launch/demo films: pick, install, generate. No manual steps.

  hairline_scene.py pick "<brief / script text>" [--top 4]
      Ranks the 27 figures by how well their `fits` keywords match the text. Prints figure, shelf, score, what it says.

  hairline_scene.py make --project videos/<p> --figure laptop --start 12.0 --dur 4.5 \
        --box 560,300,800 --plate "#0b0b0e" --hi "#f2f2f5" [--edge --mid --lo] [--stroke 2.4] \
        [--intensity 0.7] [--theme dark|light] [--id hl1] [--at-cursor]
      1. installs assets/hairline.bundle.js into the project (idempotent)
      2. writes assets/hairline/<id>.html : a ready fragment (markup + CSS + the scene.add call)
         plus <id>.json : placement, path in seconds, and the cursor path in frame pixels
         (when --at-cursor), for /oversized-cursor so cursor and figure agree.
      The fragment is the same code as tools/hairline/example/index.html (proven in a render).
      Remember the one rule: Hairline.scene() once per composition, call H.bind(tl, total) last.
"""
import argparse, json, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_SCORE = 4  # two keyword hits (or the figure named); one stray word is not a metaphor
G = json.loads((HERE / "gestures.json").read_text())


def pick(text, top):
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    low = text.lower()
    rows = []
    for name, g in G.items():
        score = sum(2 if (f in words or f in low) and " " not in f else (2 if f in low else 0) for f in g["fits"])
        if name in words:
            score += 3
        rows.append((score, name, g))
    rows.sort(key=lambda r: (-r[0], r[1]))
    shown = [r for r in rows[:top] if r[0] >= MIN_SCORE]
    if not shown:
        print("no figure matches this story; do not force one (a figure needs a metaphor beat).")
        return
    for s, n, g in shown:
        print(f"{n:10s} score {s:2d}  [{g['shelf']}]  {g['says']}")


def make(a):
    g = G.get(a.figure)
    if not g:
        sys.exit(f"unknown figure {a.figure}; known: {', '.join(G)}")
    proj = Path(a.project)
    if not proj.is_dir():
        sys.exit(f"no such project {proj}")
    (proj / "assets").mkdir(exist_ok=True)
    shutil.copy(HERE / "dist" / "hairline.bundle.js", proj / "assets" / "hairline.bundle.js")
    out = proj / "assets" / "hairline"  # not compositions/: the linter treats every file there as a composition
    out.mkdir(exist_ok=True)

    bx, by, bw = [float(v) for v in a.box.split(",")]
    bh = bw * 0.8  # figures are 5:4 (viewBox 400x320)
    path = [{"t": round(a.start + u * a.dur, 3), "x": x, "y": y} for u, x, y in g["path"]]
    path.append({"t": round(a.start + g["leave_at"] * a.dur, 3), "leave": True})
    plate, hi = a.plate, a.hi
    # tones derived from the brand: mix the highlight colour into the plate at 55/32/14 %
    def mix(c1, c2, w):
        c1, c2 = c1.lstrip("#"), c2.lstrip("#")
        v = [round(int(c1[k:k + 2], 16) * (1 - w) + int(c2[k:k + 2], 16) * w) for k in (0, 2, 4)]
        return "#%02x%02x%02x" % tuple(v)
    edge, mid, lo = a.edge or mix(plate, hi, .55), a.mid or mix(plate, hi, .32), a.lo or mix(plate, hi, .14)
    i = a.id or f"hl-{a.figure}"
    html = f"""<!-- Hairline beat: {a.figure} ({g['says']}) -->
<style>
#{i}{{position:absolute;left:{bx:g}px;top:{by:g}px;width:{bw:g}px;height:{bh:g}px;
 --hairline-plate:{plate};--hairline-hi:{hi};--hairline-edge:{edge};--hairline-mid:{mid};--hairline-lo:{lo};--hairline-stroke:{a.stroke}}}
</style>
<div id="{i}" class="clip" data-start="{a.start:g}" data-duration="{a.dur:g}"></div>
<script>
  // needs assets/hairline.bundle.js loaded before this block (a script tag in the page head)
  window.__HL = window.__HL || Hairline.scene();   // ONE scene per composition
  window.__HL.add("#{i}", "{a.figure}", {{ theme:"{a.theme}", intensity:{a.intensity},
    path:{json.dumps(path)} }});
  // after ALL beats are added, once: window.__HL.bind(tl, TOTAL_SECONDS)
</script>
"""
    (out / f"{i}.html").write_text(html)

    # cursor path in frame pixels, sampled at 10 Hz with the same smoothstep the driver uses
    def at(t):
        pts = path
        if t < pts[0]["t"]:
            return None
        a0 = pts[0]
        for b in pts[1:]:
            if t < b["t"]:
                if b.get("leave"):
                    return a0["x"], a0["y"]
                u = (t - a0["t"]) / max(1e-6, b["t"] - a0["t"])
                u = u * u * (3 - 2 * u)
                return a0["x"] + (b["x"] - a0["x"]) * u, a0["y"] + (b["y"] - a0["y"]) * u
            if b.get("leave"):
                return None
            a0 = b
        return a0["x"], a0["y"]

    cur, t = [], path[0]["t"]
    end = path[-1]["t"]
    while t <= end:
        p = at(t)
        if p:
            cur.append({"t": round(t, 2), "px": round(bx + p[0] * bw, 1), "py": round(by + p[1] * bh, 1)})
        t += 0.1
    meta = {"figure": a.figure, "box": {"x": bx, "y": by, "w": bw, "h": bh}, "start": a.start, "dur": a.dur,
            "path": path, "cursor_px": cur if a.at_cursor else None}
    (out / f"{i}.json").write_text(json.dumps(meta, indent=1))
    print(f"installed assets/hairline.bundle.js; wrote assets/hairline/{i}.html (+ .json)"
          + (f"; cursor path {len(cur)} points" if a.at_cursor else ""))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick"); p.add_argument("text"); p.add_argument("--top", type=int, default=4)
    m = sub.add_parser("make")
    m.add_argument("--project", required=True); m.add_argument("--figure", required=True)
    m.add_argument("--start", type=float, required=True); m.add_argument("--dur", type=float, required=True)
    m.add_argument("--box", required=True, help="x,y,width in frame px (height = 0.8*width)")
    m.add_argument("--plate", required=True); m.add_argument("--hi", required=True)
    m.add_argument("--edge"); m.add_argument("--mid"); m.add_argument("--lo")
    m.add_argument("--stroke", type=float, default=2.4); m.add_argument("--intensity", type=float, default=0.7)
    m.add_argument("--theme", default="dark"); m.add_argument("--id")
    m.add_argument("--at-cursor", action="store_true")
    a = ap.parse_args()
    pick(a.text, a.top) if a.cmd == "pick" else make(a)


if __name__ == "__main__":
    main()
