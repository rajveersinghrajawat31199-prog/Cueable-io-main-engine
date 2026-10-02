# Build gotchas (each one cost time on the benchmark)

## Composition contract
- One bare `<template>`; every `<style>`/`<script>` inside it. Root styled by `#root` (never a class); the full-bleed ground
  is its own `class="clip"` layer. Frames use the host's GSAP; do not load it again.
- Every timed element: `class="clip"` + `data-start` + `data-duration` + `data-track-index`. Frame `data-duration` == the
  storyboard duration (rebuild after `sync-durations`).
- Prefix ids and classes with the frame prefix (`f05-`). **An id collision is silent**: `#f03-h1` (heading) vs
  `#f03-h{i}` (chips) made two elements share a tween; lint's `gsap_repeated_fromto_without_baseline` caught it. Use
  distinct stems (`k` for chips, `c` for chars).
- Seek-safe only: no `repeat`/`yoyo`, no `Date.now`/`Math.random`, no CSS transitions, no `onUpdate` counters.
  Chain explicit tweens or `tl.set` steps instead.
- Never put a CSS `transform` on an element GSAP animates a transform on (centre with `inset`/margins).
- `fromTo` applies its from-state at build time: fine for hidden-until-later elements; add `gsap.set` baselines when the same
  element gets several `fromTo`s. Overlapping tweens on one property: shorten one or move the later one.

## GSAP + SVG
- `svgOrigin` + `x/y` across two consecutive tweens on one group ends off-canvas. Nested groups: outer = translate, inner =
  scale/rotate with `svgOrigin` set once. Verify the end state numerically (`getBoundingClientRect` in headless Chrome).
- Animating a gradient: `attr:{x1,x2}` from an offset to the ORIGINAL values.
- Inline `<svg>` clips its content to the viewBox by default: `overflow:visible` if a part scales beyond it.

## Layout checks
- `content_overlap` errors on big numerals stacked under labels are false positives from tall glyph boxes: mark
  `data-layout-allow-overlap` after confirming the visible gap in a snapshot. Mark intended overflow
  (`data-layout-allow-overflow`) for off-frame cursors and scrolled message wrappers.
- `duplicate_media_discovery_risk`: the same image source twice in one frame file. Use a different image, or a non-image
  element (gradient chip) for the second use. CSS `background:url()` is also counted.
- Measure element positions at build time with `pos(el)` (offsetLeft/Top chain). Sub-composition roots may be re-id'd, so the
  loop stops at `#root` or the top: harmless as long as ancestors sit at 0,0.
- Contrast: the checker enforces 3:1 on large text; placeholders/`small` need `#8A8A8A` or darker on near-white.

## Assembly / render
- `assemble-index.mjs` reads STORYBOARD.md; to check a subset (calibration) pass a scratch copy with only those frames,
  then re-assemble the real one.
- `hyperframes catalog --json` prints registry errors on stderr: use `2>/dev/null` before parsing.
- Full render: `--quality draft` (~15-90s) for iteration, `--quality high` for the deliverable.
- Screenshots of a local HTML sheet: headless Chrome `--screenshot --window-size` works; the in-app browser pane shows
  large `file://` pages as static snapshots (relative assets fail).
