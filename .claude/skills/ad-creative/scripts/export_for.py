#!/usr/bin/env python3
"""Make a platform-conformant export from a master render using a PLATFORM ADAPTER, then verify it with check_export.py. Also writes a thumbnail.
The master (60 fps by default) is never touched.

  --use paid (default)  a PAID ad: if the master is at or above the platform's paid frame-rate limit, convert to the adapter's `fps_paid_export`
                        (LinkedIn: 29.97) by BLENDING frames. Below the limit, nothing is converted.
  --use organic         keep the master's frame rate and size (LinkedIn organic accepts 10-60 fps); just remux/encode and verify against the organic limits
  --fps N               explicit override for either (must be lower than the master; frames are never invented)

Blending averages the source frames that fall in each output frame instead of dropping them, so motion blur stays correct: 60 -> 30 by averaging pairs keeps
a film-style 180-degree shutter, dropping every other frame would halve it. Size is kept native when inside the platform's min/max.

usage: export_for.py master.mp4 --platform linkedin --aspect 9:16 [--use paid|organic] [--fps N] [--size native|recommended|max] [--out exports/] [--thumb-at 1.0]
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("master"); ap.add_argument("--platform", required=True); ap.add_argument("--aspect", required=True)
ap.add_argument("--out", default="exports"); ap.add_argument("--size", default="native", choices=["native", "recommended", "max"]); ap.add_argument("--fps", type=float); ap.add_argument("--use", default="paid", choices=["paid", "organic"]); ap.add_argument("--thumb-at", type=float, default=1.0); a = ap.parse_args()
AD = json.load(open(os.path.join(HERE, "..", "platforms", a.platform + ".json"))); V = AD["video"]; A = V["aspects"].get(a.aspect)
if not A: sys.exit(f"aspect {a.aspect} not in adapter ({', '.join(V['aspects'])})")
p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "json", a.master], capture_output=True, text=True).stdout)["streams"][0]
sw, sh = p["width"], p["height"]; n, d = p["r_frame_rate"].split("/"); sfps = float(n) / float(d)
want = int(a.aspect.split(":")[0]) / int(a.aspect.split(":")[1])
if abs(sw / sh - want) > 0.01: sys.exit(f"master is {sw}x{sh}, not {a.aspect}: re-author or re-render the composition for this aspect. Cropping or letterboxing is not done here (reframe per format, never crop).")
# size: keep native when it fits the platform's min/max
if a.size == "recommended": W, H = A["recommended"]
elif a.size == "max": W, H = A["max"]
else: W, H = (sw, sh) if A["min"][0] <= sw <= A["max"][0] and A["min"][1] <= sh <= A["max"][1] else A["max"]
vf = [f"scale={W}:{H}:flags=lanczos"] if (W, H) != (sw, sh) else []
note = f"fps kept at {sfps:g}"
if a.use == "paid" and not a.fps and V.get("fps_policy") == "required_for_paid" and sfps >= V["fps_max_exclusive"] - 1e-9:
    a.fps = V["fps_paid_export"]; note = "PAID export: frame rate must be below %s, converting to %s" % (V["fps_max_exclusive"], a.fps)
if a.fps:
    if a.fps >= sfps - 0.01: sys.exit(f"--fps {a.fps:g} is not lower than the master's {sfps:g}: frames are never invented (re-render the master at the rate you need)")
    ratio = sfps / a.fps; k = round(ratio)
    if k >= 2 and abs(ratio - k) / k < 0.01:      # e.g. 60 -> 30 / 29.97: average k consecutive frames, keep one per group (aligned groups)
        vf += [f"tmix=frames={k}", f"select='eq(mod(n\\,{k})\\,{k - 1})'", f"setpts=N/({sfps / k})/TB"]
        vf += [f"fps={a.fps}"]                       # always pin the output rate (else ffmpeg duplicates frames back up to the input rate)
        note = (note + "; " if note.startswith("PAID") else "") + f"{sfps:g} -> {a.fps:g} fps by averaging {k} frames per output frame (blend, not drop)"
    else:                                          # non-integer ratio (e.g. 60 -> 24/25): weighted blend of neighbouring frames
        vf += [f"framerate=fps={a.fps}"]; note = f"{sfps:g} -> {a.fps:g} fps by weighted frame blending"
os.makedirs(a.out, exist_ok=True); stem = os.path.splitext(os.path.basename(a.master))[0]
tag = f"_{a.fps:g}fps" if a.fps else ""; base = f"{a.out}/{stem}_{a.platform}_{a.use}_{a.aspect.replace(':', 'x')}{tag}"
has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", a.master], capture_output=True, text=True).stdout.strip() != ""
cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.master] + (["-vf", ",".join(vf)] if vf else []) + ["-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-pix_fmt", "yuv420p", "-maxrate", "16M", "-bufsize", "32M", "-movflags", "+faststart"]
cmd += ["-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2"] if has_audio else ["-an"]
subprocess.run(cmd + [base + ".mp4"], check=True)
q = 2
while True:   # thumbnail <= platform cap
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(a.thumb_at), "-i", base + ".mp4", "-frames:v", "1", "-q:v", str(q), base + ".jpg"], check=True)
    if os.path.getsize(base + ".jpg") <= V["thumbnail"]["max_bytes"] or q >= 12: break
    q += 2
print(f"{note}; size {W}x{H}\nwrote {base}.mp4 ({os.path.getsize(base + '.mp4') / 1e6:.1f} MB) and {base}.jpg ({os.path.getsize(base + '.jpg') / 1e3:.0f} KB)")
sys.exit(subprocess.run([sys.executable, os.path.join(HERE, "check_export.py"), base + ".mp4", "--platform", a.platform, "--aspect", a.aspect, "--use", a.use]).returncode)
