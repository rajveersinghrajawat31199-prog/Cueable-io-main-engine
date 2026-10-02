#!/usr/bin/env bash
# Rebuild everything downstream of the storyboard for one launch video. Idempotent. Run from anywhere:
#   build_all.sh <project_dir> [--render draft|high]
# Steps: pad VO -> sync durations into STORYBOARD.md -> SFX+BGM -> project frame builders -> assemble -> lint -> check
#        -> (optional) render -> critique. Never edits any skill. Stops on the first failure.
set -euo pipefail
P="$(cd "${1:?project dir}" && pwd)"; shift || true
Q=""; [ "${1:-}" = "--render" ] && Q="${2:-draft}"
SK="$HOME/.claude/skills/product-launch-video/scripts"     # upstream engine scripts (read-only use)
LV="$(cd "$(dirname "$0")" && pwd)"
cd "$P"
export HYPERFRAMES_SKIP_SKILLS=1                            # never let init/render refresh skills mid-run
python3 "$LV/pad_vo.py" --project . | tail -1
node "$SK/audio.mjs" sync-durations --audio-meta ./audio_meta.json --storyboard ./STORYBOARD.md | tail -1
python3 "$LV/gen_sfx.py" --project .
for b in scripts/build_*frames*.py; do [ -e "$b" ] && python3 "$b" >/dev/null && echo "built via $b"; done
node "$SK/assemble-index.mjs" --storyboard ./STORYBOARD.md --hyperframes . | grep -E "total duration|sfx|bgm|voice"
npx hyperframes lint 2>&1 | tail -3
npx hyperframes check 2>&1 | grep -E "✗|Check " || true
if [ -n "$Q" ]; then
  mkdir -p renders
  npx hyperframes render --skill=product-launch-video --quality "$Q" --output "renders/${Q}.mp4" 2>&1 | grep -E " MB "
  python3 "$HOME/.claude/skills/video-critique/scripts/critique.py" "renders/${Q}.mp4" --project . 2>&1 | grep -vE "^\[PASS\]"
fi
