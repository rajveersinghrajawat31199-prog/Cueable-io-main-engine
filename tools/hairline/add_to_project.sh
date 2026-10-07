#!/bin/sh
# usage: tools/hairline/add_to_project.sh videos/<project>
# Copies the seek-safe Hairline bundle into the project's assets/. Then in index.html:
#   <script src="assets/hairline.bundle.js"></script>   (see .claude/skills/hairline-figures/SKILL.md)
set -e
here=$(cd "$(dirname "$0")" && pwd)
[ -d "$1" ] || { echo "usage: $0 videos/<project>"; exit 1; }
mkdir -p "$1/assets"
cp "$here/dist/hairline.bundle.js" "$1/assets/hairline.bundle.js"
echo "installed $1/assets/hairline.bundle.js ($(wc -c < "$here/dist/hairline.bundle.js") bytes)"
