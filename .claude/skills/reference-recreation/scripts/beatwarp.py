#!/usr/bin/env python3
"""Beat warp: nudge the reference's key hits onto the music's beat grid by at most N frames (what the Pinterest film did by hand).

  python3 beatwarp.py --spec motion-spec.json --bpm 90 [--grid-div 2] [--phase 0] [--max-shift 5] [--out warp.json] [--keys 30,90,246]

Key hits = hard cuts, big appearances, pointer presses and the first typed character (or --keys). Film frame 0 is a bar line unless --phase says otherwise.
The grid is every beat/grid-div (default: 8th notes: 10 frames at 90 bpm, 30 fps). Output: [[ref_frame, film_frame], ...] (piecewise linear),
usable by build_from_spec.py --warp and fidelity.py --warp. Prints each nudge and the stretch it causes between neighbours.
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--bpm", type=float, required=True)
    ap.add_argument("--grid-div", type=int, default=2)
    ap.add_argument("--phase", type=float, default=0.0, help="film frame of the first grid line")
    ap.add_argument("--max-shift", type=int, default=5)
    ap.add_argument("--out", default="warp.json")
    ap.add_argument("--keys")
    ap.add_argument("--from", dest="f_from", type=int)
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    fps = spec["source"]["fps"]
    step = fps * 60.0 / a.bpm / a.grid_div
    f0 = spec["measured"][0] if a.f_from is None else a.f_from
    f1 = spec["measured"][1]
    cands = {}                                                # frame -> importance
    if a.keys:
        for k in a.keys.split(","):
            cands[int(k)] = 5.0
    else:
        for e in spec["events"]:
            k, imp = int(e["frame"]), 0.0
            if e["kind"] == "cut":
                imp = 3.0
            elif e["kind"] == "press":
                imp = 2.5
            elif e["kind"] == "appear" and e.get("role") in ("card", "photo"):
                imp = 1.5
            elif e["kind"] == "typing":
                imp = 1.2
            if imp:
                cands[k] = max(cands.get(k, 0), imp)
    # greedy by importance: accept a key only if the nudge is small, the keys are not crowded and no segment gets stretched beyond [lo, hi]
    chosen = {f0: 0.0, f1 + 1: float(f1 + 1 - f0)}            # ref frame -> film frame
    lo, hi = 0.8, 1.25
    for k, imp in sorted(cands.items(), key=lambda kv: (-kv[1], kv[0])):
        if k <= f0 + 1 or k >= f1:
            continue
        rel = k - f0
        g = float(round(round((rel - a.phase) / step) * step + a.phase))
        if abs(g - rel) > a.max_shift:
            continue
        trial = dict(chosen)
        trial[k] = g
        ks = sorted(trial)
        ok = all(b - a_ >= 12 for a_, b in zip(ks, ks[1:])) and all(lo <= (trial[b] - trial[a_]) / float(b - a_) <= hi for a_, b in zip(ks, ks[1:]))
        if ok:
            chosen = trial
    pts = [[k, chosen[k]] for k in sorted(chosen)]
    # the warp as (ref, film) with film relative to the first measured frame; ref frames absolute
    out = [[int(r), float(g)] for r, g in pts]
    json.dump(out, open(a.out, "w"))
    print("grid every %.2f frames; %d key hits nudged:" % (step, len(out) - 2))
    for (r0, g0), (r1, g1) in zip(out, out[1:]):
        stretch = (g1 - g0) / float(r1 - r0) if r1 > r0 else 1.0
        print("  ref f%-4d -> film f%-5.0f (shift %+d)   segment stretch x%.2f" % (r1, g1, round(g1 - (r1 - f0)), stretch))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
