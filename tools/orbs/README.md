# thinking-orbs (vendored)

`thinking-orbs` 0.3.2, MIT (`lib/LICENSE`), by Jakub Antalik: github.com/Jakubantalik/thinking-orbs
- `lib/` unmodified npm dist (engine only: pure geometry, no React/DOM).
- `src/driver.js` OUR code: brand-tinted canvas painter, state timeline + cross-fade, GSAP bind. `dist/orbs.bundle.js` is the build (global `Orbs`).
- `states.json` per-state meaning + keywords for the picker; `orbs_scene.py pick|make` generator; render gate is `tools/hairline/check_figures.py <mp4> <project> assets/orbs`.
- `test/catalog.html` all 9 states x 2 sizes. Usage and rules: `.claude/skills/thinking-orbs/SKILL.md`.
