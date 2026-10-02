#!/usr/bin/env bash
# Subframe motion blur for a HyperFrames project: render at fps*SUB, average groups of subframes with ffmpeg tmix, keep one per group.
# The whole film is a pure function of time, so each subframe is an exact sample: this is real temporal blur, not a filter.
#
# usage: render_blur.sh [project-dir=.] [--fps 60] [--sub 4] [--shutter 180|360] [--quality looks] [--out renders/final.mp4] [--crf 12] [--workers auto|N] [--keep]
#   --shutter 180 (default) averages the first half of each group's subframes (film-style); 360 averages all of them (smearier).
#   Cost: render time is ~SUB x the plain render (60 fps x 4 = 240 fps, the CLI maximum). --sub 1 = no blur (plain render).
set -euo pipefail
DIR="."; FPS=60; SUB=4; SHUTTER=180; Q=looks; OUT=renders/final.mp4; CRF=12; WORKERS=4; KEEP=0
if [ $# -gt 0 ] && [[ "$1" != --* ]]; then DIR="$1"; shift; fi
while [ $# -gt 0 ]; do case "$1" in
  --fps) FPS="$2"; shift 2;; --sub) SUB="$2"; shift 2;; --shutter) SHUTTER="$2"; shift 2;;
  --quality) Q="$2"; shift 2;; --out) OUT="$2"; shift 2;; --crf) CRF="$2"; shift 2;; --workers) WORKERS="$2"; shift 2;; --keep) KEEP=1; shift;; *) echo "unknown arg $1"; exit 1;; esac; done
cd "$DIR"; mkdir -p renders
HI=$((FPS*SUB)); [ "$HI" -le 240 ] || { echo "fps*sub=$HI exceeds the renderer maximum of 240"; exit 1; }
N=$(( SUB*SHUTTER/360 )); [ "$N" -ge 1 ] || N=1
TMP="renders/.sub-$HI.mp4"
export HYPERFRAMES_SKIP_SKILLS=1
if [ "$SUB" -le 1 ]; then npx --yes hyperframes@0.8.55 render --quality "$Q" --fps "$FPS" -o "$OUT" --quiet; echo "wrote $OUT (no blur)"; exit 0; fi
npx --yes hyperframes@0.8.55 render --quality "$Q" --fps "$HI" --crf 10 --workers "$WORKERS" -o "$TMP" --quiet
# average N consecutive subframes; keep the frame whose window starts at the output frame's own time
ffmpeg -y -v error -i "$TMP" -vf "tmix=frames=${N},select='eq(mod(n\,${SUB})\,$((N-1)))',setpts=N/${FPS}/TB" -r "$FPS" -c:v libx264 -crf "$CRF" -pix_fmt yuv420p -movflags +faststart "$OUT"
[ "$KEEP" = 1 ] || rm -f "$TMP"
echo "wrote $OUT  (${FPS} fps, ${SUB} subframes, ${SHUTTER} deg shutter)"
