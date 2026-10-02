# Rebuilding the brand's own UI (the core of a launch video)

## Why this overrides the stock skills
The stock `/product-launch-video` says "use the real screenshot; don't rebuild the site in HTML", the storyboard recipe says
"never draw a vendor's UI in DOM", and the frame-worker says on-screen text must not repeat narration. Those rules are right
for a site *tour of a third party*. A launch video needs the brand's **own** product shown working, which a marketing-page
screenshot cannot do. So: rebuild, and say so in every frame's `ui:` block (workers never read BRIEF.md).

## What "rebuilt" means
- Cards, tables, chat, composers, chips, charts, sidebars: HTML/CSS/SVG in the brand's tokens (frame.md).
- Content images (ad creatives, product photos) appear **whole** inside built UI. Never cropped: fit each image to its own
  aspect (`height` fixed, `width:auto`, or `object-fit:contain` in a neutral slot).
- Icons: neutral shapes or gradient chips; never emoji, never hand-drawn third-party logos.
- The cursor: a real, oversized arrow (~76px at 1080p) with the tip anchored (21%,14%), press-compress to .84, ripple. It
  enters from off-frame, glides, presses, drifts aside, exits. It must cause a visible state change. (The registry
  `oversized-cursor` is a self-contained demo with its own target: reuse its mechanics, not the component.)
- Measure targets, don't guess: use `pos(el)` from lv_lib to place the cursor tip on the real element.

## Legibility floor at 1080p
UI text >= 22px. Chips/labels >= 22px. A number the viewer must read is a focal: >= 120px where the layout allows.
Caption line 40px. Anything smaller is decoration, never information. Contrast: text/placeholder >= 3:1 (placeholder
`#8A8A8A` on near-white passes; `#A1A1A1` fails).

## Layout consistency
- Specialist card shell: fixed geometry across the run, only contents swap. Numeric handoff in STORYBOARD.md.
- Persistent thread: chat column geometry fixed across frames; new messages fade in; scroll the message wrapper by
  measuring `offsetTop+offsetHeight` against the visible limit. Start the next frame in the previous frame's end state
  (scrolled, chips pressed, panel state).
- Empty states are motion: skeleton bars + a linear shimmer sweep (chained tweens, not `repeat`).

## Typing, counting, checking (seek-safe patterns)
- Typing: one span per char, `tl.set(opacity:1)` at its time; a per-char caret (`i` inside the span) toggled on/off. A single
  caret after the whole string is WRONG (it sits at the end of hidden text).
- Count-up: `tl.fromTo(el,{textContent:0},{textContent:N,snap:{textContent:1},...})`. For formatted values (Indian commas, currency) use stepped
  `tl.set(el,{textContent:"..."})` at times.
- Status flips: two chips stacked in a relative container, crossfade opacity.
- Checklists: circle + stroke-dashoffset tick, staggered.

## Truthfulness
Each figure is `[site]` (the brand's published claim/sample) or `[illustrative]`. State which in the storyboard; list the
illustrative ones in the final message.
