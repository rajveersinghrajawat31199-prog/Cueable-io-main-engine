#!/usr/bin/env python3
"""Objective checks on a RENDERED ui-morph-loop MP4 (the machine half of the critique; taste is still yours).

  seam        last frame -> first frame must look like any other frame step (no pop at the loop point)
  dead beats  every beat window must contain visible change ("something happens on every beat")
  dead run    no stretch longer than --max-still seconds with (almost) no change
  determinism (optional) --compare other.mp4: two renders of the same project must be frame-identical

usage: check_loop.py renders/final.mp4 --bpm 120 [--offset 0] [--max-still 0.75] [--compare other.mp4] [--sheet]
exit 1 on any FAIL. Needs ffmpeg + numpy. Writes snapshots/beats.png (one frame per beat) with --sheet.
"""
import argparse, os, subprocess, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--bpm", type=float, required=True); ap.add_argument("--offset", type=float, default=0.0)
ap.add_argument("--max-still", type=float, default=0.75); ap.add_argument("--compare"); ap.add_argument("--sheet", action="store_true")
ap.add_argument("--hook-sec", type=float, default=1.0, help="the first real change (a morph, not a pulse) must start by this time"); ap.add_argument("--hook-px", type=float, default=1500)
ap.add_argument("--dead-px", type=float, default=20, help="pixels (of 216 wide) changing per frame below which a beat is 'dead'")
a = ap.parse_args()
fails = warns = 0
def say(level, msg):
    global fails, warns
    fails += level == "FAIL"; warns += level == "WARN"; print(f"{level:4}  {msg}")

def probe(v):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,width,height", "-of", "csv=p=0", v], capture_output=True, text=True).stdout.strip().split(",")
    n, d = o[2].split("/"); return int(o[0]), int(o[1]), float(n) / float(d)
W, H, FPS = probe(a.video)
w, h = 216, int(216 * H / W) // 2 * 2
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"scale={w}:{h}:flags=area,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
F = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
N = len(F); dur = N / FPS
print(f"{os.path.basename(a.video)}: {N} frames @ {FPS:g} fps = {dur:.2f} s, analysed at {w}x{h}")

D = np.abs(np.diff(F, axis=0))
K = max(1, int(round(FPS / 30)))                                    # compare frames 1/30 s apart so thresholds do not depend on the render fps
DK = np.abs(F[K:] - F[:-K])
step = D.mean(axis=(1, 2))                                          # mean change from frame i to i+1 (used for the seam)
act = (DK > 12).sum(axis=(1, 2)).astype(np.float32)                 # pixels visibly changing per 1/30 s (used for beats / still runs)
seam = float(np.abs(F[-1] - F[0]).mean())                          # last -> first (the loop step)
near = np.concatenate([step[:int(FPS * 0.5)], step[-int(FPS * 0.5):]])
limit = max(2.0 * float(near.max()), 0.25)
say("PASS" if seam <= limit else "FAIL", f"loop seam: last->first changes {seam:.3f} vs {float(near.max()):.3f} max ordinary step at the seam (limit {limit:.3f})")

hook = next((i / FPS for i in range(len(act)) if act[i] >= a.hook_px), None)
say("PASS" if hook is not None and hook <= a.hook_sec else "WARN", f"hook: first real change (>= {a.hook_px:g} px moving) at {hook:.2f} s (want <= {a.hook_sec:g} s)" if hook is not None else "hook: nothing ever changes by that measure")
spb = 60.0 / a.bpm; beats = int(round((dur - a.offset) / spb))
dead = []
for b in range(beats):
    i0, i1 = int((a.offset + b * spb) * FPS), min(len(step), int((a.offset + (b + 1) * spb) * FPS))
    if i1 > i0 and act[i0:i1].mean() < a.dead_px: dead.append(b)
say("PASS" if not dead else "WARN", "every beat has visible change" if not dead else f"{len(dead)} near-still beat(s): {', '.join('b'+str(b) for b in dead)}  (give each something to do: a cursor move, a count, a stagger)")

still = act < a.dead_px; run = best = 0; end = 0
for i, s in enumerate(still):
    run = run + 1 if s else 0
    if run > best: best, end = run, i
say("PASS" if best / FPS <= a.max_still else "WARN", f"longest near-still run {best/FPS:.2f} s (ends {(end+1)/FPS:.2f} s; limit {a.max_still} s)")

if a.compare:
    def md5s(v): return [l.split(",")[-1].strip() for l in subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-f", "framemd5", "-"], capture_output=True, text=True).stdout.splitlines() if l and not l.startswith("#")]
    A, B = md5s(a.video), md5s(a.compare)
    diff = [i for i, (x, y) in enumerate(zip(A, B)) if x != y]
    say("PASS" if len(A) == len(B) and not diff else "FAIL", "two renders are frame-identical (deterministic)" if len(A) == len(B) and not diff else f"renders differ: {len(diff)} frame(s), first at {diff[0] if diff else '?'} (lengths {len(A)}/{len(B)})")

if a.sheet:
    os.makedirs("snapshots", exist_ok=True)
    cols = 8; rows = (beats + cols - 1) // cols
    sel = "+".join(f"eq(n\\,{int(round((a.offset + b * spb) * FPS))})" for b in range(beats))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.video, "-vf", f"select='{sel}',scale=240:-1,tile={cols}x{rows}", "-vsync", "0", "-frames:v", "1", "snapshots/beats.png"])
    print("wrote snapshots/beats.png (one frame per beat)")
print(f"\nSUMMARY: {fails} FAIL, {warns} WARN")
sys.exit(1 if fails else 0)
