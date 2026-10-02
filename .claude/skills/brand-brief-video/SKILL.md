---
name: brand-brief-video
description: "ROUTER / entry point — from a brand brief to a finished HyperFrames video, one approval gate at a time. Load when the user has a brand brief (product details, brand guidelines, assets, references) and wants to make a video with them without stitching skills together by hand. Runs the seven-stage pipeline (brand-archaeology → creative-direction → storyboard → score → hyperframes-build → visual-critique, plus design-translation as a Mode-B branch when approved keyframes already exist) and STOPS after each stage to show the artifact and wait for your explicit go-ahead before spending on the next one. After the storyboard is approved, generates each scene one at a time and stops for approval per scene. Also triggers on: 'I have a brand brief', 'make a video for this brand', 'from brief to video', 'run the pipeline', 'brand-driven video'."
---

# Brand-brief → video (Router)

You are the orchestrator. You do not do the work of any stage yourself — you route to the
seven skills below and enforce the approval gates between them. **Never advance a stage
without an explicit yes from the user.** Silence is not consent, and "looks fine" is not
"go".

## Pipeline

```
                              ┌── design-translation (Mode B, if approved keyframes)
brand sources                 │
     ↓                        ↓
brand-archaeology  →  creative-direction  →  storyboard  →  score  →  hyperframes-build  →  visual-critique
     │ approve         │ approve            │ approve      │ approve   │ approve per scene  │ approve fixes
     ↓                 ↓                    ↓              ↓           ↓                    ↓
brand-brief.json  creative-direction.json  storyboard.json  score.json  compositions/*.html  render-state.json
```

**Two composition modes** (chosen once, at the direction stage):

- **Edit** — ordered shots with transitions. Beats can be reordered or muted. Use the CompositionPlan model. Right for showreels, launch clips, most product promos.
- **Continuity** — one system evolving over time. Reordering the beats would break the causality. Score-driven. Right when the film is *one object* being re-read (Hookflo's missing dot; a diagram unfolding).

Choose by asking: *could these beats be reordered without breaking the film?* Yes → edit. No → continuity.

## Order of work

### 0 — Interview for the brief (before any skill runs)

Ask the user for, in one message:

1. **The product / brand.** One paragraph. What does it do, who for.
2. **Brand assets.** Site URL (it will be captured with `npx hyperframes capture`), logo files, existing brand guidelines PDF, screenshots, whatever exists. Say "none" honestly rather than making them up.
3. **Reference material.** Films / motion pieces the brand has already shipped, or ones that feel right in adjacent brands. Not "make it like Apple" — make it like *this specific 30-second piece*.
4. **Duration and format.** 15s / 30s / 60s; 16:9 / 9:16 / 1:1.
5. **Where the film will run.** Site hero / paid social / conference open / internal all-hands. This changes the tone more than the length does.
6. **The one thing a viewer should get**, plus **source material** (docs, PR, launch post).
7. **Screenshots of the real product** (reference for rebuilding UI, never pasted into scenes)
   and a **reference video** if one exists.
8. **Non-negotiables.** Things that must be in the film (a specific stat, a logo lockup, a legal line, a launch date) and things that must not (competitor names, unreleased features, a colour that clashes with the parent brand).

Write these back as a compact brief-of-the-brief. **Wait for the user to confirm.** Then start the pipeline.

### 1 — Load and run `/brand-archaeology`

Input: raw sources. Output: `brand-brief.json`. When a URL is given, archaeology first runs
`npx hyperframes capture` into `<project>/.capture/` and reads that as its source set.

**Gate:** present the brief as a compact summary (identitySummary, productTruth, markLogic,
top 3 visualRules, all failureModes). Ask: *does this recognise your brand?* Do not
paste 2,000 tokens of JSON at the user — that is a report, not a decision. Wait for yes.

### 2 — Load and run `/creative-direction`

Input: `brand-brief.json`. Output: `creative-direction.json` + `direction-candidates.json`.

**Gate:** show all three candidate pitches (≤60 words each) with their scores, then the
promoted direction with heroMotif, densityArc, forbiddenBehaviours. The user may pick a
different candidate; if so, re-promote and re-write the direction file. Wait for yes.

**Branch decision:** if the user already has approved keyframes (an existing design file,
signed-off frames) rather than a brand to derive from, skip archaeology and direction and
load `/design-translation` instead. That skill takes the keyframes as input and produces
`storyboard.json` + `score.json` directly.

### 3 — Load and run `/storyboard`

Input: `creative-direction.json` + `brand-brief.json`. Output: `storyboard.json`.

The storyboard skill runs its own self-critique pass before it hands back — do not skip
that pass to save a turn. The critique catches "frames that behave like a diagram
rather than like the brand", and it is the cheapest quality gain in the pipeline.

**Gate:** show the state list (id, beat/purpose, one-line visual, persists/entering/
leaving), the critique findings, and the fixes applied. Ask: *is this the film?* Wait for
yes. Then the storyboard builds one static frame per state and shows a **rendered stills
grid** (`npx hyperframes snapshot`); a second yes is recorded as `storyboard-stills` in
`approvals.json`, and `/hyperframes-build` refuses to start without it. This is the last stage where restructuring is cheap; after this, changes cost scenes.

### 4 — Load and run `/score`

Input: `storyboard.json` + `creative-direction.json`. Output: `score.json`.

**Gate:** show the total duration, state boundaries, the top-level cue table, and the
continuity list. If the pipeline is in *edit* mode, this stage produces a
`CompositionPlan`-shaped JSON instead of a full score — timings per beat, transitions,
content bindings. Wait for yes.

### 5 — Load and run `/hyperframes-build` — ONE SCENE AT A TIME

Input: `score.json` + `storyboard.json` + `creative-direction.json` + `brand-brief.json`.
Output: one `compositions/scene-NN-<state-id>.html` per state, plus the master
`index.html` that stitches them.

**This is the per-asset approval loop the user asked for.**

For each state in `storyboard.states`, in order:

1. Build `compositions/scene-NN-<state-id>.html`.
2. Run `npx hyperframes lint <file>` — must pass.
3. Run `npx hyperframes check <file>` — must pass (runtime, layout, contrast).
4. Run `npx hyperframes snapshot <file>` — capture keyframes as PNGs.
5. Present: the scene file path, the PNG previews, one line on what the scene does and
   what it inherits from the score.
6. **Gate — wait for yes on this scene.** Then move to the next state.

Only after every scene is individually approved, assemble the master `index.html`. Show
the assembled index in the Studio (`npx hyperframes preview .`) and gate again.

Before hand-building any named visual, run `npx hyperframes catalog --query "<beat>"` and
prefer `npx hyperframes add <block>`; after a scene passes critique, save it to
`scene-library/<name>/`. Reference launch scenes: `github.com/heygen-com/hyperframes-launches`.
Steering phrases (push in, pan, hard cut, global speed) are in
`/motion-doctrine/references/feel-notes.md`.

Load `/seam-craft` and `/cut-the-curve` before writing the seams between scenes — the
seams are what makes the film feel like one continuous camera move instead of a slide
deck. Load `/motion-doctrine` first if you have not already; every seam-level decision
descends from it.

### 6 — Load and run `/visual-critique`

Input: the rendered contact sheet + `creative-direction.forbiddenBehaviours` +
`score.continuity`. Output: findings appended to `render-state.json`.

The critique proposes **removals and simplifications, not additions**. That is the
expected shape. The four Hookflo findings were all cuts.

**Gate:** show the findings. For each, ask *apply?* If yes, run the fixer. Re-critique
until `critique.status === "passed"`.

### 7 — Final render

Once the critique has passed, run `npx hyperframes render` for the final MP4 / WebM.
Report the output path, the duration, and where the artifacts live.

## Artifact layout

For a project at `<project>/`, the pipeline writes:

```
<project>/
├── .pipeline/
│   ├── brand-brief.json
│   ├── creative-direction.json
│   ├── direction-candidates.json
│   ├── storyboard.json
│   ├── score.json
│   ├── render-state.json
│   └── approvals.json          # one entry per gate: {stage, at, note}
├── compositions/
│   ├── scene-01-<state-id>.html
│   └── ...
└── index.html                  # master composition
```

Record every approval in `approvals.json` as `{stage, at, note}`. If a stage is re-run
after an amendment, append a new entry rather than overwriting — the trail is what makes
"we changed our mind about beat 4" traceable.

## Rules

- **Never advance without an explicit yes.** "Looks good" is a yes; anything vaguer is
  not. When in doubt, ask again.
- **JSON before prose.** The artifacts are what every next stage reads, not chat history.
- **Retrieve, do not dump.** Load `/motion-doctrine` and the technique skills only where
  you actually need them; do not paste them into every turn.
- **Do not skip the storyboard's self-critique.** It is the cheapest quality gate in the
  pipeline and the most common shortcut.
- **Every scene is approved individually before the next is built.** Do not batch scenes
  to save turns. The whole point of this pipeline is that a bad decision at scene 3 does
  not propagate to scenes 4–10.
- **Do not re-derive an earlier stage from the website.** The brief exists so nothing
  reads the raw sources after archaeology.

## Supporting references

- `references/SYSTEM_PRINCIPLES.md` — universal principles every stage assumes.
- `references/PIPELINE.md` — full artifact contracts (JSON shapes) and gate protocol.
- `references/HYPERFRAMES-MAPPING.md` — how Remotion-idiom concepts (progress functions,
  score-owned time, per-part `t: 0-1`) map onto HyperFrames HTML + GSAP timelines.

## Done when

The final render exists on disk, `render-state.critique.status === "passed"`, every stage
has at least one approved entry in `approvals.json`, and the user has confirmed the
final film. Anything less is a paused run, not a finished one.
