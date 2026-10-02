#!/usr/bin/env python3
"""Per-frame VO clips from the one continuous take: optional LEAD silence (speech never starts at t=0) and trailing
silence to a target length so UI frames have room to act (spliced silence, no re-TTS). Idempotent: rebuilds from
assets/vo/vo_NN.raw.mp3 and words_raw every run. Then run:  audio.mjs sync-durations  (see build_all.sh).

config (launch.config.json):
  "audio": {"lead": {"1": 0.3}, "targets": {"1": 4.9, "2": 6.48, ...}}     # seconds, keyed by frame number
usage: pad_vo.py [--project .]
"""
import json, os, subprocess, sys
args = sys.argv[1:]
ROOT = os.path.abspath(args[args.index("--project") + 1]) if "--project" in args else os.getcwd()
cfg = json.load(open(os.path.join(ROOT, "launch.config.json")))["audio"]
LEAD = {int(k): v for k, v in cfg.get("lead", {}).items()}
TARGET = {int(k): v for k, v in cfg["targets"].items()}
meta = json.load(open(os.path.join(ROOT, "audio_meta.json")))
for v in meta["voices"]:
    f = v["frame"]; src = os.path.join(ROOT, "assets/vo", f"vo_{f:02d}.mp3"); raw = os.path.join(ROOT, "assets/vo", f"vo_{f:02d}.raw.mp3")
    if not os.path.exists(raw): os.rename(src, raw)
    base = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", raw]))
    lead = LEAD.get(f, 0.0)
    tgt = max(TARGET.get(f, 0), base + lead)          # never cut speech: target is a floor
    af = (f"adelay={int(lead*1000)}|{int(lead*1000)},afade=t=in:st={lead:.3f}:d=0.05," if lead else "") + f"apad=whole_dur={tgt:.3f}"
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-t", f"{tgt:.3f}", "-c:a", "libmp3lame", "-b:a", "128k", src])
    v.setdefault("words_raw", v["words"])
    v["words"] = [dict(w, start=round(w["start"] + lead, 3), end=round(w["end"] + lead, 3)) for w in v["words_raw"]]
    v["duration_s"] = round(tgt, 3)
    print(f"frame {f:>2}: raw {base:5.2f}s lead {lead:.2f} -> {tgt:5.2f}s" + ("   (target below speech length: raised)" if TARGET.get(f, 0) < base + lead else ""))
json.dump(meta, open(os.path.join(ROOT, "audio_meta.json"), "w"), indent=2)
print("total %.2fs" % sum(v["duration_s"] for v in meta["voices"]))
