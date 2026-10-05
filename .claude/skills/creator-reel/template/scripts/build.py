#!/usr/bin/env python3
"""Generate index.html (HyperFrames composition) + build/schedule.json (sound cues) from edl.py.
usage: python3 scripts/build.py"""
import json
import math
import os
import sys

from PIL import ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl  # noqa: E402

ROOT, FPS, DUR, ACC = edl.ROOT, edl.FPS, edl.DUR, edl.ACC
W, H = 1080, 1920
MAXW = 925  # widest a line of type may be (frame minus safe margins)

F_SERIF = ImageFont.truetype(os.path.join(ROOT, "assets/fonts/InstrumentSerif-italic-latin.woff2"), 1000)
F_SANS = ImageFont.truetype(os.path.join(ROOT, "assets/fonts/DMSans-var.woff2"), 1000)
STY = dict(  # font, default px size, letter-spacing em
    x=("serif", 250, -.02), X=("serif", 250, -.02), l=("serif", 150, -.02), L=("serif", 150, -.02),
    m=("sans", 80, -.03), s=("sans", 52, -.02), u=("sans", 26, .16), p=("sans", 84, -.02))
BIG = "xXlL"


def secs(t):                      # time that lands ON a frame
    return math.floor(round(t * FPS) * 1e6 / FPS) / 1e6


def fmt(v):
    return ("%.5f" % v).rstrip("0").rstrip(".") or "0"


def win(t0, t1):                  # frame-exact half-open clip window -> (data-start, data-duration)
    f0, f1 = round(t0 * FPS), max(round(t1 * FPS), round(t0 * FPS) + 1)
    start = 0.0 if f0 == 0 else math.floor((f0 / FPS - 1e-5) * 1e5) / 1e5
    end = math.floor((f1 / FPS - 1e-5) * 1e5) / 1e5
    return fmt(start), fmt(round(end - start, 5))


def tw(txt, st, size):
    f = F_SERIF if STY[st][0] == "serif" else F_SANS
    return f.getlength(txt) / 1000 * size + STY[st][2] * size * len(txt)


def resolve(v, default):
    if v is None:
        return default
    if isinstance(v, tuple):
        return edl.cut(v[1])["m0"] + edl.cut(v[1])["dur"] + (v[2] if len(v) > 2 else 0)
    return v


# ------------------------------------------------------------------ cards
SFX, R, UL, STK, CNT = [], [], [], [], []   # sound cues; reveals; underlines; strikes; count-ups
cards = []
for c in edl.CARDS:
    occ = c["occ"]
    anchors = [a for ln in c["lines"] for t in ln["tok"] for a in t["anc"]]
    starts = [edl.mt(a, occ) for a in anchors]
    ends = [edl.me(a, occ) for a in anchors]
    c["t0"] = resolve(c["t0"], min(starts) - 0.07)
    cut_end = max([edl._cut_for(a, occ)["m0"] + edl._cut_for(a, occ)["dur"] for a in anchors if not isinstance(a, str)] or [1e9])
    c["t1"] = resolve(c["t1"], min(max(ends) + c["hold"], cut_end))   # text belongs to its sentence: never straddles a jump cut
    cards.append(c)
by_zone = {}
for c in sorted(cards, key=lambda c: c["t0"]):          # hard-cut swap: a card ends where the next one in its zone starts
    prev = by_zone.get(c["zone"])
    if prev and prev["t1"] > c["t0"]:
        prev["t1"] = c["t0"]
    by_zone[c["zone"]] = c

html_cards, dims, n_tok = [], [], 0
DM = []


def add_dim(kind, t0, t1):          # face-dimming plate; fades in/out so it never reads as a brightness pulse
    d0_, dd_ = win(t0, t1)
    did = "dm%d" % (len(DM) + 1)
    dims.append('<div id="%s" class="clip dim %s" data-start="%s" data-duration="%s" data-track-index="3"></div>' % (did, kind, d0_, dd_))
    DM.append([did, secs(t0), secs(t1)])


for c in cards:
    occ = c["occ"]
    if c["t1"] - c["t0"] < 0.2:
        c["t1"] = c["t0"] + 0.2
    s0, d0 = win(c["t0"], c["t1"])
    lines_html = []
    for li, ln in enumerate(c["lines"]):
        toks = ln["tok"]
        sizes = []
        for t in toks:
            sz = next((int(f[2:]) for f in t["flags"] if f.startswith("sz")), STY[t["st"]][1])
            sizes.append(sz)
        txts = [t["txt"].replace("{}", "12") for t in toks]
        width = sum(tw(tx, t["st"], sz) + (1.2 * sz if t["st"] == "p" else 0) for tx, t, sz in zip(txts, toks, sizes)) + 22 * (len(toks) - 1)
        fit = min(1.0, MAXW / (width * 1.03))
        dx = ln["dx"] or ([0, 34, 12, 46][li % 4] * (1 if c["align"] == "left" else -1 if c["align"] == "right" else 0))
        parts = []
        for ti, (t, sz, tx) in enumerate(zip(toks, sizes, txts)):
            n_tok += 1
            tid = "k%d" % n_tok
            words = t["txt"].split(" ")
            per_word = len(t["anc"]) == len(words) and len(words) > 1
            big = t["st"] in BIG
            inner = []
            if "{}" in t["txt"]:                       # count-up token: "{}–13" -> <span class=cnt>12</span>–13
                cid_ = tid + "c"
                inner.append('<span class="w" id="%sw0">%s</span>' % (tid, t["txt"].replace("{}", '<span id="%s">12</span>' % cid_)))
                a0 = edl.mt(t["anc"][0], occ)
                R.append([tid + "w0", a0 - 0.03 + (0.12 if big else 0), 1 if big else 0])
                n_to = int(next(f[3:] for f in t["flags"] if f.startswith("cnt")))
                CNT.append([cid_, a0 + 0.1, n_to])
                for k in range(5):
                    SFX.append(dict(name="tick", t=a0 + 0.1 + k * 0.12, gain=-23 + k * 1.5, align="onset"))
            else:
                for wi, wd in enumerate(words):
                    anc = t["anc"][wi] if per_word else t["anc"][0]
                    wid = "%sw%d" % (tid, wi)
                    inner.append('<span class="w" id="%s" data-layout-allow-overlap>%s</span>' % (wid, wd))
                    if per_word or wi == 0:
                        tr = edl.mt(anc, occ) - 0.03 + (0.12 if big else 0)
                        R.append([tid if t["st"] == "p" else wid, tr, 1 if big else 0])
                        if not per_word:
                            break  # whole token reveals together; remaining words are rendered inside the first span below
                if not per_word:
                    inner = ['<span class="w" id="%sw0" data-layout-allow-overlap>%s</span>' % (tid, t["txt"])]
            tr0 = edl.mt(t["anc"][0], occ) - 0.03 + (0.12 if big else 0)
            extra = ""
            if "ul" in t["flags"]:
                extra += ('<svg class="ul" id="%su" viewBox="0 0 300 24" preserveAspectRatio="none" data-layout-allow-overflow>'
                          '<path d="M4 15 C 52 4, 104 21, 152 11 S 252 17, 296 6" pathLength="1"/></svg>' % tid)
                UL.append([tid + "u", tr0 + 0.28])
            sk = next((f for f in t["flags"] if f.startswith("strike")), None)
            if sk:
                ts = edl.mt(int(sk[6:]), occ)
                extra += '<i class="strike" id="%ss" data-layout-allow-overflow></i>' % tid
                STK.append([tid + "s", tid, ts])
                SFX.append(dict(name="slide", t=ts - 0.02, gain=-15, align="onset"))
            if t["st"] in "xX" and c["id"] not in ("tag", "htitle"):
                SFX.append(dict(name=("up" if (c["id"] in ("h3", "c24d")) else ["pop", "click", "select", "pop"][n_tok % 4]),
                                t=tr0 + 0.04, gain=-13, align="onset"))
            elif t["st"] in "lL" and c["id"] != "htitle":
                SFX.append(dict(name="tick", t=tr0 + 0.02, gain=-19, align="onset"))
            parts.append('<span class="t st-%s" id="%s" style="font-size:%dpx" data-layout-allow-overlap>%s%s</span>'
                         % (t["st"], tid, round(sz * fit), " ".join(inner), extra))
        lines_html.append('<div class="ln" style="margin-left:%dpx">%s</div>' % (max(dx, 0), "".join(parts)) if dx >= 0 else
                          '<div class="ln" style="margin-right:%dpx">%s</div>' % (-dx, "".join(parts)))
    if c["bg"]:
        add_dim(c["bg"], c["t0"], c["t1"])
    html_cards.append('<div id="cd_%s" class="clip card z-%s al-%s" data-start="%s" data-duration="%s" data-track-index="6">%s</div>'
                      % (c["id"], c["zone"], c["align"], s0, d0, "".join(lines_html)))

# ------------------------------------------------------------------ b-roll
html_br, BR = [], []
for bid, clip, w0, w1, mode, lead, tail, _ in edl.BROLL:
    cl = edl.BROLL_CLIPS[clip]
    t0 = edl.mt(w0) - lead
    t1 = min(edl.me(w1) + tail, t0 + cl["dur"] - 0.05)
    s0, d0 = win(t0, t1)
    ow, oh = cl["out"]
    if mode == "full":
        html_br.append('<video id="%s" class="clip bro full" src="assets/br/%s.mp4" muted playsinline data-start="%s" data-duration="%s" '
                       'data-media-start="0" data-track-index="4"></video>' % (bid, clip, s0, d0))
        html_br.append('<div class="clip shade%s" data-start="%s" data-duration="%s" data-track-index="5"></div>' % (" strong" if clip == "total" else "", s0, d0))
    else:
        cw = 930
        ch = round(cw * oh / ow)
        top = round(H / 2 - ch / 2 - 10)
        add_dim("poster", t0, t1)
        html_br.append('<video id="%s" class="clip bro card3d" src="assets/br/%s.mp4" muted playsinline data-start="%s" data-duration="%s" '
                       'data-media-start="0" data-track-index="4" style="left:75px;top:%dpx;width:%dpx;height:%dpx"></video>'
                       % (bid, clip, s0, d0, top, cw, ch))
    BR.append([bid, secs(t0), round(t1 - t0, 3), mode])

# ------------------------------------------------------------------ transitions
html_fx, LK, GL, WH = [], [], [], []
for tr in edl.TRANSITIONS:
    at, dur = tr["at"], tr["dur"]
    if tr["kind"] == "leak":
        t0 = at - dur * 0.36
        html_fx.append('<div id="%s" class="leak"><i class="la"></i><i class="lr"></i><i class="lg"></i></div>' % tr["id"])
        LK.append([tr["id"], secs(t0), dur])
        SFX.append(dict(name=["wh_air_a", "wh_air_b"][(len(LK) - 1) % 2], t=at, gain=-9, align="apex"))
    elif tr["kind"] == "flash":
        html_fx.append('<div id="%s" class="glint"><i></i></div>' % tr["id"])
        GL.append([tr["id"], secs(at - 0.07), dur])
        SFX.append(dict(name=["wh_burst_a", "wh_burst_b"][(len(GL) - 1) % 2], t=at - 0.02, gain=-11, align="apex"))
    elif tr["kind"] == "whip":
        WH.append([secs(at), dur])
        SFX.append(dict(name="wh_swish_a", t=at - 0.03, gain=-9, align="apex"))

# ------------------------------------------------------------------ zoom punch-ins at cuts
Z = [[secs(c["m0"]), c["zoom"]] for c in edl.CUTS]

# ------------------------------------------------------------------ page
CSS = """
@font-face{font-family:'DM Sans';font-weight:100 1000;src:url('assets/fonts/DMSans-var.woff2') format('woff2');}
@font-face{font-family:'Instrument Serif';font-style:italic;font-weight:400;src:url('assets/fonts/InstrumentSerif-italic-latin.woff2') format('woff2');}
:root{--acc:@@ACC@@}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#0a0305}
#root{position:relative;width:1080px;height:1920px;overflow:hidden;background:#0a0305}
#stage{position:absolute;inset:0;overflow:hidden}
.clip{position:absolute;inset:0}
#th{width:1080px;height:1920px;object-fit:cover;transform-origin:50% 42%;z-index:1}
.vig{z-index:2;background:linear-gradient(180deg,rgba(0,0,0,.40) 0%,rgba(0,0,0,0) 26%,rgba(0,0,0,0) 56%,rgba(0,0,0,.52) 100%),radial-gradient(ellipse 85% 70% at 50% 46%,rgba(0,0,0,0) 55%,rgba(0,0,0,.35) 100%);pointer-events:none}
.dim{z-index:3;background:rgba(6,2,4,.42)} .dim.poster{background:rgba(6,2,4,.62)}
.bro{z-index:4;object-fit:cover}
.bro.full{width:1080px;height:1920px;transform-origin:50% 50%}
.card3d{inset:auto;border-radius:34px;box-shadow:0 0 0 2px rgba(255,255,255,.16),0 36px 90px rgba(0,0,0,.6),0 0 110px rgba(255,216,74,.2)}
.shade{z-index:5;background:linear-gradient(180deg,rgba(0,0,0,.45) 0%,rgba(0,0,0,0) 30%,rgba(0,0,0,0) 62%,rgba(0,0,0,.55) 100%);pointer-events:none}
.shade.strong{background:linear-gradient(180deg,rgba(0,0,0,.88) 0%,rgba(0,0,0,.7) 24%,rgba(0,0,0,.0) 46%,rgba(0,0,0,0) 66%,rgba(0,0,0,.5) 100%)}
.card{z-index:6;display:flex;flex-direction:column;padding:0 75px;pointer-events:none}
.z-top{justify-content:flex-start;padding-top:205px}
.z-bot{justify-content:flex-end;padding-bottom:420px}
.z-mid{justify-content:center}
.z-tag{justify-content:flex-start;padding-top:150px}
.al-left{align-items:flex-start} .al-right{align-items:flex-end} .al-center{align-items:center}
.ln{display:flex;align-items:baseline;gap:22px;white-space:nowrap;line-height:.94;padding-top:8px}
.t{display:inline-block;position:relative;text-shadow:0 2px 30px rgba(0,0,0,.5)}
.w{display:inline-block;opacity:0}
.st-x,.st-X,.st-l,.st-L{font-family:'Instrument Serif',serif;font-style:italic;font-weight:400;letter-spacing:-.02em;line-height:.9}
.st-x,.st-l{color:var(--acc)} .st-X,.st-L{color:#fff}
.st-m{font-family:'DM Sans',sans-serif;font-weight:400;letter-spacing:-.03em;color:#fff}
.st-s{font-family:'DM Sans',sans-serif;font-weight:350;letter-spacing:-.02em;color:rgba(255,255,255,.92)}
.st-p{font-family:'DM Sans','Helvetica Neue',Arial,sans-serif;font-weight:800;letter-spacing:-.02em;color:#1a0d08;background:var(--acc);border-radius:999px;padding:.1em .55em .16em;text-shadow:none;box-shadow:0 14px 44px rgba(0,0,0,.4);opacity:0}
.st-p .w{opacity:1}
.st-u{font-family:'DM Sans',sans-serif;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--acc)}
.ul{position:absolute;left:-2%;bottom:-.05em;width:104%;height:.16em;overflow:visible;pointer-events:none;opacity:0}
.ul path{fill:none;stroke:var(--acc);stroke-width:5;stroke-linecap:round;stroke-dasharray:1;stroke-dashoffset:1}
.strike{position:absolute;left:-2%;top:54%;width:104%;height:.045em;background:var(--acc);transform-origin:0 50%;transform:scaleX(0)}
.leak{position:absolute;inset:-18%;z-index:20;opacity:0;mix-blend-mode:screen;pointer-events:none;overflow:hidden}
.leak i{position:absolute;inset:-20%;will-change:transform,opacity}
.leak .la{background:radial-gradient(ellipse 46% 120% at 12% 56%,rgba(255,236,190,.92),transparent 46%),radial-gradient(ellipse 70% 130% at 26% 52%,rgba(255,122,48,.78),transparent 68%);filter:blur(34px)}
.leak .lr{background:radial-gradient(ellipse 52% 112% at 80% 36%,rgba(232,48,52,.62),rgba(255,70,80,.22) 50%,transparent 76%);filter:blur(46px)}
.leak .lg{background:linear-gradient(104deg,transparent 24%,rgba(255,150,64,.32) 40%,rgba(255,236,190,.7) 51%,rgba(255,126,50,.24) 62%,transparent 78%);filter:blur(24px)}
.glint{position:absolute;inset:-12%;z-index:21;opacity:0;mix-blend-mode:screen;pointer-events:none}
.glint i{position:absolute;inset:0;background:radial-gradient(circle at 76% 24%,rgba(255,240,205,.95),rgba(255,190,96,.4) 22%,transparent 56%),linear-gradient(118deg,transparent 38%,rgba(255,236,190,.5) 50%,transparent 62%)}
"""

JS = """
window.__timelines=window.__timelines||{};
const tl=gsap.timeline({paused:true});
tl.to({},{duration:@@DUR@@,ease:'none'},0);
@@DATA@@
Z.forEach(([t,s])=>tl.set('#th',{scale:s},t));
DM.forEach(([id,t0,t1])=>{tl.fromTo('#'+id,{opacity:0},{opacity:1,duration:.2,ease:'power1.out',immediateRender:false},t0);tl.to('#'+id,{opacity:0,duration:.18,ease:'power1.in'},Math.max(t0+.2,t1-.18));});
R.forEach(([id,t,big])=>tl.fromTo('#'+id,{opacity:0,y:big?84:38},{opacity:1,y:0,duration:big?.24:.18,ease:'power3.out',immediateRender:false},t));
UL.forEach(([id,t])=>{tl.to('#'+id,{opacity:1,duration:.01},t);tl.fromTo('#'+id+' path',{strokeDashoffset:1},{strokeDashoffset:0,duration:.32,ease:'power2.out',immediateRender:false},t);});
STK.forEach(([id,tok,t])=>{tl.fromTo('#'+id,{scaleX:0},{scaleX:1,duration:.22,ease:'power2.out',immediateRender:false},t);tl.to('#'+tok+' .w',{opacity:.55,duration:.2},t+.1);});
CNT.forEach(([id,t,n])=>tl.fromTo('#'+id,{textContent:0},{textContent:n,duration:.55,ease:'power1.out',snap:{textContent:1},immediateRender:false},t));
BR.forEach(([id,t,d,mode])=>{
  if(mode==='full') tl.fromTo('#'+id,{scale:1.1},{scale:1,duration:d,ease:'power1.out',immediateRender:false},t);
  else tl.fromTo('#'+id,{scale:.9,y:46,rotateX:9,transformPerspective:1300},{scale:1,y:0,rotateX:0,transformPerspective:1300,duration:.3,ease:'power3.out',immediateRender:false},t);
});
LK.forEach(([id,t,d])=>{
  tl.fromTo('#'+id,{opacity:0},{opacity:.92,duration:d*.3,ease:'sine.out',immediateRender:false},t);
  tl.to('#'+id,{opacity:.5,duration:d*.2,ease:'sine.inOut'},t+d*.3);
  tl.to('#'+id,{opacity:0,duration:d*.5,ease:'sine.in'},t+d*.5);
  tl.fromTo('#'+id+' .la',{xPercent:-30,scale:.92,rotation:-4},{xPercent:26,scale:1.1,rotation:2,duration:d,ease:'sine.inOut',immediateRender:false},t);
  tl.fromTo('#'+id+' .lr',{xPercent:24,yPercent:-8},{xPercent:-20,yPercent:8,duration:d,ease:'sine.inOut',immediateRender:false},t);
  tl.fromTo('#'+id+' .lg',{xPercent:-34,rotation:-6},{xPercent:30,rotation:4,duration:d,ease:'sine.inOut',immediateRender:false},t);
});
GL.forEach(([id,t,d])=>{
  tl.fromTo('#'+id,{opacity:0,scale:.92},{opacity:1,scale:1.06,duration:.07,ease:'power2.out',immediateRender:false},t);
  tl.to('#'+id,{opacity:0,scale:1.22,duration:d-.07,ease:'power2.in'},t+.07);
});
WH.forEach(([t,d])=>{
  tl.fromTo('#stage',{x:0,scale:1,filter:'blur(0px)'},{x:-190,scale:1.1,filter:'blur(20px)',duration:.1,ease:'power2.in',immediateRender:false},t-.1);
  tl.fromTo('#stage',{x:190,scale:1.1,filter:'blur(20px)'},{x:0,scale:1,filter:'blur(0px)',duration:d-.1+.08,ease:'power3.out',immediateRender:false},t);
});
window.__timelines['main']=tl;
"""

data = "const Z=%s,R=%s,UL=%s,STK=%s,CNT=%s,BR=%s,LK=%s,GL=%s,WH=%s;" % tuple(
    json.dumps(x, separators=(",", ":")) for x in (Z, [[a, round(b, 3), c] for a, b, c in R], [[a, round(b, 3)] for a, b in UL],
                                                    [[a, b, round(c, 3)] for a, b, c in STK], [[a, round(b, 3), c] for a, b, c in CNT],
                                                    BR, LK, GL, WH))
data += "const DM=%s;" % json.dumps(DM, separators=(",", ":"))
js = JS.replace("@@DUR@@", fmt(DUR)).replace("@@DATA@@", data)

page = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<title>HYROX scarcity story</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>%s</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="1080" data-height="1920" data-duration="%s" data-fps="30">
<div id="stage">
<video id="th" class="clip" data-layout-allow-overflow src="assets/master.mp4" muted playsinline data-start="0" data-duration="%s" data-media-start="0" data-track-index="0"></video>
<div class="clip vig" data-start="0" data-duration="%s" data-track-index="1"></div>
%s
%s
%s
</div>
%s
<audio id="vo" src="assets/audio/vo.wav" data-start="0" data-duration="%s" data-track-index="9" data-volume="1"></audio>
<audio id="sfx" src="assets/audio/sfx.wav" data-start="0" data-duration="%s" data-track-index="10" data-volume="1"></audio>%s
</div>
<script>%s</script>
</body>
</html>
""" % (CSS.replace("@@ACC@@", ACC), fmt(DUR), fmt(DUR), fmt(DUR), "\n".join(dims), "\n".join(html_br), "\n".join(html_cards),
       "\n".join(html_fx), fmt(DUR), fmt(DUR),
       ('\n<audio id="bgm" src="assets/audio/bgm.wav" data-start="0" data-duration="%s" data-track-index="11" data-volume="1"></audio>' % fmt(DUR))
       if os.path.exists(os.path.join(ROOT, "assets", "audio", "bgm.wav")) else "", js)

open(os.path.join(ROOT, "index.html"), "w").write(page)
os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
SFX.sort(key=lambda e: e["t"])
json.dump(dict(duration=DUR, sfx=[{**e, "t": round(e["t"], 3)} for e in SFX]), open(os.path.join(ROOT, "build", "schedule.json"), "w"), indent=1)
for b in BR: print("  b-roll", b)
for t in edl.TRANSITIONS: print("  trans ", t["id"], t["kind"], round(t["at"], 2))
print("index.html: %d cards, %d tokens, %d b-roll, %d transitions, %d sfx cues, %.2fs" % (len(cards), n_tok, len(BR), len(edl.TRANSITIONS), len(SFX), DUR))
