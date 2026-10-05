#!/usr/bin/env python3
"""assets/vo/vo-words.json: word timings on the MASTER timeline (what the critic / captions need)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl  # noqa: E402

out = []
for c in edl.CUTS:
    for i in range(c["w0"], c["w1"] + 1):
        s = edl.mt(i, "hook" if c["hook"] else None)
        e = min(edl.me(i, "hook" if c["hook"] else None), s + 0.7)
        out.append(dict(word=edl.WORDS[i]["text"], start=round(s, 3), end=round(e, 3)))
out.sort(key=lambda w: w["start"])
os.makedirs(os.path.join(edl.ROOT, "assets", "vo"), exist_ok=True)
json.dump(out, open(os.path.join(edl.ROOT, "assets", "vo", "vo-words.json"), "w"), ensure_ascii=False, indent=0)
print(len(out), "words")
