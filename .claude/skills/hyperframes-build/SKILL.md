---
name: hyperframes-build
description: "Stage 5 of the brand-brief-video pipeline. Adapted from the showreel motion-system's remotion-build skill for HyperFrames. Takes score.json + storyboard.json + creative-direction.json + brand-brief.json and emits one composition HTML per storyboard state (approved one at a time), then stitches them into a master index.html. Enforces the invariant that no frame number and no coordinate lives in composition HTML — all of them read from the score. Also loads on triggers: 'build the compositions', 'generate the scenes', 'implement the score', 'write the hyperframes html', 'ship the film'."
---

# HyperFrames build (Stage 5)

**Role:** `implementer` · **Input:** `score.json` + `storyboard.json` +
`creative-direction.json` + `brand-brief.json` + AssetManifest + retrieved HyperFrames
primitives · **Output:** `<project>/compositions/scene-NN-<state-id>.html` per state,
plus `<project>/index.html` (the master), plus
`<project>/.pipeline/render-state.json` · **Budget:** ~60k in, ~12k out per scene.

## Retrieve, do not dump

You may open the HyperFrames tree, but only by name. **Load these skills, in this
order:**

1. `/hyperframes-core` — the composition contract (`class="clip"`, `data-*` attrs,
   GSAP timeline registered on `window.__timelines`, framework-owned media playback,
   determinism rules).
2. `/motion-doctrine` — the gateway motion law. Every seam decision descends from it.
3. `/hyperframes-animation` — animation runtime adapters (GSAP default; Lottie /
   Anime.js / TypeGPU / CSS / WAAPI as alternatives).
4. `/hyperframes-keyframes` — seek-safe keyframe authoring per runtime.
5. `/seam-craft` + `/cut-the-curve` — the seam catalog for scene-to-scene transitions.
   Load only when you get to the master `index.html`.
6. `/hyperframes-registry` — for edit-mode plans, block/component installation.
7. `/media-use` — media resolution (BGM, SFX, images, LUTs) for anything the score's
   `content` references.
8. `/hyperframes-cli` — `lint`, `check`, `snapshot`, `preview`, `render`.

Never load `packages/core/**` or the registry wholesale, and never read another film's
`compositions/*.html` "for reference".

## Structure

For a project at `<project>/`, the file layout is:

```
<project>/
├── index.html                                 # master, stitches scenes
├── hyperframes.json                           # project config (fps, size, …)
├── compositions/
│   ├── scene-01-<state-id>.html               # one per storyboard state
│   ├── scene-02-<state-id>.html
│   └── …
├── assets/                                    # media (from /media-use)
├── .pipeline/                                 # the JSON artifacts
└── STORYBOARD.md                              # HyperFrames convention, human-readable
```

## Contract: every composition HTML

- Root element is `<div class="clip" data-fps="60" data-duration="<seconds>">` with
  `data-fps` and `data-duration` matching the score's values for this state (or the
  whole film, for the master).
- Every animation lives on a **single paused GSAP timeline** created at the top of the
  scene's inline `<script>` and registered as `window.__timelines.push(tl)`. That
  registration is how HyperFrames drives seek at render time — a scene that misses it
  will not render.
- The score reaches the composition two ways:
  - **CSS custom properties on the clip root** for numbers that CSS uses directly
    (widths, colours, durations expressed as `Xs`).
  - **An inline `<script>const S = {…};</script>`** near the top of the scene for
    numbers that JS reads. `S` is built by pasting the relevant slice of `score.json`
    at build time — one `JSON.parse(…)` moment, no computed values.
- **No magic numbers.** If a number appears in the HTML that is not a class name, a
  role or an attribute-value name, either it is bound from the score (correct) or it
  is an oversight (fix before the gate).
- No `Date.now()`, no unseeded `Math.random()`, no render-time network fetches — the
  render is deterministic (HyperFrames rule).
- `class="clip"` sits on the root. Every child that participates in the timeline is a
  named element or has a stable `data-hf-id`.

## Real UI at scene scale

Any scene that shows a product screen follows these rules. Screenshots are **reference
only**, never scene content.

- **Every UI element is real.** Same labels, layout, icons and states as the product. No
  invented buttons, no coloured squares standing in for icons.
- **Live DOM text, not a pasted screenshot.** Rebuild the screen in HTML/CSS. A scene built
  from a screenshot of a real app contains zero `<img>` of that screenshot.
- **Rebuild only the part the scene needs**, roughly 1.8x larger, on a clean background. A
  scene about one button shows that button and its immediate context, not the full app.
- **Legible at final size.** Minimum roughly 28px at 1080p for anything meant to be read.
- **Device frames:** layer the real UI behind a transparent device-frame PNG so the frame's
  real alpha shape masks the corners. Never fake screen corners with CSS radius.
- **Icons** come from `hyperframes-build/references/real-icons.md`, never redrawn.

## Real icons, catalog first, timing scale

- **Icons:** follow `references/real-icons.md`. No placeholder shapes for product icons.
- **Catalog first.** Before hand-building any named visual (transition, text effect, chart,
  mock UI), run `npx hyperframes catalog --query "<what the beat should do>"` and prefer
  `npx hyperframes add <block>`. Also check `scene-library/` for a reusable scene. Example
  launch-style scenes: `github.com/heygen-com/hyperframes-launches`.
- **Global timing scale.** Expose `S.timingScale` (default 1) and multiply every camera-move
  duration by it, so one number retimes all zooms and pans. Vocabulary and recipes:
  `../motion-doctrine/references/feel-notes.md`.
- **After a scene passes critique**, save it to `scene-library/<name>/` with its variables
  documented (logo ending, prompt box, phone mockup, stat count-up) so the next video can
  start from it.

## Precondition: approved stills

**Refuse to start building** unless `approvals.json` has a `storyboard-stills` entry, meaning
the user approved the rendered stills sheet from the storyboard stage. If it is missing, go
back to `/storyboard` step "Still-frame sheet".

## Order of work — ONE SCENE AT A TIME

**This is the per-asset approval loop the user asked for.** Do not batch.

For each state `s` in `storyboard.states`, in order:

1. **Write `compositions/scene-NN-<s.id>.html`.**
   - Bind CSS variables from `score.geometry.<object>` and `score.cues`.
   - Bind `S = {...score.geometry, ...score.cues, ...score.content}` inline.
   - Author the GSAP timeline referencing `S.*` and CSS vars only.
   - Fill in every element the storyboard's `entering` / `persists` list requires.
2. **Lint:** `npx hyperframes lint compositions/scene-NN-<s.id>.html`. Must pass.
   Common causes of failure (from the showreel notes):
   - `gsap_css_transform_conflict` — the element has both a CSS `transform: …` and a
     GSAP tween animating a transform component (x, y, scale, rotate). GSAP overwrites
     the full CSS transform. Fix: move the CSS transform onto the tween's `fromTo`
     start values.
   - Missing `class="clip"` on the root.
   - Timeline not registered on `window.__timelines`.
3. **Check:** `npx hyperframes check compositions/scene-NN-<s.id>.html`. Must pass —
   this runs the scene in headless Chrome and catches runtime errors, layout issues
   and WCAG contrast failures.
4. **Snapshot:** `npx hyperframes snapshot compositions/scene-NN-<s.id>.html` — writes
   PNGs of the state's key frames (start, densityArc peak, end) to
   `compositions/qa/<s.id>-*.png`.
5. **Present to the user:**
   - The scene file path.
   - The three PNG previews.
   - One line on what the scene does and what it inherits from the score.
   - The score cues and geometry keys the scene reads (so the user can verify the
     invariant held).
6. **Gate — wait for explicit yes.** On no:
   - "Motion feels wrong" → adjust the timeline's easing / positions; do not touch
     score cues (they were approved at Stage 4).
   - "Wrong element / composition" → this is a scene issue, adjust here.
   - "The number is wrong" → this is a *score* issue; go back to `/score`, amend, and
     re-enter this scene once the score is re-approved.
   - Record the finding, apply the fix, re-lint / re-check / re-snapshot, gate again.
7. Only after `yes`, append to `render-state.json.scenes[]` and move to the next state.

## The master `index.html`

Only after every scene is individually approved.

**Continuity mode**: the master IS the composition. All scenes were state views for
testing; at render time the master is a single HTML file whose GSAP timeline addresses
every state's cues by absolute score time. The state view files stay in
`compositions/` for future refinements.

**Edit mode**: the master is a small stitch — it declares the overall duration and
composes the scene files as clips, with the `data-transition="<name>"` attribute per
seam picked from `/seam-craft`. Every transition name must exist in the brand's
`brand.motion.transitions` list.

Before the master gate:

1. Read `/motion-doctrine` on the vector law (how you exit determines how you enter),
   the seam gate, and the ban on idle wobble.
2. Read `/cut-the-curve` on the five velocity-matched seams and pick per pair of
   scenes.
3. Run `npx hyperframes lint index.html`, `npx hyperframes check index.html`,
   `npx hyperframes snapshot index.html --grid 6x4` for a contact sheet.
4. Present the contact sheet and the seam list (which seam between which scenes and
   why).
5. Gate.

## Do not force the system

If the film is a continuity system, do not force it into edit mode. Both authored
reference films correctly used none of the CompositionPlan machinery. Custom glue is
expected — Hookflo's marker identity chain, two-leg orthogonal migration and
gutter-only route stroke could not have come from a registry block and should not be
pushed back into one.

## Then render

Once the critique has passed (Stage 6):

```bash
npx hyperframes render <project>/index.html --out out/<film>.mp4
```

Write `render-state.json` with:

- Artifact versions the build came from (SHA of each `.pipeline/*.json`).
- Per-scene lint/check/snapshot paths.
- The master's contact sheet path.
- The final MP4 path and duration.

Do not write prose about the build; the critic must not read implementation logs.

## Done when

Every scene is written, lints clean, checks clean, snapshots exist, and every scene is
approved individually in `approvals.json`. The master exists and is approved. The
final MP4 is on disk.
