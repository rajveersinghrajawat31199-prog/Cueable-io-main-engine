#!/usr/bin/env python3
"""Compare ASR engines on ONE clip: the bake-off every new transcription tool must win before it goes into tools.json.
usage: asr_bench.py <speech_16k.wav> <reference.json> <candidate.json> [candidate2.json ...]
reference = a transcript you trust (Scribe's analysis/scribe.json for Hinglish; a hand-fixed one is better).
candidate = {words:[{text|word,start,end}]} or segments[].words, or just {"text": "..."} (then no timing metrics).
Prints per candidate: token recall vs reference (script-agnostic, normalised), speech coverage, ghosts, median word-start error (ms) on
matched tokens. Also record seconds-per-audio-minute, RAM and licence yourself. Recall is a proxy: the reference is not ground truth."""
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asr_coverage import GHOSTS, check, load_words  # noqa: E402

norm = lambda t: re.sub(r"[^\wऀ-ॿ]+", "", t.lower())  # noqa: E731


def tokens_and_words(path):
    d = json.load(open(path))
    try:
        ws = load_words(path)
    except (KeyError, TypeError):
        ws = []
    if ws:
        return [norm(w["text"]) for w in ws if norm(w["text"])], ws
    return [norm(t) for t in re.split(r"\s+", d.get("text", "")) if norm(t)], []


wav, ref_path, cands = sys.argv[1], sys.argv[2], sys.argv[3:]
ref_tok, ref_words = tokens_and_words(ref_path)
print("%-34s %7s %9s %7s %8s %12s" % ("candidate", "recall", "coverage", "ghosts", "words", "start err ms"))
for c in cands:
    tok, ws = tokens_and_words(c)
    pool = list(tok)
    hit = 0
    errs = []
    for i, r in enumerate(ref_tok):
        if r in pool:
            pool.remove(r)
            hit += 1
            if ws and ref_words:
                m = [w for w in ws if norm(w["text"]) == r]
                if m:
                    errs.append(min(abs(w["start"] - ref_words[i]["start"]) for w in m) * 1000)
    cov = ("%.0f%%" % (100 * check(ws, wav)["coverage"])) if ws else "n/a"
    ghosts = len(GHOSTS.findall(" ".join(tok)))
    print("%-34s %6.0f%% %9s %7d %8d %12s" % (os.path.basename(c)[:34], 100 * hit / max(len(ref_tok), 1), cov, ghosts, len(tok),
                                           ("%.0f" % statistics.median(errs)) if errs else "n/a"))
