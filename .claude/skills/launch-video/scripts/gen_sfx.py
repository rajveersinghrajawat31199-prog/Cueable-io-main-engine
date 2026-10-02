#!/usr/bin/env python3
"""Prepare light UI SFX (from the shared library) + the music bed, and mount both in audio_meta.json.

config (launch.config.json):
  "sfx": {
    "cues":    [[frame, t_in_frame_s, "name", volume], ...],
    "recipes": [{"type":"stagger","frame":2,"t0":0.14,"n":3,"step":0.13,"offset":0.05,"names":["pop2","pop2a","pop2b"],"vol":0.3}]
  },
  "bgm": {"src":"~/Downloads/track.mp3","start":0,"volume":0.115,"lead":0.3,"fade_in":1.4,"fade_out":2.6,"query":"why this track"}

Volumes are CAPPED per palette entry (sfx_palette.json) so a cue can't exceed its safe level under the voice.
Run AFTER pad_vo.py / sync-durations (the bed length = sum of frame durations). Env BGM_VOL overrides bgm.volume.
usage: gen_sfx.py [--project .]
"""
import os, re, sys, json, glob, subprocess
args = sys.argv[1:]
ROOT = os.path.abspath(args[args.index("--project") + 1]) if "--project" in args else os.getcwd()
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.expanduser("~/hyperframes-assets/sfx")
cfg = json.load(open(os.path.join(ROOT, "launch.config.json")))
pal = json.load(open(os.path.join(HERE, "sfx_palette.json")))["palette"]
pal.update(cfg.get("sfx", {}).get("palette", {}))   # a project may add/override entries

def resolve(e):
    if "file" in e: p = os.path.join(LIB, e["file"])
    else:
        m = glob.glob(os.path.join(LIB, e["glob"])); assert m, f"no SFX match: {e['glob']}"; p = m[0]
    assert os.path.exists(p), p
    return p

OUT = os.path.join(ROOT, "assets", "sfx"); os.makedirs(OUT, exist_ok=True)
PEAK = -11.0
def prep(name, e):
    dst = os.path.join(OUT, name + ".mp3"); tmp = dst + ".tmp.wav"
    dur, pitch = e.get("dur", 0.9), e.get("pitch", 1.0)
    af = f"asetrate=44100*{pitch},aresample=44100" if pitch != 1.0 else "anull"
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", resolve(e), "-t", str(dur), "-ac", "1", "-af", af, tmp])
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", tmp, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mx = float(re.search(r"max_volume: ([-\d.]+) dB", r).group(1))
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", f"volume={PEAK-mx}dB,afade=t=out:st={e.get('fade_st',0.5)}:d={e.get('fade_d',0.4)}", "-c:a", "libmp3lame", "-b:a", "128k", dst])
    os.remove(tmp)
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dst]))

cues = [list(c) for c in cfg.get("sfx", {}).get("cues", [])]
for r in cfg.get("sfx", {}).get("recipes", []):
    if r["type"] == "stagger":
        for k in range(r["n"]):
            cues.append([r["frame"], r["t0"] + k * r["step"] + r.get("offset", 0), r["names"][k % len(r["names"])], r.get("vol", 0.3)])
    else: raise SystemExit(f"unknown recipe type {r['type']}")

used = sorted({c[2] for c in cues})
dur = {n: prep(n, pal[n]) for n in used}
cues = [(int(f), round(float(t), 3), n, min(float(v), pal[n]["cap"])) for f, t, n, v in cues]
assert all(t > 0 for f, t, n, v in cues), "no SFX at t=0"

meta_path = os.path.join(ROOT, "audio_meta.json")
meta = json.load(open(meta_path))
meta["sfx"] = [{"frame": f, "file": f"assets/sfx/{n}.mp3", "offset_s": t, "duration_s": round(dur[n], 2), "volume": v} for f, t, n, v in sorted(cues)]

b = cfg.get("bgm")
if b:
    total = round(sum(v["duration_s"] for v in meta["voices"]), 2)
    os.makedirs(os.path.join(ROOT, "assets", "bgm"), exist_ok=True)
    dst = os.path.join(ROOT, "assets", "bgm", "bgm.mp3")
    lead, fi, fo = b.get("lead", 0.3), b.get("fade_in", 1.4), b.get("fade_out", 2.6)
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-ss", str(b.get("start", 0)), "-t", str(total), "-i", os.path.expanduser(b["src"]), "-af",
        f"adelay={int(lead*1000)}|{int(lead*1000)},afade=t=in:st={lead}:d={fi},afade=t=out:st={total-fo}:d={fo},atrim=0:{total}", "-c:a", "libmp3lame", "-b:a", "160k", dst])
    meta["bgm"] = {"path": "assets/bgm/bgm.mp3", "volume": float(os.environ.get("BGM_VOL", b.get("volume", 0.12))), "query": b.get("query", ""), "duration_s": total}
    meta["bgm_pending"] = False
else:
    meta["bgm"] = None
json.dump(meta, open(meta_path, "w"), indent=2)
print(f"{len(cues)} SFX cues ({len(used)} sounds); bgm: {'yes vol ' + str(meta['bgm']['volume']) if meta['bgm'] else 'none'}")
