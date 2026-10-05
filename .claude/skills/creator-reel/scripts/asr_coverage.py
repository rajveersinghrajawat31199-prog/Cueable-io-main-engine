#!/usr/bin/env python3
"""Acceptance test for an ASR result. Would have rejected both failed Hindi transcripts of the HYROX job.
usage: asr_coverage.py words.json speech_16k.wav [--min-cover 0.97] [--max-gap 2.0]
Passes when: >= min-cover of the speech frames (audio energy) lie within a transcribed word (+-0.25 s), the longest run of
speech with no word is <= max-gap seconds, and no 'ghost' hallucination (subscribe / thanks for watching, or one token repeated
4+ times in a row) appears. Accepts Scribe ({words:[{text,start,end,type}]}), engine/whisper ({words:[{word,...}]} or segments[].words)."""
import json
import re
import sys
import wave

import numpy as np

GHOSTS = re.compile(r"subscribe|सब्सक्राइब|thanks? for watching|thank you for watching|धन्यवाद|like and share", re.I)


def load_words(path):
    d = json.load(open(path))
    ws = d["words"] if "words" in d and d["words"] else [w for s in d.get("segments", []) for w in s.get("words", [])]
    out = []
    for w in ws:
        if w.get("type", "word") != "word":
            continue
        out.append(dict(text=(w.get("text") or w.get("word") or "").strip(), start=float(w["start"]), end=float(w["end"])))
    return out


def speech_frames(wav_path):
    w = wave.open(wav_path)
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = len(x) // 160
    db = 20 * np.log10(np.sqrt((x[:n * 160].reshape(n, 160) ** 2).mean(1) + 1e-12) + 1e-9)
    return db > (np.percentile(db, 10) + 11)


def check(words, wav_path, min_cover=0.97, max_gap=2.0):
    sp = speech_frames(wav_path)
    cov = np.zeros(len(sp), bool)
    for w in words:
        cov[max(int((w["start"] - 0.25) * 100), 0):min(int((w["end"] + 0.25) * 100) + 1, len(sp))] = True
    miss = sp & ~cov
    cover = 1 - miss.sum() / max(sp.sum(), 1)
    run = best = 0
    for m in miss:                                  # longest uncovered speech run, tolerating 0.3 s breaks inside it
        run = run + 1 if m else max(run - 1, 0) if run else 0
        best = max(best, run)
    toks = [w["text"] for w in words]
    ghosts = len(GHOSTS.findall(" ".join(toks)))
    rep = sum(1 for i in range(len(toks) - 3) if len({t.lower() for t in toks[i:i + 4]}) == 1)
    ok = bool(cover >= min_cover and best / 100 <= max_gap and ghosts == 0 and rep == 0)
    return dict(ok=ok, coverage=round(float(cover), 3), longest_uncovered_s=round(best / 100, 1), ghosts=ghosts, repeats=rep,
                words=len(words), speech_s=round(float(sp.sum()) / 100, 1))


if __name__ == "__main__":
    a = sys.argv[1:]
    kw = {}
    for flag, key in (("--min-cover", "min_cover"), ("--max-gap", "max_gap")):
        if flag in a:
            i = a.index(flag); kw[key] = float(a[i + 1]); del a[i:i + 2]
    r = check(load_words(a[0]), a[1], **kw)
    print(json.dumps(r))
    sys.exit(0 if r["ok"] else 1)
