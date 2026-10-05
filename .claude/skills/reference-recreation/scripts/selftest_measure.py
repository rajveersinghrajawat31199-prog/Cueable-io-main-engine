#!/usr/bin/env python3
"""Regression test for measure.py / refkit against numbers measured by hand on the Airbnb-style reel (tests/airbnb_reel_ground_truth.json).
  selftest_measure.py REFERENCE.MP4        (~1 min: measures frames 90-264 and compares)   exit 1 on any FAIL
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
gt = json.load(open(os.path.join(HERE, "..", "tests", "airbnb_reel_ground_truth.json")))
out = tempfile.mkdtemp(prefix="measure_selftest_")
subprocess.run([sys.executable, os.path.join(HERE, "measure.py"), sys.argv[1], "--out", out, "--frames", "90:264", "--ignore-box", "800,60,1080,260"], capture_output=True)
sp = json.load(open(os.path.join(out, "motion-spec.json")))
T = [t for t in sp["tracks"] if not t.get("junk")]
fails = 0


def check(name, ok, got, want):
    global fails
    fails += 0 if ok else 1
    print("%s  %-34s got %s  want %s" % ("PASS" if ok else "FAIL", name, got, want))


def box_at(t, f):
    f0, f1 = t["frames"]
    return t["boxes"][f - f0] if f0 <= f <= f1 else None


def best(f, pred):
    c = [(((b[2] - b[0]) * (b[3] - b[1])), t, b) for t in T if t["cls"] == "flat" for b in [box_at(t, f)] if b and pred(t, b)]
    return max(c, key=lambda x: x[0]) if c else None


pr = gt["pill_rest_box"]
for f in pr["frames"]:
    r = best(f, lambda t, b: (b[2] - b[0]) > 440 and (b[3] - b[1]) < 100)
    check("pill box f%d" % f, bool(r) and max(abs(a - b) for a, b in zip(r[2], pr["box"])) <= pr["tol_px"], r[2] if r else None, pr["box"])
w = []
for f in range(92, 109):
    r = best(f, lambda t, b: (b[2] - b[0]) > 440 and (b[3] - b[1]) < 100)
    w.append((r[2][2] - r[2][0]) if r else None)
want = gt["pill_settle_widths_f92_108"]
check("pill settle widths (max diff <= 3)", all(a is not None for a in w) and max(abs(a - b) for a, b in zip(w, want)) <= 3, w[:6], want[:6])
l = []
for f in range(217, 235):
    r = best(f, lambda t, b: (b[3] - b[1]) >= 560)
    l.append(r[2][0] if r else None)
want = gt["card_left_edge_f217_234"]
check("calendar card left edge (<= 2 px)", all(a is not None for a in l) and max(abs(a - b) for a, b in zip(l, want)) <= 2, l[:6], want[:6])
ty = [e for e in sp["events"] if e["kind"] == "typing"]
check("typing frames exact", bool(ty) and ty[0]["frames"][:10] == gt["typing_frames"][:10], ty[0]["frames"][:10] if ty else None, gt["typing_frames"][:10])
cur = {int(t[0]): t for t in (sp.get("cursor") or {}).get("track", [])}
truth = {}
for k in ("A", "B", "out"):
    for f, x, y in gt["cursor_tips"][k]:
        truth[f] = (x, y)
errs = [float(np.hypot(cur[f][1] - x, cur[f][2] - y)) for f, (x, y) in truth.items() if f in cur]
check("pointer found (>= 80% of truth)", len(errs) >= 0.8 * len(truth), "%d/%d" % (len(errs), len(truth)), ">= %d" % int(0.8 * len(truth)))
if errs:
    check("pointer tip error median/p90", np.median(errs) <= 2.0 and np.percentile(errs, 90) <= 4.0, "%.1f/%.1f px" % (np.median(errs), np.percentile(errs, 90)), "<= 2.0/4.0 px")
lo, hi = gt["cursor_interval_limit"]
stray = [f for f in cur if not (lo <= f <= hi)]
check("no pointer outside its real life", not stray, len(stray), 0)
role_ok = []
for name, rr in gt["roles"].items():
    r = best(rr["frame"], lambda t, b: abs(b[0] - rr["box"][0]) < 30 and abs(b[2] - rr["box"][2]) < 30)
    role_ok.append((name, r[1]["role"] if r else None))
check("roles (pill, card)", all(g == n for n, g in role_ok), role_ok, "pill, card")
print("\n%s (%d check(s) failed)" % ("OK" if not fails else "FAILED", fails))
sys.exit(1 if fails else 0)
