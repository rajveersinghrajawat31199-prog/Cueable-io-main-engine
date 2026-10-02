# Remotion-idiom → HyperFrames mapping

The pipeline was originally written for Remotion (React `<Composition>` + `useCurrentFrame()`).
HyperFrames is an HTML/GSAP framework. The concepts port cleanly; the mechanics differ.

## Concept map

| Concept                        | Remotion                                          | HyperFrames                                                                     |
|--------------------------------|---------------------------------------------------|---------------------------------------------------------------------------------|
| Composition file               | `<Composition>` TSX component                     | `.html` file with `class="clip"` root and `data-*` timing                       |
| Time source                    | `useCurrentFrame()`                               | GSAP timeline paused, registered on `window.__timelines`                        |
| Progress per part              | `progress(frame, in, out)`                        | `tl.to(el, { … }, position)` — timeline position IS the progress                |
| A "score" of coordinates       | typed view of `score.json` in a `.ts` file        | a small `<script>` block or `<style>` `--var:` custom properties                |
| Frame-rate                     | `<Composition fps={60} …>`                        | `data-fps="60"` on the clip root                                                 |
| Duration                       | `durationInFrames`                                | `data-duration="25"` (seconds) on the clip root                                  |
| Interpolate                    | `interpolate(frame, [a,b], [x,y], { clamp: true })` | GSAP tween with the same in/out values on a paused timeline                    |
| Sequences (edit mode)          | `<Sequence from={} durationInFrames={}>`          | one HTML file per scene under `compositions/`, master `index.html` stitches     |
| Transitions between scenes     | `<TransitionSeries>` / custom                     | seam techniques from `/seam-craft` + `/cut-the-curve`                           |
| CLI: still                     | `npx remotion still …`                            | `npx hyperframes snapshot <file> --frame <n>`                                    |
| CLI: render                    | `npx remotion render …`                           | `npx hyperframes render <file>`                                                  |
| CLI: preview                   | Remotion Studio                                   | `npx hyperframes preview <project>` → the Studio at localhost:3002              |
| Validation before render       | `validatePlan(plan, vocab, brand)`                | `npx hyperframes lint <file>` + `npx hyperframes check <file>`                  |

## The two invariants still hold

Both survive the framework port:

1. **Progress, not frames, wherever a part can express itself in 0–1.** In HyperFrames
   this means: a scene's GSAP timeline reads its own duration from `data-duration`;
   internal tweens are laid on the timeline at proportional positions, not at absolute
   frame numbers. When the score changes a state's duration, only the master timeline
   moves; the scene's internal proportions survive.

2. **No coordinate in composition HTML that could have lived in the score.** Coordinates
   that the user might edit (an object's centre, a row's cell width, a metronome step)
   go into `score.json` and reach the composition as CSS custom properties or as inline
   `<script>const CFG = {…}</script>` populated from the score at build time — never as
   magic numbers scattered through the DOM.

## Two composition modes, HyperFrames flavour

### Edit mode → CompositionPlan-shaped `score.json`

Emit one scene HTML per beat. Register each scene's GSAP timeline on
`window.__timelines`. The master `index.html` is a straightforward stitch of scenes
with `data-transition="…"` attrs handled by the seam skills.

Existing HyperFrames "registry blocks" (from the `/hyperframes-registry` skill) are the
natural mapping for pattern-shaped beats — `stat-tiles`, `logo-outro`, `panel-mosaic`
etc. all have equivalents. Prefer a registry block whose behaviour matches; write
custom HTML only where none does.

### Continuity mode → full `score.json`

One master `index.html`. Every element that persists across states is authored in the
DOM once and never remounted. The GSAP timeline holds every animation, addressed by
score cues. Scene files still exist under `compositions/` — each is a "state view",
useful for testing that state in isolation via `npx hyperframes preview` — but at render
time, the master `index.html` is what plays. State views MUST agree with the master at
their state's frame range; disagreement is a lint failure (`hyperframes check` catches
divergent DOM structure across seams).

## Reference HyperFrames skills to pull

- `/hyperframes-core` — the composition contract (`class="clip"`, `data-*` attrs, GSAP
  timeline registration, framework-owned media playback).
- `/hyperframes-animation` — the runtime adapters. GSAP is the default; Lottie / Anime.js
  / TypeGPU / CSS are alternatives per scene.
- `/hyperframes-keyframes` — seek-safe keyframe authoring, plus the `hyperframes keyframes`
  diagnostic for verifying rendered motion.
- `/motion-doctrine` — the gateway motion law. Read before designing any seam.
- `/cut-the-curve`, `/seam-craft`, `/oversized-cursor` — technique catalogs for seams
  and scene transitions.
- `/hyperframes-cli` — the dev loop (`lint`, `check`, `snapshot`, `preview`, `render`).
- `/hyperframes-registry` — installable blocks; the "patterns" from Remotion-land live
  here as `hyperframes add <name>`-able components.
- `/media-use` — media OS (BGM, SFX, images, LUTs) for anything the score's `content`
  block references.

## What does NOT port

- **Remotion's `<Sequence>` timeline math.** HyperFrames scenes are separate HTML files;
  the master stitches them. Continuity films still use one master file, but the model
  is a paused GSAP timeline over one DOM, not nested `<Sequence>` children.
- **`BrandProvider` / `useBrand`.** Brand tokens (colours, type, easing names) become CSS
  custom properties on the composition root, populated from `brand-brief.json.tokens`
  and `creative-direction.json` at build time by `/hyperframes-build`.
- **`engine/timing.ts` `progress()`.** GSAP is the progress engine. Use it directly.
- **`engine/fonts.ts` auto-loading.** Fonts come in via `/media-use` and are declared in
  HTML `<link>` or `@font-face` blocks.
