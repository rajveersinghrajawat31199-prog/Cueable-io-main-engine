"""lv_lib — building blocks for launch-video frame builders. STYLE-AGNOSTIC: no brand, palette, or layout lives here.
A project's own builder script (scripts/build_frames_*.py) imports this and supplies its own CSS/HTML/JS per frame.

Templates are plain strings with %P% (frame prefix, e.g. "f05") placeholders so CSS/JS braces stay readable.

    from lv_lib import *
    P = Project(".")                       # reads frame.md for @font-face lines
    wrap(P, "05-ads-team", "f05", 3.6, css, body, js)
"""
import os, re

class Project:
    def __init__(self, root="."):
        self.root = os.path.abspath(root)
        self.out = os.path.join(self.root, "compositions", "frames")
        os.makedirs(self.out, exist_ok=True)

    def fonts(self, families=None):
        """@font-face lines the design step staged into frame.md (already point at assets/fonts/*).
        families: optional list to keep (e.g. ["Manrope", "Newsreader"]); None keeps all."""
        md = open(os.path.join(self.root, "frame.md"), encoding="utf8").read()
        lines = [l for l in md.splitlines() if l.startswith("@font-face")]
        if families:
            lines = [l for l in lines if any(("font-family:" + f) in l for f in families)]
        # de-duplicate (frame.md sometimes repeats the block)
        seen, out = set(), []
        for l in lines:
            if l not in seen: seen.add(l); out.append(l)
        return "\n".join(out)

# ---------------------------------------------------------------- shared CSS / JS
COMMON_CSS = """
.%P%-chip{display:inline-flex;align-items:center;height:44px;padding:0 20px;border-radius:100px;font-size:22px;font-weight:700;white-space:nowrap}
.%P%-cap{position:absolute;left:0;right:0;top:892px;text-align:center;font-size:40px;line-height:48px;letter-spacing:-0.01em;white-space:nowrap}
.%P%-cw{display:inline-block}
"""
# NOTE: colours are deliberately NOT in COMMON_CSS. Chip/caption colours come from the project's frame.md tokens.

CURSOR_CSS = """
#%P%-cursor{position:absolute;left:0;top:0;width:76px;height:76px;filter:drop-shadow(0 4px 6px rgba(0,0,0,.28));z-index:50}
#%P%-ripple{position:absolute;left:21%;top:14%;width:50px;height:50px;margin:-25px 0 0 -25px;border-radius:50%;border:4px solid rgba(87,53,252,.5);opacity:0}
"""

def cursor_svg(fill="#1c1c1c", stroke="#ffffff"):
    return (f'<svg viewBox="0 0 24 24" width="76" height="76" aria-hidden="true"><path d="M5 3 L5 19 L9 15 L12 22 L15 20.5 L11.5 14 L18 14 Z" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round"/></svg>')

def cursor_html(fill="#1c1c1c", stroke="#ffffff"):
    return '<div id="%P%-cursor" data-layout-allow-overflow><div id="%P%-ripple"></div>' + cursor_svg(fill, stroke) + '</div>'

# JS helpers inserted at the top of every frame script.
#   rev(sel,t,d,y)      fromTo fade+rise reveal
#   pos(el)             absolute {x,y,w,h} of an element in root coordinates (uses offsetLeft/Top: unaffected by transforms)
#   cursorPress(...)    tip-anchored press: compress to .84, release, ripple
JS_HELPERS = """
const rev=(sel,t,d,y)=>tl.fromTo(sel,{opacity:0,y:(y===undefined?14:y)},{opacity:1,y:0,duration:(d||0.4),ease:"power3.out"},t);
function pos(el){let x=0,y=0,e=el;while(e&&e.id!=="root"){x+=e.offsetLeft;y+=e.offsetTop;e=e.offsetParent;}return {x:x,y:y,w:el.offsetWidth,h:el.offsetHeight};}
function cursorPress(cur,rip,t){
  tl.to(cur,{scale:0.84,transformOrigin:"21% 14%",duration:0.1,ease:"power2.in"},t);
  tl.to(cur,{scale:1,transformOrigin:"21% 14%",duration:0.22,ease:"power2.out"},t+0.1);
  tl.fromTo(rip,{opacity:0.85,scale:0.4},{opacity:0,scale:2.4,duration:0.42,ease:"power2.out"},t+0.1);
}
"""

def caption_html(p, words, bold_upto=0):
    """words: [(text, onset_s)]. Word spans; first `bold_upto` get class {p}-cb (style it in your css)."""
    return " ".join(f'<span class="{p}-cw{" "+p+"-cb" if i < bold_upto else ""}" id="{p}-cw{i}">{w}</span>' for i, (w, t) in enumerate(words))

def caption_js(p, words, lead=0.05):
    """reveal each caption word `lead` s before its VO onset."""
    return "\n".join(f'tl.fromTo("#{p}-cw{i}",{{opacity:0,y:10}},{{opacity:1,y:0,duration:0.32,ease:"power3.out"}},{max(0.0, t-lead):.2f});' for i, (w, t) in enumerate(words))

def wrap(P, fid, p, dur, css, body, js, fonts=None, bg="#FFFFFF"):
    """Write compositions/frames/<fid>.html as one bare <template>. Root is styled by #root (never a class);
    the full-bleed ground is its own clip layer (never the root)."""
    css = (COMMON_CSS + css).replace("%P%", p)
    body = body.replace("%P%", p)
    js = (JS_HELPERS + js).replace("%P%", p)
    fonts = fonts if fonts is not None else P.fonts()
    html = f'''<template>
<style>
{fonts}
#root{{position:absolute;inset:0;font-family:system-ui,sans-serif}}
#{p}-bg{{position:absolute;inset:0;background:{bg}}}
#{p}-stage{{position:absolute;inset:0}}
{css}
</style>
<div id="root" data-composition-id="{fid}" data-width="1920" data-height="1080">
  <div id="{p}-bg" class="clip" data-start="0" data-duration="{dur}" data-track-index="0"></div>
  <div id="{p}-stage" class="clip" data-start="0" data-duration="{dur}" data-track-index="1">
{body}
  </div>
</div>
<script>
(function(){{
const tl = gsap.timeline({{ paused: true }});
{js}
window.__timelines = window.__timelines || {{}};
window.__timelines["{fid}"] = tl;
}})();
</script>
</template>
'''
    open(os.path.join(P.out, fid + ".html"), "w").write(html)
