"""edl_lib: the generic half of a creator-reel edit list (engine code, not project data).
A project's scripts/edl.py supplies only DATA (cuts, cards, b-roll, colours) and calls make_cuts().
Word timings come from analysis/words.json (written by scripts/transcribe.py); analysis/scribe.json is read as a fallback.
Cut points are placed on REAL speech edges measured from analysis/th_16k.wav, never on ASR word ends (those include trailing silence)."""
import json
import math
import os

__all__ = ["ROOT", "FPS", "WORDS", "ws", "we", "ENV", "NOISE_DB", "THR_DB", "onset", "offset", "_bounds", "CUTS", "make_cuts",
           "_cut_for", "mt", "me", "cut", "T", "L", "C"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the project dir: this file lives in videos/<p>/scripts/
FPS = 30


def _load_words():
    for name in ("words.json", "scribe.json"):
        p = os.path.join(ROOT, "analysis", name)
        if os.path.exists(p):
            return [w for w in json.load(open(p))["words"] if w.get("type", "word") == "word"]
    raise SystemExit("no analysis/words.json: run scripts/transcribe.py first")


WORDS = _load_words()
ws = lambda i: WORDS[i]["start"]  # noqa: E731
we = lambda i: WORDS[i]["end"]  # noqa: E731

def _env():
    """10 ms RMS envelope (dB) of the talking-head audio: Scribe word ENDS include trailing silence, so cut points
    are placed on the real speech edges instead."""
    import wave
    import numpy as np
    w = wave.open(os.path.join(ROOT, "analysis", "th_16k.wav"))
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = len(x) // 160
    r = np.sqrt((x[:n * 160].reshape(n, 160) ** 2).mean(1) + 1e-12)
    return 20 * np.log10(r + 1e-9)


ENV = _env()
NOISE_DB = float(sorted(ENV)[int(len(ENV) * 0.10)])
THR_DB = NOISE_DB + 11  # frames above this are speech


def onset(w0):
    """first loud frame after the last >=120 ms quiet run that precedes word w0."""
    hi = int(ws(w0) * 100) + 8
    run, cand = 0, None
    for k in range(max(0, hi - 80), min(hi, len(ENV) - 1)):
        if ENV[k] < THR_DB:
            run += 1
        else:
            if run >= 12:
                cand = k
            run = 0
    return cand / 100 if cand is not None else max(ws(w0) - 0.02, 0.0)


def offset(w1):
    """start of the first >=120 ms quiet run after word w1 starts (the real end of the phrase)."""
    lo = int((ws(w1) + 0.08) * 100)
    nxt = ws(w1 + 1) if w1 + 1 < len(WORDS) else we(w1) + 1.0
    hi = min(int((nxt + 0.05) * 100), len(ENV) - 1)
    run = 0
    for k in range(lo, hi):
        run = run + 1 if ENV[k] < THR_DB else 0
        if run == 12:
            return (k - 11) / 100
    return min(we(w1), nxt - 0.02)


def _bounds(w0, w1, pre, post, a_abs=None, b_abs=None):
    a, b = onset(w0) - pre, offset(w1) + post
    a = a if a_abs is None else a_abs
    b = b if b_abs is None else b_abs
    return max(round(a * FPS) / FPS, 0.0), round(b * FPS) / FPS



CUTS = []   # filled in place by make_cuts() so `from edl_lib import *` keeps a live reference


def make_cuts(cut_defs):
    """cut_defs: (id, first word, last word, options) in MASTER order. Ids starting with H are the hook teaser (their words are
    re-used later in the story). options: pre/post pads (s), a_abs/b_abs exact source times, zoom (punch-in scale).
    Fills CUTS in place and returns the master duration."""
    cuts, m, k = [], 0.0, 0
    for cid, w0, w1, o in cut_defs:
        a, b = _bounds(w0, w1, o.get("pre", .06), o.get("post", .10), o.get("a_abs"), o.get("b_abs"))
        hook = cid.startswith("H")
        if cuts and not hook and not cuts[-1]["hook"] and a < cuts[-1]["b"]:
            a = cuts[-1]["b"]                  # contiguous speech: never repeat source audio
        d = round((b - a) * FPS) / FPS
        if not hook:
            k += 1
        z = o.get("zoom", 1.0 if k % 2 == 1 else 1.12)  # punch-in alternates on every story cut (standard talking-head rhythm)
        cuts.append(dict(id=cid, w0=w0, w1=w1, a=a, b=a + d, m0=m, dur=d, zoom=z, hook=hook))
        m += d
    CUTS.clear()
    CUTS.extend(cuts)
    return round(m * FPS) / FPS


def _cut_for(i, occ=None):
    c = [x for x in CUTS if x["w0"] <= i <= x["w1"]]
    pick = [x for x in c if x["hook"] == (occ == "hook")] or c
    if not pick:
        raise KeyError("word %d is not in any kept cut" % i)
    return pick[0]


def mt(i, occ=None):
    """master time of the START of word i (an anchor like "t0.25" is an absolute master time)."""
    if isinstance(i, str):
        return float(i[1:])
    c = _cut_for(i, occ)
    return c["m0"] + max(0.0, min(ws(i) - c["a"], c["dur"]))


def me(i, occ=None):
    """master time of the END of word i."""
    if isinstance(i, str):
        return float(i[1:])
    c = _cut_for(i, occ)
    return c["m0"] + max(0.0, min(we(i) - c["a"], c["dur"]))


def cut(cid):
    return next(c for c in CUTS if c["id"] == cid)


# ---------------------------------------------------------------- typography cards
# token syntax  "style:text@anchor[+anchor...][|flag,flag]"   styles: x/X big italic serif (accent/white), l/L large italic,
# m medium sans, s small sans, u micro caps.  flags: ul (hand-drawn underline), szNNN (px), cntNN (count-up to NN in the {}),
# strike<word> (strike-through drawn at that word).  Several anchors = one reveal per word.
def T(s):
    s, *flags = s.split("|")
    st, rest = s.split(":", 1)
    txt, anc = rest.rsplit("@", 1)
    return dict(st=st, txt=txt, anc=[int(x) if x.isdigit() else x for x in anc.split("+")], flags=flags)


def L(*toks, dx=0):
    return dict(tok=[T(t) for t in toks], dx=dx)


def C(cid, zone, align, *lines, bg=None, occ=None, hold=0.28, t0=None, t1=None):
    return dict(id=cid, zone=zone, align=align, lines=list(lines), bg=bg, occ=occ, hold=hold, t0=t0, t1=t1)
