#!/usr/bin/env python3
"""Does a rendered video conform to a PLATFORM ADAPTER's limits? Machine-checkable facts only (container, codec, fps, size, duration, aspect, resolution, audio codec).
Says nothing about quality: that is /quality-gate. Adapters live in platforms/<name>.json (data, one per destination).

usage: check_export.py video.mp4 --platform linkedin [--aspect 9:16]      exit 1 on any FAIL
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--platform", required=True); ap.add_argument("--aspect"); ap.add_argument("--use", default="paid", choices=["paid", "organic"], help="paid ad (default) or organic post: they have different platform limits"); a = ap.parse_args()
AD = json.load(open(os.path.join(HERE, "..", "platforms", a.platform + ".json"))); V = AD["video"]
ORG = AD.get("organic")
o = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", a.video], capture_output=True, text=True).stdout)
vs = next(s for s in o["streams"] if s["codec_type"] == "video"); au = next((s for s in o["streams"] if s["codec_type"] == "audio"), None)
n, d = vs["r_frame_rate"].split("/"); fps = float(n) / float(d); w, h = int(vs["width"]), int(vs["height"]); dur = float(o["format"]["duration"]); size = int(o["format"]["size"])
fails = warns = 0
if a.use == "organic":
    if not ORG: sys.exit(f"adapter '{a.platform}' has no organic limits")
    def say(l, m):
        global fails, warns; fails += l == "FAIL"; warns += l == "WARN"; print(f"{l:4}  {m}")
    ext = os.path.splitext(a.video)[1].lower().strip(".")
    say("PASS" if ext in ORG["containers"] else "FAIL", f"container .{ext} (organic supports {', '.join(ORG['containers'])}; not {', '.join(ORG['not_supported'])})")
    say("PASS" if ORG["fps"]["min"] <= fps <= ORG["fps"]["max"] else "FAIL", f"frame rate {fps:g} (organic accepts {ORG['fps']['min']}-{ORG['fps']['max']}): the 60 fps master is fine here")
    say("PASS" if ORG["file_size_bytes"]["min"] <= size <= ORG["file_size_bytes"]["max"] else "FAIL", f"file size {size / 1e6:.1f} MB")
    say("PASS" if ORG["duration_s"]["min"] <= dur <= ORG["duration_s"]["max"] else "FAIL", f"duration {dur:.1f} s (organic {ORG['duration_s']['min']}-{ORG['duration_s']['max']} s)")
    say("PASS" if ORG["resolution"]["min"][0] <= w <= ORG["resolution"]["max"][0] and ORG["resolution"]["min"][1] <= h <= ORG["resolution"]["max"][1] else "FAIL", f"resolution {w}x{h}")
    say("PASS" if ORG["aspect_ratio"]["min"] <= w / h <= ORG["aspect_ratio"]["max"] else "FAIL", f"aspect {w / h:.3f} (organic {ORG['aspect_ratio']['as_written']})")
    print(f"\nSUMMARY ({a.platform}, organic): {fails} FAIL, {warns} WARN"); sys.exit(1 if fails else 0)
def say(l, m):
    global fails, warns; fails += l == "FAIL"; warns += l == "WARN"; print(f"{l:4}  {m}")
say("PASS" if "mp4" in o["format"]["format_name"] and a.video.lower().endswith(".mp4") else "FAIL", f"container {o['format']['format_name']} (want mp4)")
say("PASS" if vs["codec_name"] in V["codec"] else "FAIL", f"video codec {vs['codec_name']} (want {'/'.join(V['codec'])})")
say("PASS" if fps < V["fps_max_exclusive"] else "FAIL", f"frame rate {fps:g} (PAID ads: less than {V['fps_max_exclusive']}, LinkedIn spec + owner's experience)" + ("" if fps < V["fps_max_exclusive"] else f": keep this file as the master and export the paid version with export_for.py (default {V['fps_paid_export']} fps, frames blended)"))
say("PASS" if V["file_size_bytes"]["min"] <= size <= V["file_size_bytes"]["max"] else "FAIL", f"file size {size / 1e6:.1f} MB (want {V['file_size_bytes']['min'] / 1e3:.0f} KB - {V['file_size_bytes']['max'] / 1e6:.0f} MB)")
D = V["duration_s"]
say("PASS" if D["min"] <= dur <= D["max"] else "FAIL", f"duration {dur:.1f} s (hard range {D['min']}-{D['max']} s)")
say("PASS" if D["recommended"][0] <= dur <= D["recommended"][1] else "WARN", f"duration {dur:.1f} s vs recommended {D['recommended'][0]}-{D['recommended'][1]} s ({D['recommended_why']})" + ("; in-stream max %s s" % D["instream_max"] if dur > D["instream_max"] else ""))
ratio = w / h; best = min(V["aspects"], key=lambda k: abs(ratio - (int(k.split(':')[0]) / int(k.split(':')[1]))))
asp = a.aspect or best; A = V["aspects"].get(asp)
if not A: say("FAIL", f"aspect {asp} is not supported (have {', '.join(V['aspects'])})")
else:
    ar = int(asp.split(':')[0]) / int(asp.split(':')[1])
    say("PASS" if abs(ratio - ar) < 0.01 else "FAIL", f"aspect {w}x{h} = {ratio:.3f}, closest supported {asp}")
    say("PASS" if A["min"][0] <= w <= A["max"][0] and A["min"][1] <= h <= A["max"][1] else "FAIL", f"resolution {w}x{h} within {A['min'][0]}x{A['min'][1]} .. {A['max'][0]}x{A['max'][1]}")
    if [w, h] != A["recommended"]: print(f"INFO  recommended {A['recommended'][0]}x{A['recommended'][1]} (yours is valid but not the recommended size)")
if au:
    say("PASS" if au["codec_name"] in V["audio"]["codec"] else "FAIL", f"audio codec {au['codec_name']} (want {'/'.join(V['audio']['codec'])})")
else: print("INFO  no audio stream (fine for a silent-first ad; captions must carry the message)")
print(f"\nSUMMARY ({a.platform}): {fails} FAIL, {warns} WARN"); sys.exit(1 if fails else 0)
