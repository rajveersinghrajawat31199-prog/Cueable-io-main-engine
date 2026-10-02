#!/usr/bin/env bash
# Scaffold a UI-morph-loop project from the skill template.
# usage: new_project.sh <project-name>     -> creates videos/<project-name>/ in the studio root
set -euo pipefail
NAME="${1:?usage: new_project.sh <project-name>}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
STUDIO="$(cd "$HERE/../../.." && pwd)"
DEST="$STUDIO/videos/$NAME"
[ -e "$DEST" ] && { echo "refusing to overwrite $DEST"; exit 1; }
mkdir -p "$DEST/lib" "$DEST/scripts" "$DEST/renders"
cp -R "$HERE/template/assets" "$DEST/assets"
cp "$HERE/template/index.html" "$HERE/template/film.js" "$DEST/"
cp "$HERE/lib/morph.js" "$DEST/lib/morph.js"          # project-local copy: re-renders stay identical when the skill evolves
for f in "$HERE"/scripts/*; do
  b="$(basename "$f")"; [ "$b" = "new_project.sh" ] && continue; cp "$f" "$DEST/scripts/$b"
done
printf '{"id":"%s","name":"%s"}\n' "$NAME" "$NAME" > "$DEST/meta.json"
cat > "$DEST/hyperframes.json" <<'J'
{
  "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
  "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
  "paths": { "blocks": "compositions", "components": "compositions/components", "assets": "assets" },
  "media": { "autoProxy": true }
}
J
cat > "$DEST/package.json" <<J
{
  "name": "$NAME",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "npx --yes hyperframes@0.8.55 preview",
    "check": "npx --yes hyperframes@0.8.55 check",
    "render": "npx --yes hyperframes@0.8.55 render"
  }
}
J
echo "created $DEST"
echo "next: edit film.js (states, cursor, layers) + index.html (layer markup), then: cd videos/$NAME && HYPERFRAMES_SKIP_SKILLS=1 npm run check"
