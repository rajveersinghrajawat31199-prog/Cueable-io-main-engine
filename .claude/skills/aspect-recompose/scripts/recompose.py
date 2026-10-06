#!/usr/bin/env python3
"""aspect-recompose engine: derive a native-aspect sibling of an approved project WITHOUT touching audio or timelines.

  recompose.py init  --src videos/P --aspect 9:16 [--dst videos/P-9x16]   scaffold sibling + one override stub per scene
  recompose.py build --dst videos/P-9x16                                  regenerate dst/compositions/frames from SRC + dst/recompose/*
  recompose.py list  --dst videos/P-9x16                                  scenes, window in the timeline, override status

Per scene the dst folder holds  recompose/<scene>.css  (appended after the scene's own CSS, wins on cascade)
and optionally                  recompose/<scene>.json (ordered [{"find","replace"[,"count"]}] edits to the scene HTML/JS;
a find that does not match is an ERROR, never silent). The source scene is never edited; the sibling is rebuilt from it,
so a fix to the horizontal master can be re-propagated by re-running build."""
import argparse, json, os, re, shutil, sys

ASPECTS = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}
COPY = ["assets", "compositions", "index.html", "package.json", "hyperframes.json", "hyperframes.lock.json",
        "meta.json", "launch.config.json", "audio_meta.json", "frame.md", "BRIEF.md", "SCRIPT.md"]

def scenes_of(index_html):
    """[(src_path, start, duration)] for every data-composition-src scene in index.html"""
    out = []
    for m in re.finditer(r'<div[^>]*data-composition-src="([^"]+)"[^>]*>', index_html):
        tag = m.group(0)
        st = float(re.search(r'data-start="([\d.]+)"', tag).group(1))
        du = float(re.search(r'data-duration="([\d.]+)"', tag).group(1))
        out.append((m.group(1), st, du))
    return out

def retarget_root(html, w, h):
    html = re.sub(r'width=\d+, height=\d+', f'width={w}, height={h}', html)
    html = re.sub(r'width: \d+px;(\s*)height: \d+px;', rf'width: {w}px;\1height: {h}px;', html)
    html = re.sub(r'data-width="\d+" data-height="\d+"', f'data-width="{w}" data-height="{h}"', html)
    return html

def cmd_init(a):
    src = a.src.rstrip("/")
    w, h = ASPECTS[a.aspect]
    dst = a.dst or f"{src}-{a.aspect.replace(':', 'x')}"
    if os.path.exists(dst) and os.listdir(dst):
        sys.exit(f"{dst} already exists; refusing to overwrite")
    os.makedirs(dst + "/renders", exist_ok=True)
    for n in COPY:
        p = os.path.join(src, n)
        if os.path.isdir(p): shutil.copytree(p, os.path.join(dst, n))
        elif os.path.exists(p): shutil.copy(p, os.path.join(dst, n))
    idx = open(f"{dst}/index.html").read()
    open(f"{dst}/index.html", "w").write(retarget_root(idx, w, h))
    used = {os.path.basename(s) for s, _, _ in scenes_of(idx)}
    for f in os.listdir(f"{dst}/compositions/frames"):
        if f not in used: os.remove(f"{dst}/compositions/frames/{f}")
    for jn in ("meta.json", "package.json"):
        p = f"{dst}/{jn}"
        if os.path.exists(p):
            t = open(p).read().replace(os.path.basename(src), os.path.basename(dst)); open(p, "w").write(t)
    json.dump({"src": os.path.relpath(src, dst), "aspect": a.aspect, "width": w, "height": h}, open(f"{dst}/recompose.json", "w"), indent=1)
    os.makedirs(f"{dst}/recompose", exist_ok=True)
    for s, st, du in scenes_of(idx):
        n = os.path.basename(s)[:-5]
        p = f"{dst}/recompose/{n}.css"
        if not os.path.exists(p):
            open(p, "w").write(f"/* {a.aspect} layout for {n}  ({st:.2f}s +{du:.2f}s) */\n")
    print(f"scaffolded {dst}  ({w}x{h}); {len(used)} scenes; edit recompose/*.css then: recompose.py build --dst {dst}")

def cmd_build(a):
    dst = a.dst.rstrip("/")
    cfg = json.load(open(f"{dst}/recompose.json"))
    src = os.path.normpath(os.path.join(dst, cfg["src"]))
    w, h = cfg["width"], cfg["height"]
    idx = open(f"{dst}/index.html").read()
    bad = 0
    for s, st, du in scenes_of(idx):
        n = os.path.basename(s)[:-5]
        html = open(f"{src}/{s}").read()
        html = re.sub(r'data-width="\d+" data-height="\d+"', f'data-width="{w}" data-height="{h}"', html, count=1)
        css = open(f"{dst}/recompose/{n}.css").read() if os.path.exists(f"{dst}/recompose/{n}.css") else ""
        jp = f"{dst}/recompose/{n}.json"
        for e in (json.load(open(jp)) if os.path.exists(jp) else []):
            c = html.count(e["find"])
            if c == 0 or (e.get("count") and c != e["count"]):
                print(f"ERROR {n}: edit {e['find'][:60]!r} matched {c}x"); bad += 1; continue
            html = html.replace(e["find"], e["replace"])
        html = html.replace("</style>", f"/* ---- {cfg['aspect']} recompose ---- */\n{css}\n</style>", 1)
        open(f"{dst}/{s}", "w").write(html)
    sys.exit(1 if bad else 0) if bad else print("built", len(scenes_of(idx)), "scenes")

def cmd_list(a):
    dst = a.dst.rstrip("/")
    idx = open(f"{dst}/index.html").read()
    for s, st, du in scenes_of(idx):
        n = os.path.basename(s)[:-5]
        p = f"{dst}/recompose/{n}.css"
        lines = len(open(p).read().strip().splitlines()) - 1 if os.path.exists(p) else 0
        print(f"{st:7.2f}s +{du:5.2f}s  {n:34s} override css lines: {lines}")

def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    i = sp.add_parser("init"); i.add_argument("--src", required=True); i.add_argument("--aspect", default="9:16", choices=ASPECTS); i.add_argument("--dst")
    b = sp.add_parser("build"); b.add_argument("--dst", required=True)
    l = sp.add_parser("list"); l.add_argument("--dst", required=True)
    a = ap.parse_args(); {"init": cmd_init, "build": cmd_build, "list": cmd_list}[a.cmd](a)

if __name__ == "__main__":
    main()
