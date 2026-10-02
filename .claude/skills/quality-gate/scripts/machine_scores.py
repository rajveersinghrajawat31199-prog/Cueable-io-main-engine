#!/usr/bin/env python3
"""Machine-scored axes for ANY rendered video (0-10, from a format profile's score curves). Deterministic, ~5 s, no model.

  hook       first real change (>= event_frac of pixels moving; an idle pulse does not count)
  dead_time  longest near-still run
  variety    longest gap between real events (start -> events -> end)
  loop_seam  last->first step vs ordinary steps at the seam        (profile.loop)
  beat_alive share of beats with visible change                    (--bpm or profile.bpm)
  technical  hyperframes lint/layout/contrast                      (--run-check)
  flashes    whole-frame brightness pulses (white flash / strobe): any = FAIL unless the profile allows N  (scripts/flash_check.py)
  audio      video-critique numbers (levels, density, opening)     (only if the file has audio)

usage: machine_scores.py renders/final.mp4 [--profile ui-morph-loop] [--project .] [--bpm N] [--run-check] [--out quality/machine.json]
"""
import argparse, json, os, re, subprocess, sys, time
import numpy as np
from qg_common import load_gray, activity, curve, load_profile

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--profile", default="default"); ap.add_argument("--project", default=".")
ap.add_argument("--bpm", type=float); ap.add_argument("--run-check", action="store_true"); ap.add_argument("--out")
a = ap.parse_args()
P = load_profile(a.profile); M = P["machine"]; project = os.path.abspath(a.project)
out = a.out or os.path.join(project, "quality", "machine.json"); os.makedirs(os.path.dirname(out), exist_ok=True)

F, fps, info = load_gray(a.video); dur = len(F) / fps
frac, mean = activity(F, fps)
axes = {}
def put(k, score, value, unit, note=""): axes[k] = {"score": round(max(0.0, min(10.0, score)), 1), "value": None if value is None else round(float(value), 3), "unit": unit, "note": note}

# events = clusters of frames where a real share of the frame changes
ev = np.where(frac >= M["hook"]["event_frac"])[0]; starts = []
for i in ev:
    if not starts or i / fps - starts[-1] > 0.5: starts.append(i / fps)
hook_t = starts[0] if starts else None
put("hook", curve(hook_t, M["hook"]["curve"]) if hook_t is not None else 0, hook_t, "s to first real change", "" if hook_t is not None else "nothing ever changes by this measure")

still = frac < M["dead_time"]["still_frac"]; run = best = 0
_tail = int(M["dead_time"].get("tail_exempt_s", 0) * fps)                    # a deliberate end-card hold (profile opt-in) is not dead time
if _tail: still = still[:-_tail]
for s in still:
    run = run + 1 if s else 0; best = max(best, run)
put("dead_time", curve(best / fps, M["dead_time"]["curve"]), best / fps, "s longest still run")

vthr = M["variety"].get("event_frac", M["hook"]["event_frac"]); vst = []           # variety counts ANY real new event (typing, a count, a draw), so its bar is lower than the hook's
for i in np.where(frac >= vthr)[0]:
    if not vst or i / fps - vst[-1] > 0.5: vst.append(i / fps)
pts = [0.0] + vst + [dur]; gap = max(b - a_ for a_, b in zip(pts, pts[1:]))
put("variety", curve(gap, M["variety"]["curve"]), gap, "s longest gap between events", f"{len(vst)} events at >= {vthr * 100:.1f}% of pixels moving")

# restraint (opt-in per profile): how much of the frame is covered, and how many separate things move at once.
# coverage = share of pixels that differ from the canvas (the per-frame most common grey); movers = separate moving blobs per step.
if "coverage" in M or "movers" in M:
    from scipy import ndimage
    if "coverage" in M:
        cov = np.empty(len(F))
        for i, fr in enumerate(F):
            mode = np.bincount(fr.astype(np.uint8).ravel(), minlength=256).argmax()
            cov[i] = (np.abs(fr - mode) > M["coverage"].get("thr", 4)).mean()
        q = float(np.percentile(cov, M["coverage"].get("pct", 90)))
        put("coverage", curve(q, M["coverage"]["curve"]), q * 100, f"% of frame covered (p{M['coverage'].get('pct', 90)})", f"mean {cov.mean() * 100:.0f}%, peak {cov.max() * 100:.0f}% at {cov.argmax() / fps:.1f}s")
    if "movers" in M:
        K = max(1, int(round(fps / 30))); D = np.abs(F[K:] - F[:-K]) > M["movers"].get("thr", 5); px = F.shape[1] * F.shape[2]
        min_area = M["movers"].get("min_area", 0.0015) * px; cnt = np.zeros(len(D))
        for i, m in enumerate(D):
            if m.sum() < min_area: continue
            lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=M["movers"].get("merge", 4)))
            cnt[i] = int((np.bincount(lab.ravel())[1:] >= min_area).sum())
        w = max(1, int(round(M["movers"].get("window_s", 3.0) * fps))); roll = np.convolve(cnt, np.ones(w) / w, "valid") if len(cnt) >= w else cnt
        q = float(roll.max()); t_at = float(roll.argmax() / fps)
        put("movers", curve(q, M["movers"]["curve"]), q, f"separate things moving at once (busiest {M['movers'].get('window_s', 3.0):g}s window, mean)", f"busiest at {t_at:.1f}-{t_at + M['movers'].get('window_s', 3.0):g}s; whole-film mean {cnt.mean():.1f}, p90 {np.percentile(cnt, 90):.0f}")

if P.get("loop"):
    seam = float(np.abs(F[-1] - F[0]).mean()); k = int(fps * 0.5)
    near = float(np.concatenate([mean[:k], mean[-k:]]).max())
    ratio = seam / max(near, 0.05)
    put("loop_seam", curve(ratio, M["loop_seam"]["curve"]), ratio, "x ordinary step (lower is better)", f"seam {seam:.3f} vs {near:.3f}")

bpm = a.bpm or P.get("bpm")
if bpm:
    spb = 60.0 / bpm; nb = int(dur / spb); alive = 0
    for b in range(nb):
        i0, i1 = int(b * spb * fps), min(len(frac), int((b + 1) * spb * fps))
        alive += i1 > i0 and frac[i0:i1].mean() >= M["dead_time"]["still_frac"]
    put("beat_alive", curve(alive / nb, M["beat_alive"]["curve"]), alive / nb, "share of beats alive", f"{nb - alive} dead of {nb}")

# flashes: any whole-frame brightness pulse (a 'white flash' / strobe) is a defect unless the profile explicitly allows it (machine.flashes.allow = N events)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flash_check import find_flashes
_fl = find_flashes(a.video); _allow = P["machine"].get("flashes", {}).get("allow", 0); _n = max(0, len(_fl) - _allow)
put("flashes", 10 - 5 * _n, len(_fl), "whole-frame brightness pulses", "none" if not _fl else "at " + ", ".join(f"{e['t']}s" for e in _fl[:8]) + (" ..." if len(_fl) > 8 else "") + f" (allowed {_allow}); customers see these as a white flash")

if a.run_check:
    ver = re.search(r"hyperframes@([\d.]+)", open(os.path.join(project, "package.json")).read()).group(1) if os.path.exists(os.path.join(project, "package.json")) else "latest"
    t0 = time.time(); r = subprocess.run(["npx", "--yes", f"hyperframes@{ver}", "check"], cwd=project, capture_output=True, text=True, env=dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1"))
    ok = "Check passed" in r.stdout + r.stderr
    put("technical", 10 if ok else 0, 1 if ok else 0, "check passed", f"hyperframes@{ver} check in {time.time() - t0:.0f}s")

if info["audio"]:
    crit = os.path.expanduser("~/.claude/skills/video-critique/scripts/critique.py")
    if os.path.exists(crit):
        r = subprocess.run([sys.executable, crit, a.video, "--project", project, "--no-sheets"] + P["machine"].get("audio", {}).get("critic_args", []), capture_output=True, text=True)   # critic_args: e.g. --allow-edge for films whose plates are full-bleed on purpose
        ign = P["machine"].get("audio", {}).get("ignore", [])   # warning classes the format's playbook declares intentional (profile says why)
        warn_lines = [l for l in r.stdout.splitlines() if l.startswith("[WARN]")]
        kept = [l for l in warn_lines if not any(x in l for x in ign)]
        f_, w_ = len(re.findall(r"\[FAIL\]", r.stdout)), len(kept)
        if r.returncode in (0, 1) and "SUMMARY" in r.stdout:
            put("audio", 10 - 4 * f_ - 0.5 * w_, f_, "FAIL count", f"{f_} FAIL, {w_} WARN counted, {len(warn_lines) - len(kept)} intended WARN discounted per profile (numbers only: never heard)")
        else: axes["audio"] = {"score": None, "value": None, "unit": "", "note": "critic could not run: " + (r.stderr.strip().splitlines() or ["?"])[-1][:80]}
else:
    axes["audio"] = {"score": None, "value": None, "unit": "", "note": "silent film: no audio axis"}

res = {"video": os.path.abspath(a.video), "profile": a.profile, "dur": round(dur, 2), "fps": fps, "size": [info["w"], info["h"]], "axes": axes, "generated": time.strftime("%Y-%m-%d %H:%M:%S")}
json.dump(res, open(out, "w"), indent=1)
print(f"{os.path.basename(a.video)}  {dur:.1f}s  profile={a.profile}")
for k, v in axes.items():
    sc = "  n/a" if v["score"] is None else f"{v['score']:5.1f}"
    val = "" if v["value"] is None else f"{v['value']} {v['unit']}"
    print(f"  {k:11} {sc}   {val}  {v['note']}")
print(f"wrote {out}")
