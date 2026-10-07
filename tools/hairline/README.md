# Hairline (vendored)

`@lucasmarkes/hairline` 0.3.0, MIT (see `lib/LICENSE`). 27 isometric SVG line figures that answer the pointer.
Source: https://github.com/lucasmarkes/hairline · site: https://hairline.lucasmarkes.com

- `lib/` unmodified npm dist (index.js, index.d.ts, LICENSE).
- `src/driver.js` OUR code: virtual 60 fps clock + scripted pointer so figures are seek-safe in renders.
  `src/reference-clock.js` is the upstream test clock it was modelled on.
- `dist/hairline.bundle.js` built bundle (global `Hairline`). Rebuild:
  `npx --yes esbuild tools/hairline/src/driver.js --bundle --format=iife --global-name=Hairline --outfile=tools/hairline/dist/hairline.bundle.js`
- `test/catalog.html` all 27 figures; `?t=1.2` seek time, `?mode=rest`, `?dark=1`. Serve `tools/hairline` (launch config `hairline-test`, port 3011).
- `example/index.html` working 3-figure composition. `add_to_project.sh videos/<p>` installs the bundle.
- Usage + catalogue: `.claude/skills/hairline-figures/SKILL.md`.

- `gestures.json` per-figure: shelf, what it says, `fits` keywords (for the picker), preset pointer path.
- `hairline_scene.py pick|make` automatic picker + beat generator; `check_figures.py` render gate (off-frame / blank / static).
