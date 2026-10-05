#!/usr/bin/env python3
"""Motion skeleton from a motion-spec: a HyperFrames project whose elements move EXACTLY like the measured ones (position, size, lifetime per frame), drawn as plain shapes.
Restyle it afterwards (colours, radii, shadows, photos, real text) instead of re-measuring and re-coding every move.

  python3 build_from_spec.py --spec motion-spec.json --out DIR [--frames A:B] [--min-area 400] [--template ../../videos/<project>]

Flat tracks -> coloured rounded boxes (colour and corner radius measured); photo-like tracks -> striped placeholder boxes; ink tracks -> dark bars (typing growth is kept);
the pointer -> its sprite as a PNG moved/scaled by the measured tip path. Every element has id e_<track id> and data-role, so a restyle pass can target roles.
"""
import argparse
import base64
import io
import json
import math
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from refkit import cursor as cur  # noqa: E402

FPS = 30
PRE = """
const F=30, S0=@@S0@@;
const tl=gsap.timeline({paused:true});
const $=(s)=>document.querySelector(s);
const TN=(g)=>Math.floor((g-S0)*1e6/F)/1e6;
// P: place an element on every frame of its life from measured boxes [[x0,y0,x1,y1],...]; only changes are written
function P(sel,f0,boxes){
  const el=$(sel); let prev=null;
  for(let i=0;i<boxes.length;i++){
    const b=boxes[i], k=b.join(',');
    if(k!==prev){ tl.set(el,{x:b[0],y:b[1],width:b[2]-b[0],height:b[3]-b[1],opacity:1},TN(f0+i)); prev=k; }
  }
  tl.set(el,{opacity:0},TN(f0+boxes.length));
}
// C: the pointer from measured tips [[f,x,y,scale],...] (gaps of up to 3 frames are bridged)
function C(sel,tipx,tipy,pts){
  const el=$(sel);
  for(let i=0;i<pts.length;i++){
    const p=pts[i]; tl.set(el,{x:p[1]-tipx,y:p[2]-tipy,scale:p[3],opacity:1},TN(p[0]));
    const nx=pts[i+1]; if(nx && nx[0]-p[0]>1){ for(let g=p[0]+1;g<nx[0];g++){ const a=(g-p[0])/(nx[0]-p[0]); tl.set(el,{x:p[1]+(nx[1]-p[1])*a-tipx,y:p[2]+(nx[2]-p[2])*a-tipy,scale:p[3]+(nx[3]-p[3])*a,opacity:nx[0]-p[0]>4?0:1},TN(g)); } }
    if(!nx) tl.set(el,{opacity:0},TN(p[0]+1));
  }
}
"""


def clip_window(a, b):
    start = 0.0 if a == 0 else math.floor((a / FPS - 1e-5) * 1e5) / 1e5
    end = math.floor(((b + 1) / FPS - 1e-5) * 1e5) / 1e5
    return start, round(end - start, 5)


def make_warp(path, A):
    """ref frame -> film frame (relative to frame A) and its inverse from a warp.json [[ref, film], ...]; identity when no file."""
    if not path:
        return (lambda f: float(f - A)), (lambda g: float(g + A))
    pts = json.load(open(path))
    xs = np.array([p[0] for p in pts], float)
    ys = np.array([p[1] for p in pts], float)
    fw = lambda f: float(np.interp(f, xs, ys, left=ys[0] + (f - xs[0]), right=ys[-1] + (f - xs[-1])))
    gi = lambda g: float(np.interp(g, ys, xs, left=xs[0] + (g - ys[0]), right=xs[-1] + (g - ys[-1])))
    return fw, gi


def resample_boxes(boxes, f0, lo, hi, fw, gi):
    """per-film-frame boxes for ref frames lo..hi: returns (first film frame, [box,...])."""
    G0, G1 = int(round(fw(lo))), int(round(fw(hi)))
    out = []
    for g in range(G0, G1 + 1):
        f = min(max(gi(g), lo), hi)
        i = int(math.floor(f - f0))
        i = min(max(i, 0), len(boxes) - 1)
        j = min(i + 1, len(boxes) - 1)
        t = (f - f0) - i
        out.append([int(round(boxes[i][k] + (boxes[j][k] - boxes[i][k]) * t)) for k in range(4)])
    return G0, out


def sprite_png(name):
    from PIL import Image
    sp = cur.load_sprite(name)
    h, w = sp["outline"].shape
    a = np.zeros((h, w, 4), np.uint8)
    sil = np.maximum(sp["outline"], sp["fill"]) > 0.5
    from scipy import ndimage as ndi
    sil = ndi.binary_fill_holes(sil | ndi.binary_dilation(sil, iterations=1))
    a[sil] = (255, 255, 255, 255)
    a[sp["outline"] > 0.5] = (17, 17, 17, 255)
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), w, h, sp["tip"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames")
    ap.add_argument("--min-area", type=int, default=400)
    ap.add_argument("--warp", help="warp.json from beatwarp.py: retime the reference frames onto the music's beat grid")
    ap.add_argument("--text-bars", action="store_true", help="draw ink tracks as dark bars instead of their OCR text (for round-trip tests)")
    ap.add_argument("--template", help="an existing project whose hyperframes.json/package.json are copied")
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    W, H = spec["source"]["width"], spec["source"]["height"]
    A, B = spec["measured"]
    if a.frames:
        A, B = [int(v) for v in a.frames.split(":")]
    out = a.out
    os.makedirs(os.path.join(out, "compositions"), exist_ok=True)
    for f in ("hyperframes.json", "package.json"):
        src = os.path.join(a.template, f) if a.template else None
        if src and os.path.exists(src):
            shutil.copy(src, os.path.join(out, f))
    name = os.path.basename(os.path.abspath(out))
    if not os.path.exists(os.path.join(out, "package.json")):
        json.dump(dict(name=name, private=True, type="module", scripts={k: "npx --yes hyperframes@0.8.113 " + v for k, v in dict(dev="preview", check="check", render="render").items()}), open(os.path.join(out, "package.json"), "w"), indent=2)
    if not os.path.exists(os.path.join(out, "hyperframes.json")):
        json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json", "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}}, open(os.path.join(out, "hyperframes.json"), "w"), indent=2)
    json.dump(dict(id=name, name=name, createdAt="2026-01-01T00:00:00.000Z"), open(os.path.join(out, "meta.json"), "w"), indent=2)
    segs = [s for s in spec["segments"] if s["frames"][1] >= A and s["frames"][0] <= B]
    fw, gi = make_warp(a.warp, A)
    hosts, total = [], int(round(fw(B + 1)))
    cur_png = None
    if spec.get("cursor") and spec["cursor"].get("sprite") in cur.available():
        cur_png = sprite_png(spec["cursor"]["sprite"])
    for n, sg in enumerate(segs, start=1):
        s0, s1 = max(sg["frames"][0], A), min(sg["frames"][1], B)
        g0, g1 = int(round(fw(s0))), int(round(fw(s1 + 1))) - 1
        cid = "seg%d" % sg["index"]
        tracks = [t for t in spec["tracks"] if t["segment"] == sg["index"] and not t.get("junk") and t["frames"][1] >= s0 and t["frames"][0] <= s1]
        tracks = [t for t in tracks if t["cls"] != "ink" and max((b[2] - b[0]) * (b[3] - b[1]) for b in t["boxes"]) >= a.min_area or t["cls"] == "ink" and t["frames"][1] - t["frames"][0] >= 3]
        order = {"flat": 0, "photo": 1, "ink": 2}
        tracks.sort(key=lambda t: (order[t["cls"]], -((t["boxes"][0][2] - t["boxes"][0][0]) * (t["boxes"][0][3] - t["boxes"][0][1]))))
        els, js = [], []
        for z, t in enumerate(tracks, start=1):
            f0 = t["frames"][0]
            bx = t["boxes"]
            lo, hi = max(f0, s0), min(t["frames"][1], s1)
            G0, sel_boxes = resample_boxes(bx, f0, lo, hi, fw, gi)
            eid = "e_" + t["id"]
            if t["cls"] == "flat":
                r = t.get("radius")
                css = "background:%s;border-radius:%spx" % (t.get("color") or "#ddd", ("%.1f" % r) if r else "0")
            elif t["cls"] == "photo":
                css = "background:repeating-linear-gradient(45deg,#8c8c8c 0 5px,#bdbdbd 5px 10px)"
            elif t.get("text") and not a.text_bars:
                tb = t.get("text_box") or t["boxes"][0]
                px = t.get("font_px_est") or max(10, (tb[3] - tb[1]) / 0.8)
                col = t.get("ink_color") or "#222"
                css = "overflow:hidden;white-space:nowrap;color:%s;font:400 %.1fpx/1 Inter,Helvetica,Arial,sans-serif" % (col, px)
            else:
                css = "background:#2a2a2a;border-radius:2px"
            inner = ""
            if t["cls"] == "ink" and t.get("text") and not a.text_bars:
                tb = t.get("text_box") or t["boxes"][0]
                bb0 = t["boxes"][max(range(len(t["boxes"])), key=lambda i: t["boxes"][i][2] - t["boxes"][i][0])]
                inner = '<span class="fit" data-w="%d" style="position:absolute;left:%dpx;top:%dpx">%s</span>' % (tb[2] - tb[0], tb[0] - bb0[0], tb[1] - bb0[1], t["text"].replace("&", "&amp;").replace("<", "&lt;"))
            els.append('<div id="%s" class="el" data-role="%s" data-layout-allow-overflow data-layout-allow-overlap data-layout-allow-occlusion style="z-index:%d;%s">%s</div>' % (eid, t.get("role", t["cls"]), z, css, inner))
            js.append("P('#%s',%d,%s);" % (eid, G0, json.dumps(sel_boxes, separators=(",", ":"))))
        if cur_png and spec.get("cursor"):
            pts = [[int(round(fw(p[0]))), p[1], p[2], p[3]] for p in spec["cursor"]["track"] if s0 <= p[0] <= s1]
            if pts:
                src, w, h, tip = cur_png
                els.append('<img id="cursor" class="el" data-layout-allow-overflow data-layout-allow-overlap data-layout-allow-occlusion src="%s" style="z-index:9000;width:%dpx;height:%dpx;transform-origin:%.1fpx %.1fpx;background:none"/>' % (src, w, h, tip[0], tip[1]))
                js.append("C('#cursor',%.1f,%.1f,%s);" % (tip[0], tip[1], json.dumps([[p[0], round(p[1], 1), round(p[2], 1), round(p[3], 2)] for p in pts], separators=(",", ":"))))
        html = """<!doctype html>
<html><head><meta charset="UTF-8" /></head><body>
<template>
<style>
#root{position:absolute;inset:0;overflow:hidden;background:%s;}
.el{position:absolute;left:0;top:0;width:10px;height:10px;opacity:0;}
</style>
<div id="root" data-composition-id="%s" data-width="%d" data-height="%d">
%s
</div>
<script>
%s
%s
// text is fitted to the measured width of the reference's text (the reference's face is not available: the font size absorbs the difference)
document.querySelectorAll('.fit').forEach(function(sp){var w=sp.getBoundingClientRect().width,t=parseFloat(sp.dataset.w);if(w>2&&t>2){sp.style.fontSize=(parseFloat(getComputedStyle(sp).fontSize)*t/w).toFixed(2)+'px';}});
window.__timelines["%s"]=tl;
</script>
</template>
</body></html>
""" % (sg["bg"], cid, W, H, "\n".join(els), PRE.replace("@@S0@@", str(g0)), "\n".join(js), cid)
        open(os.path.join(out, "compositions", cid + ".html"), "w").write(html)
        st, du = clip_window(g0, g1)
        hosts.append('<div id="host-%s" class="clip" data-composition-id="%s" data-composition-src="compositions/%s.html" data-start="%s" data-duration="%s" data-track-index="%d" data-width="%d" data-height="%d"></div>' % (cid, cid, cid, st, du, n, W, H))
    idx = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=%d, height=%d" />
<title>%s skeleton</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:%dpx;height:%dpx;overflow:hidden;background:#fff;}
#root{position:relative;width:100%%;height:100%%;overflow:hidden;background:#fff;}
.clip{position:absolute;inset:0;}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="%d" data-height="%d" data-duration="%s" data-fps="30">
%s
</div>
<script>
const tl=gsap.timeline({paused:true});
window.__timelines["main"]=tl;
</script>
</body>
</html>
""" % (W, H, name, W, H, W, H, round(total / FPS, 5), "\n".join(hosts))
    open(os.path.join(out, "index.html"), "w").write(idx)
    print("skeleton:", out, "| segments", [s["index"] for s in segs], "| frames", total, "| film frame 0 = reference frame", A)


if __name__ == "__main__":
    main()
