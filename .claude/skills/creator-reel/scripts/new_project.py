#!/usr/bin/env python3
"""Scaffold a creator-reel project and run every automatic analysis step, so the first manual action is writing the edit list.
usage: new_project.py <name> --talking-head PATH [--broll PATH] [--bgm PATH] [--lang hi] [--no-asr] [--accent "#FFD84A"]
Creates videos/<name>/ with the script template, fonts, pinned CLI files; then: probes the footage, extracts analysis/th_16k.wav,
makes contact sheets (talking head; b-roll tone-mapped if HDR), analyses the music, runs scripts/transcribe.py (acceptance-tested),
starts the job receipt. Prints what to open next."""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("--talking-head", required=True)
ap.add_argument("--broll", default="")
ap.add_argument("--bgm", default="")
ap.add_argument("--lang", default=None)
ap.add_argument("--no-asr", action="store_true")
ap.add_argument("--accent", default="#FFD84A")
A = ap.parse_args()
P = os.path.join(REPO, "videos", A.name)
if os.path.exists(P):
    sys.exit("videos/%s already exists: edit it, do not re-scaffold" % A.name)
TH, BR, BGM = (os.path.abspath(os.path.expanduser(p)) if p else "" for p in (A.talking_head, A.broll, A.bgm))
for p in (TH, BR, BGM):
    if p and not os.path.exists(p):
        sys.exit("missing file: " + p)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    j = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,"
                        "pix_fmt,color_transfer:stream_tags=rotate", "-of", "json", path]).stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), {})
    rot = int(v.get("tags", {}).get("rotate", 0) or 0) % 180 == 90
    w, h = (v.get("height"), v.get("width")) if rot else (v.get("width"), v.get("height"))
    return dict(dur=float(j["format"]["duration"]), w=w, h=h, fps=v.get("r_frame_rate"), transfer=v.get("color_transfer", ""),
                pix=v.get("pix_fmt"), audio=any(s["codec_type"] == "audio" for s in j["streams"]), rotated=rot)


for d in ("assets/fonts", "assets/sfx", "assets/audio", "assets/br", "assets/vo", "assets/source", "analysis", "scripts", "exports", "build"):
    os.makedirs(os.path.join(P, d))


def keep(path):
    """clone the source file into the project (APFS clone: instant, no extra disk, survives the original being moved or deleted)"""
    dst = os.path.join(P, "assets", "source", os.path.basename(path))
    if subprocess.run(["cp", "-c", path, dst], capture_output=True).returncode:
        shutil.copy(path, dst)
    return dst


TH = keep(TH)
BR = keep(BR) if BR else ""
for f in os.listdir(os.path.join(SKILL, "template", "scripts")):
    shutil.copy(os.path.join(SKILL, "template", "scripts", f), os.path.join(P, "scripts", f))
for f in os.listdir(os.path.join(SKILL, "template", "assets", "fonts")):
    shutil.copy(os.path.join(SKILL, "template", "assets", "fonts", f), os.path.join(P, "assets", "fonts", f))
edl = open(os.path.join(P, "scripts", "edl.py")).read().replace("__SRC__", TH).replace("__BROLL__", BR).replace("__ACC__", A.accent).replace("__NAME__", A.name)
open(os.path.join(P, "scripts", "edl.py"), "w").write(edl)
pin = "hyperframes@0.8.113"
json.dump({"name": A.name, "private": True, "type": "module", "scripts": {"dev": "npx --yes %s preview" % pin, "check": "npx --yes %s check" % pin,
          "render": "npx --yes %s render" % pin, "publish": "npx --yes %s publish" % pin}}, open(os.path.join(P, "package.json"), "w"), indent=2)
json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json", "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
           "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}, "media": {"autoProxy": True},
           "authoringSkill": "general-video"}, open(os.path.join(P, "hyperframes.json"), "w"), indent=2)
json.dump({"id": A.name, "name": A.name}, open(os.path.join(P, "meta.json"), "w"), indent=2)

th = probe(TH)
print("talking head: %dx%d %s fps, %.1f s, transfer=%s, audio=%s" % (th["w"], th["h"], th["fps"], th["dur"], th["transfer"] or "sdr", th["audio"]))
if th["w"] != 1080 or th["h"] != 1920:
    print("  NOTE: not 1080x1920 portrait: cut_master.py assumes it; adjust the scale there if needed")
run(["ffmpeg", "-v", "error", "-y", "-i", TH, "-vn", "-ac", "1", "-ar", "16000", os.path.join(P, "analysis", "th_16k.wav")])
run(["ffmpeg", "-v", "error", "-y", "-i", TH, "-vf", "fps=1/6,scale=216:384,tile=6x2", "-frames:v", "1", os.path.join(P, "analysis", "th_sheet.png")])
print("  -> analysis/th_16k.wav, analysis/th_sheet.png")
if BR:
    b = probe(BR)
    hdr = b["transfer"] in ("arib-std-b67", "smpte2084")
    print("b-roll: %dx%d (after rotation%s), %.1f s, transfer=%s%s" % (b["w"], b["h"], " applied" if b["rotated"] else "", b["dur"], b["transfer"] or "sdr", "  -> HDR: tone-map needed" if hdr else ""))
    step = max(3.0, b["dur"] / 36)
    tone = ",zscale=t=linear:npl=1000,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,eq=gamma=1.25" if hdr else ""
    sw, sh = (162, 288) if b["h"] > b["w"] else (288, 162)
    run(["ffmpeg", "-v", "error", "-y", "-skip_frame", "nokey", "-i", BR, "-an", "-vf", "fps=1/%.2f,scale=%d:%d%s,tile=9x4" % (step, sw, sh, tone), "-frames:v", "1",
         os.path.join(P, "analysis", "br_sheet.png")])
    open(os.path.join(P, "analysis", "br_sheet.txt"), "w").write("one cell every %.2f s, 9 columns, row-major: cell k = t %.2f s\n" % (step, step))
    print("  -> analysis/br_sheet.png (cell k = %.2f s * k)" % step)
if BGM:
    ext = os.path.splitext(BGM)[1] or ".mp3"
    shutil.copy(BGM, os.path.join(P, "assets", "audio", "bgm_src" + ext))
    out = run([sys.executable, os.path.join(P, "scripts", "bgm_analyze.py"), BGM]).stdout
    open(os.path.join(P, "analysis", "bgm_analysis.txt"), "w").write(out)
    print("music: analysed -> analysis/bgm_analysis.txt (find where the drums/beat enter; start the bed there, see SKILL.md S6)")
run([sys.executable, os.path.join(REPO, ".claude", "skills", "job-receipt", "scripts", "job_receipt.py"), "start", "--project", "videos/" + A.name, "--name", "Creator reel: " + A.name], cwd=REPO)
if not A.no_asr:
    print("\ntranscribing (acceptance-tested)...")
    r = subprocess.run([sys.executable, os.path.join(HERE, "transcribe.py"), os.path.join(P, "analysis", "th_16k.wav"), "--project", P] + (["--lang", A.lang] if A.lang else []))
    if r.returncode:
        print("  ASR did not pass: see analysis/asr_log.json; tell the user before cutting")
print("""
NEXT (manual part, in this order):
  1. open analysis/th_sheet.png%s; read: python3 scripts/edl.py words   (index|start|word)
  2. write scripts/edl.py data: CUT_DEFS (hook first), CARDS, BROLL, BROLL_CLIPS   (SKILL.md S3-S5)
  3. python3 scripts/prep_sfx.py; python3 scripts/prep_broll.py; python3 scripts/cut_master.py; python3 scripts/write_words.py
  4. python3 scripts/build.py; python3 scripts/build_audio.py%s; npx hyperframes@0.8.113 check; render (SKILL.md S8)""" % (
    ", analysis/br_sheet.png" if BR else "", " --bgm-from <seconds>" if BGM else ""))
