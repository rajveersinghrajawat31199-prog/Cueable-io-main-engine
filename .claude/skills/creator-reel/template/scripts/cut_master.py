#!/usr/bin/env python3
"""Cut the talking head into the master (jump cuts on real speech edges) + processed voice track.
-> assets/master.mp4 (video only, CFR 30, short GOP)   assets/audio/vo.wav (48 kHz stereo, ~-16 LUFS)"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl  # noqa: E402

os.makedirs(os.path.join(edl.ROOT, "assets", "audio"), exist_ok=True)
FAD = 0.012  # 12 ms edge fades: no clicks at the cuts
parts, vs, as_ = [], [], []
for i, c in enumerate(edl.CUTS):
    a, b, d = c["a"], c["b"], c["dur"]
    parts.append("[0:v]trim=start=%.5f:end=%.5f,setpts=PTS-STARTPTS[v%d]" % (a, a + d, i))
    parts.append("[0:a]atrim=start=%.5f:end=%.5f,asetpts=PTS-STARTPTS,afade=t=in:d=%.3f,afade=t=out:st=%.5f:d=%.3f[a%d]"
                 % (a, a + d, FAD, d - FAD, FAD, i))
    vs.append("[v%d]" % i)
    as_.append("[a%d]" % i)
n = len(edl.CUTS)
parts.append("".join(v + a for v, a in zip(vs, as_)) + "concat=n=%d:v=1:a=1[vc][ac]" % n)
parts.append("[vc]eq=contrast=1.04:saturation=1.06,format=yuv420p[vout]")
parts.append("[ac]highpass=f=70,acompressor=threshold=-24dB:ratio=2.5:attack=10:release=150:makeup=2,"
             "loudnorm=I=-16:LRA=9:TP=-1.5,aresample=48000,afade=t=in:st=0:d=0.14,aformat=channel_layouts=stereo[aout]")   # 140 ms fade from silence: the first word starts at ~0.16 s
script = os.path.join(edl.ROOT, "build", "cut_master.filter")
os.makedirs(os.path.dirname(script), exist_ok=True)
open(script, "w").write(";\n".join(parts))

out_v = os.path.join(edl.ROOT, "assets", "master.mp4")
out_a = os.path.join(edl.ROOT, "assets", "audio", "vo.wav")
cmd = ["ffmpeg", "-v", "error", "-y", "-i", edl.SRC, "-filter_complex_script", script,
       "-map", "[vout]", "-an", "-r", "30", "-vsync", "cfr", "-c:v", "libx264", "-crf", "12", "-preset", "medium",
       "-g", "30", "-keyint_min", "30", "-sc_threshold", "0", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_v,
       "-map", "[aout]", "-c:a", "pcm_s16le", out_a]
print("cutting %d segments -> %.2f s master" % (n, edl.DUR))
subprocess.run(cmd, check=True)
print("done:", out_v, out_a)
