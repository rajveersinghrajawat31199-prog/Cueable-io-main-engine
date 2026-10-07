---
name: hairline-figures
description: Use when a demo or launch video wants a 3D-looking object (isometric line drawing) that reacts to a cursor: a keyboard whose keys sink, a laptop lid that opens, a terrain that rises, a vault, a router, a cabinet. 27 ready figures (@lucasmarkes/hairline, MIT) driven frame-exactly by a scripted pointer path. Also routes a request for a NEW custom figure to /hairline-create.
---

# Hairline figures in videos

What they are: **SVG isometric line drawings** (not WebGL / not true 3D) on a 400x320 canvas, drawn in one thin stroke. Each answers a pointer with a spring/tween motion. Upstream is made for websites; we vendored it and added `tools/hairline/src/driver.js` so a *scripted* pointer drives it on a virtual 60 fps clock. Seeking to any time (forward, back, jump) gives the identical drawing: verified bit-exact on all 27 figures, then rendered through HyperFrames 0.8.34.

Use them as: hero object in a launch/demo, "what the product does" metaphors, empty-state / security / devices / infra beats, B-roll between UI scenes. Not for: photoreal product shots, anything needing colour fills or text inside the drawing (figures contain no text by design).

## Automatic use (the engine decides; the user does not run anything)

Called from `/studio-intake` (step 2b) and `/launch-video` (stages 3, 6-7). The user only sees the result in the storyboard and can veto it at the existing storyboard gate.

1. **Pick** (seconds, no cost): `python3 tools/hairline/hairline_scene.py pick "<message + proof points + tagline + category>"`. Score >= 4 means a real fit (vault 10-12 for a security brief); no output means NO figure: never force one.
2. **Decide** (all must hold): a score >= 4 hit; the story has a slot for an object beat (opening hook behind the type, a metaphor between two UI frames, a proof-point section break, the end card); the brand tone is precise/technical/calm (thin isometric line art does not suit a playful, photographic or hand-drawn identity: check `frame.md`); the film is a launch/demo/brand film. Budget: 0-2 figures per 60 s, 3-5 s each, one per beat; figures + orbs (`/thinking-orbs`) combined never exceed 2 decorative objects per 60 s. A figure never replaces the rebuilt product UI.
3. **Build** (one call per beat, installs the bundle, recolours, scripts the gesture, writes the cursor path):
   `python3 tools/hairline/hairline_scene.py make --project videos/<p> --figure <name> --start <s> --dur <s> --box x,y,width --plate <canvas hex from frame.md> --hi <ink or accent hex> [--at-cursor]`
   Tones (edge/mid/lo) are derived from plate + hi automatically. Box width >= 700 px at 1080p (height = 0.8 x width, must stay inside the frame). Paste the fragment from `assets/hairline/<id>.html` into the beat's composition, load `assets/hairline.bundle.js` in the head after GSAP, and call `window.__HL.bind(tl, TOTAL)` ONCE, last.
4. **Cursor**: if the story is "the user does this" (UI-driven demo) pass `--at-cursor` and feed `<id>.json -> cursor_px` to `/oversized-cursor`; for pure metaphor beats leave the cursor out.
5. **Gate** (before the critic): `python3 tools/hairline/check_figures.py renders/<x>.mp4 videos/<p>` must print only PASS (FAILs: off-frame, nothing drawn, never moves).
6. Record in BRIEF.md `figures:` (name, beat, why) and in STORYBOARD.md on that frame (`ui: hairline <name>, <what the pointer does>`) because frame workers never read BRIEF.md.

Slow-burn figures (subtle motion, give them 4-5 s): `vault` (dial mark turns; bolts only withdraw after 40 clicks), `phosphor` (a few dots), `padlock` (single shackle swing).

## Manual install (only when working by hand)

```sh
tools/hairline/add_to_project.sh videos/<project>        # copies assets/hairline.bundle.js (186 kB, offline, no CDN); hairline_scene.py make does this for you
```
Full working composition: `tools/hairline/example/index.html` (3 figures, dark theme, 6 s, lint clean, draft render 5 s).

## Use

```html
<script src="assets/hairline.bundle.js"></script>   <!-- after GSAP, before your script -->
<div id="f1" class="clip" data-start="0" data-duration="6"></div>   <!-- size it in CSS: 5:4 box, e.g. 800x640 -->
<script>
  const tl = gsap.timeline({ paused: true });
  const H = Hairline.scene();
  H.add("#f1", "laptop", {
    theme: "dark", intensity: 0.7,
    at: 0,                                   // offset the whole path on the timeline (s)
    path: [ {t:1.2,x:.5,y:.9}, {t:2.6,x:.5,y:.15}, {t:4,x:.5,y:.6}, {t:5.2,leave:true} ]
  });
  H.bind(tl, 6);                             // MUST be called last on the timeline; 6 = total seconds
  window.__timelines = { "<composition-id>": tl };
</script>
```
- `path` = pointer keyframes in seconds; `x,y` are 0..1 of the figure box; eased (smoothstep) between keys; `leave:true` takes the pointer off (figure returns to rest). Before the first key the figure is at rest.
- Several figures in one scene share one clock; give each its own path. Add all with `H.add` BEFORE `H.bind`.
- `intensity` 0..1 (default .5) is the per-figure strength (spread, travel, lid angle...). `theme` "light"|"dark". `label` is the a11y name.
- Colour/stroke: set CSS vars on the figure or an ancestor: `--hairline-plate` (bg), `-hi` (lit strokes), `-edge`, `-mid`, `-lo`, `--hairline-stroke` (px). **For 1080p video raise the stroke** (try `--hairline-stroke: 2` to `3`) or the lines look too faint; keep the box large (>= 700 px wide). Match brand: plate = scene background, hi = brand accent or white.
- A visible cursor is NOT drawn. If the story needs one, add it with `/oversized-cursor` and use the same path numbers (cursor px = box origin + x*width, y*height) so it lines up.

## Which figure for which point (pointer behaviour -> what to script)

| Shelf | Figure | Pointer does | Script it as |
| --- | --- | --- | --- |
| Interfaces | exploded | app window in 4 layers; move across opens the gap, down picks a layer | sweep right, then down |
| Data | terrain | 81 pillars rise around the pointer | slow diagonal drift |
| Data | phosphor | 7x7 dot matrix loop; pointer paints fading trail | short strokes, leave |
| Data | riffle | tray of 8 cards, hovered card stands up (arrow-keys unsupported here) | hop across the tray |
| Machines | slow | crates on a belt; hover slows the clock | enter and hold |
| Machines | turntable | blocks on a turntable; a flick spins it, settles on a quarter turn | fast swipe |
| Machines | elevator | 4 floors; pointer height picks the floor, car travels | vertical moves |
| Devices | keyboard | key under pointer sinks, neighbours follow | drag along the keys |
| Devices | phone | layers glass/board/battery/shell | like exploded |
| Devices | laptop | pointer height = lid angle, spring | y .9 -> .15 -> .6 |
| Coding | terminal | height scrolls history, line lifts | vertical sweep |
| Coding | cabinet | rack of 12 blades pulled out by height | vertical sweep |
| Coding | branches | commit graph; hovered commit and history rise | move along the graph |
| Security | vault | circling the dial turns it, bolts withdraw at 40 | circle the centre, several loops |
| Security | lockers | locker under pointer opens, previous shuts | step across |
| Security | padlock | shackle springs open as pointer nears | approach, then leave |
| Connectivity | patch | cable under pointer lifts, neighbours lean | drag along ports |
| Connectivity | dish | pointer aims the gimbal dish | slow arcs |
| Connectivity | router | antennas lean toward the pointer | move left/right |
| Empty states | loupe | loupe dragged across ruled sheet | drag |
| Empty states | sieve | height picks a sieve, rises clear | vertical |
| Empty states | rail | pointer brushes hangers, they rock | sweep across |
| Empty states | plug | pointer draws plug toward socket | move toward socket |
| Empty states | query | question mark hook turns, dot ball rolls | circle nearby |
| Empty states | drawer | height picks a drawer, slides out | vertical |
| Empty states | basket | tilts toward pointer, handle swings late | side to side |
| Empty states | plot | empty bar chart; pointer brushes tabs | sweep across |

"Made with the skill" (Vercel, Mastra, Notion marks) exist on the site as tribute pieces; they are third-party marks, not in the package, and must not be used in a client film.

## Rules and limits (all verified unless marked)

- Render path verified: HyperFrames 0.8.34 `lint` clean, draft render of 6 s / 1080p = 5 s. The Hairline loop is driven only by the driver; GSAP and the runtime never see the virtual clock.
- Deterministic seek verified across 27 figures x 12 scrub orders (mask ids are auto-numbered and ignored in comparison; they are invisible).
- The upstream 260 ms CSS stroke/fill fade is disabled (not seekable). Highlight changes are therefore instant; this is the only visual difference from the website.
- Fragments live in `assets/hairline/` (NOT `compositions/`: the linter treats every file there as a composition). A literal closing script tag inside a JS comment breaks the page and lint does not catch it: the generator avoids it, keep it that way. `riffle` only reacts inside a narrow band (x .3-.7, y .3-.5); its preset stays in it.
- Do not call `Hairline.scene()` twice on one page; one scene per composition. Sub-compositions: one scene in the sub-composition that owns the figures.
- Fixed 5:4 aspect (400x320 viewBox); do not stretch. For 9:16, place the figure in a 5:4 box and compose around it.
- Not verified: Studio timeline scrubbing UI (logic is the same seek path), 4K render time, nested sub-composition mounting, and audio/taste (no ear or design review done).
- `prefers-reduced-motion` makes some figures static; the render browser does not set it.

## A figure that does not exist yet

Run `/hairline-create <idea>` (vendored from upstream; `.claude/skills/hairline-create/`). It builds one standalone `hairline-<name>.html` (own kernel, slider, theme toggle) and validates it against 10 style rules. That standalone file is NOT wired to our driver: using one in a film needs the figure code ported onto the package engine (not done, not tested). For a one-off, screen-record is not acceptable (non-deterministic); ask first.

## Refresh

`npm view @lucasmarkes/hairline version`, then re-copy `dist/index.js` + `index.d.ts` into `tools/hairline/lib/` and rebuild per `tools/hairline/README.md`; re-run `tools/hairline/test/catalog.html` and the determinism check before trusting it.
