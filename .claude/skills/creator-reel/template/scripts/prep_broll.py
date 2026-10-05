#!/usr/bin/env python3
"""Crop sections out of the 4K HLG portrait phone footage and render them as SDR 1080p-class b-roll clips.
Crop FIRST (cheap), then tone-map HLG -> SDR on the small frames. -> assets/br/<name>.mp4"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl  # noqa: E402

os.makedirs(os.path.join(edl.ROOT, "assets", "br"), exist_ok=True)
TONE = ("zscale=t=linear:npl=1000,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:desat=0,"
        "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,eq=%s")
only = sys.argv[1:]
_tr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer", "-of", "csv=p=0", edl.BROLL_SRC],
                     capture_output=True, text=True).stdout.strip()
HDR = _tr in ("arib-std-b67", "smpte2084")          # SDR sources must NOT go through the HLG tone-map
for name, c in edl.BROLL_CLIPS.items():
    if only and name not in only:
        continue
    x, y, w, h = c["crop"]
    ow, oh = c["out"]
    eq = c.get("eq", "gamma=1.2:contrast=1.06:saturation=1.1")
    vf = "crop=%d:%d:%d:%d,scale=%d:%d:flags=lanczos,%s" % (w, h, x, y, ow, oh, TONE % eq if HDR else "eq=" + eq)
    out = os.path.join(edl.ROOT, "assets", "br", name + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(c["ss"]), "-t", str(c["dur"]), "-i", edl.BROLL_SRC, "-an",
                    "-vf", vf, "-r", "30", "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-g", "30", "-pix_fmt", "yuv420p", out],
                   check=True)
    print("made", out)
