"""Edit decision list for __NAME__: PROJECT DATA ONLY (the engine is edl_lib.py).
Everything is anchored to word timings of the talking-head clip (analysis/words.json), so cuts, type reveals, B-roll and sound derive from
what is actually said, never from hand-timed seconds. Word indices = indices into WORDS: python3 scripts/edl.py words  ->  index|start|word.
Read .claude/skills/creator-reel/SKILL.md S3-S5 BEFORE filling this in."""
import os
import sys

from edl_lib import *  # noqa: F401,F403
from edl_lib import _bounds, _cut_for  # noqa: F401

SRC = os.path.expanduser("__SRC__")
BROLL_SRC = os.path.expanduser("__BROLL__")
ACC = "__ACC__"   # the ONE accent colour of the film

# ---------------------------------------------------------------- cuts (MASTER order)
# (id, first word, last word, options). Ids starting with H = the hook teaser (words re-used later in the story).
# options: pre/post pads (s, default .06/.10), a_abs/b_abs exact SOURCE seconds (use them when a gap is < 100 ms), zoom (punch-in scale).
# Cut points sit in the pauses; never cut inside continuous speech without an energy dip; verify the hook's audio by re-transcribing it.
CUT_DEFS = [
    # ("H1", 232, 234, dict(pre=.16, zoom=1.14)),     # hook line pulled from the end of the story
    # ("S1", 0, 9, {}),
]
DUR = make_cuts(CUT_DEFS) if CUT_DEFS else 0.0

# ---------------------------------------------------------------- type cards
# token  "style:text@anchor[+anchor..][|flags]"  styles x/X big italic serif (accent/white), l/L large, m medium sans, s small sans,
# u micro caps, p pill (rounded accent background).  anchors = word indices, or "t0.25" for an absolute master time.
# flags: ul underline | szNNN px | cntNN count-up in "{}" | strikeNNN strike-through at word NNN.
# C(id, zone top|bot|mid|tag, align left|center|right, L(tok, tok...), ..., occ="hook", bg="dim"|"poster", t0=, t1=("end", cutid))
# Hook title card id MUST be "htitle" (build.py gives it no sound); spoken-word type of the hook goes in the bot zone.
CARDS = [
    # C("htitle", "top", "center", L("p:figure from the footage@t0.18"), L("s:the twist@t0.50|sz70"), occ="hook", t0=0.08, t1=("end", "H3")),
]

# ---------------------------------------------------------------- b-roll
# BROLL: (id, clip, first word, last word, "full" | "card", lead s, tail s, None)
# BROLL_CLIPS: clip -> dict(ss=seconds in source, dur=, crop=(x, y, w, h) in the ROTATED frame, out=(w, h), eq="gamma=1.5:contrast=1.14:saturation=1.1")
# 9:16 full-bleed crops for scenes; landscape crops of a screen as rounded "card" over a dimmed face.
BROLL = []
BROLL_CLIPS = {}

# ---------------------------------------------------------------- transitions
TRANSITIONS = []   # hard cuts only: light leaks / flashes / whips and whoosh sounds were rejected by the user. Add only if asked.

if __name__ == "__main__":
    if sys.argv[1:] == ["words"]:
        print("\n".join("%d|%.2f|%s" % (i, w["start"], w["text"]) for i, w in enumerate(WORDS)))
        raise SystemExit
    print("master duration %.2fs, %d cuts" % (DUR, len(CUTS)))
    for c in CUTS:
        print("%-5s src %6.2f-%6.2f  master %6.2f-%6.2f  zoom %.2f" % (c["id"], c["a"], c["b"], c["m0"], c["m0"] + c["dur"], c["zoom"]))
