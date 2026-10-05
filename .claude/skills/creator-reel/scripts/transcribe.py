#!/usr/bin/env python3
"""ASR adapter for creator reels: runs the engines listed in tools.json (slots.asr.order), applies the acceptance test
(asr_coverage.py) to each result, keeps the first that passes, and writes analysis/words.json + analysis/asr_log.json.
usage: transcribe.py <speech_16k.wav> [--project videos/<p>] [--lang hi|en|...] [--engine auto|scribe|whisper-py|hyperframes] [--accept-anyway]
To add a new engine (e.g. the user's repo): write run_<name>(audio, lang, project) -> (words, language), register it in RUN, put the name in
tools.json order. words = [{text, start, end, type:"word"}]. Never print the API key."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)
from asr_coverage import check  # noqa: E402

TOOLS = json.load(open(os.path.join(HERE, "..", "tools.json")))
WHISPER_PY = os.path.expanduser("~/.venvs/asr/bin/whisper")
HF = "hyperframes@0.8.113"


def secret(name):
    if os.environ.get(name):
        return os.environ[name]
    p = os.path.expanduser("~/.config/hyperframes/secrets.env")
    if os.path.exists(p):
        for line in open(p):
            if line.strip().startswith(name + "=") or line.strip().startswith("export " + name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def run_scribe(audio, lang, project):
    key = secret("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("no ELEVENLABS_API_KEY")
    out = subprocess.run(["curl", "-s", "-X", "POST", "https://api.elevenlabs.io/v1/speech-to-text", "-H", "xi-api-key: " + key,
                          "-F", "model_id=scribe_v1", "-F", "timestamps_granularity=word", "-F", "tag_audio_events=false",
                          "-F", "diarize=false", "-F", "file=@" + audio], capture_output=True, text=True, timeout=600).stdout
    d = json.loads(out)
    if "words" not in d:
        raise RuntimeError("scribe error: " + out[:200])
    return [dict(text=w["text"], start=w["start"], end=w["end"], type="word") for w in d["words"] if w["type"] == "word"], d.get("language_code")


def run_whisper_py(audio, lang, project):
    if not os.path.exists(WHISPER_PY):
        raise RuntimeError("no ~/.venvs/asr whisper")
    tmp = tempfile.mkdtemp()
    cmd = [WHISPER_PY, audio, "--model", "small", "--word_timestamps", "True", "--output_format", "json", "--output_dir", tmp,
           "--fp16", "False", "--condition_on_previous_text", "False"] + (["--language", lang] if lang else [])
    subprocess.run(cmd, capture_output=True, check=True, timeout=3600)
    d = json.load(open(os.path.join(tmp, os.path.splitext(os.path.basename(audio))[0] + ".json")))
    return [dict(text=w["word"].strip(), start=w["start"], end=w["end"], type="word") for s in d["segments"] for w in s.get("words", [])], d.get("language")


def run_hyperframes(audio, lang, project):
    model = "small.en" if lang == "en" else "large-v3"
    cmd = ["npx", "--yes", HF, "transcribe", audio, "--dir", project, "--json", "-m", model] + (["-l", lang] if lang else [])
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if p.returncode != 0:
        raise RuntimeError("engine transcribe failed: " + (p.stderr or p.stdout)[-300:])
    cand = os.path.join(project, "transcript.json")
    d = json.load(open(cand)) if os.path.exists(cand) else json.loads(p.stdout[p.stdout.index("{"):])
    ws = d.get("words") or [w for s in d.get("segments", []) for w in s.get("words", [])]
    return [dict(text=(w.get("word") or w.get("text")).strip(), start=w["start"], end=w["end"], type="word") for w in ws], lang


RUN = {"scribe": run_scribe, "whisper-py": run_whisper_py, "hyperframes": run_hyperframes}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--project", default=None)
    ap.add_argument("--lang", default=None)
    ap.add_argument("--engine", default="auto")
    ap.add_argument("--accept-anyway", action="store_true")
    A = ap.parse_args()
    audio = os.path.abspath(A.audio)
    project = os.path.abspath(A.project or os.path.dirname(os.path.dirname(audio)))
    order = TOOLS["slots"]["asr"]["order"]
    engines = [A.engine] if A.engine != "auto" else order.get("en" if A.lang in ("en", "eng") else "default", order["default"])
    log, won = [], None
    for eng in engines:
        t0 = time.time()
        try:
            words, lang = RUN[eng](audio, A.lang, project)
        except Exception as e:                                   # noqa: BLE001  (any failure = try the next engine)
            log.append(dict(engine=eng, error=str(e)[:300]))
            print("%-12s FAILED: %s" % (eng, str(e)[:160]))
            continue
        tmp = os.path.join(tempfile.mkdtemp(), "w.json")
        json.dump({"words": words}, open(tmp, "w"))
        res = check(words, audio)
        res.update(engine=eng, seconds=round(time.time() - t0))
        log.append(res)
        print("%-12s %s  coverage %.0f%%  longest uncovered %.1fs  ghosts %d  words %d  (%ds)"
              % (eng, "PASS" if res["ok"] else "FAIL", 100 * res["coverage"], res["longest_uncovered_s"], res["ghosts"], res["words"], res["seconds"]))
        if res["ok"] or A.accept_anyway:
            won = dict(engine=eng, language=lang, words=words)
            break
    out_dir = os.path.join(project, "analysis")
    os.makedirs(out_dir, exist_ok=True)
    json.dump(log, open(os.path.join(out_dir, "asr_log.json"), "w"), indent=1)
    if not won:
        print("NO ENGINE PASSED the acceptance test: tell the user, do not cut from this transcript. Log: analysis/asr_log.json")
        sys.exit(2)
    json.dump(won, open(os.path.join(out_dir, "words.json"), "w"), ensure_ascii=False, indent=0)
    print("wrote analysis/words.json (%s, %d words)" % (won["engine"], len(won["words"])))
