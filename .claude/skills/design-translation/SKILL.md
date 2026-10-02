---
name: design-translation
description: "Mode-B branch of the brand-brief-video pipeline. Use INSTEAD of brand-archaeology + creative-direction + storyboard when the user already has approved keyframes (a signed-off Figma / design file with the film's frames drawn). Takes the keyframes as an AssetManifest and produces storyboard.json + score.json directly. Also loads on triggers: 'translate this design', 'these keyframes are approved', 'design-to-motion', 'the design is signed off'."
---

# Design translation — Mode B (Stages 1–3 collapsed)

**Role:** `storyboarder` then `scorer` · **Input:** approved keyframes as an
AssetManifest · **Output:** `<project>/.pipeline/storyboard.json` +
`<project>/.pipeline/score.json`.

For films that start from approved design rather than from a brand. Reference case:
GROW+, six Paper keyframes, already signed off before the pipeline touched them.

**There is no archaeology and no direction generation.** The creative direction was
approved before the pipeline started. Do not re-derive a brand, do not score three
concepts, do not write a BrandBrief. The narrower and harder question is: *what happens
between frame 01 and frame 02 such that both remain true?*

## When to use this skill vs the full pipeline

| Situation                                              | Path                                                       |
|--------------------------------------------------------|------------------------------------------------------------|
| Brand exists, no film yet                              | Full pipeline (archaeology → direction → storyboard → …)   |
| Keyframes signed off, need to animate them             | **This skill**, then `/score` refinements, then build      |
| Brand exists AND some keyframes exist                  | Full pipeline — the keyframes are references, not the plan |
| A campaign palette / one-off look                      | Full pipeline — do NOT register a campaign as a brand      |

## Order of work

1. **Read the keyframes as a sequence, not as compositions.** GROW+'s six frames are
   one horizontal strip of landscape worked on six times: frame 02 contains frame 01's
   material, cut. Once that is seen, the film's rule writes itself — *reveal by
   removal* — and every downstream decision follows.
2. **Write each keyframe as a storyboard state**, with `persists` doing the real work:
   which object in frame 02 *is* an object from frame 01, rather than a new object that
   resembles it. That distinction is invisible in stills and is usually the piece's
   most careful decision. Number-of-remounts across the sequence is the honesty check.
3. **Infer continuity, then state it.** Anything the stills cannot prove goes in
   `score.continuity` so the implementation is answerable to it. If the design shows a
   number changing from 12 → 8 → 3 but doesn't show *how*, that is a continuity note
   for the score, not a decision the build stage should improvise.
4. **Adopt the design file's coordinate space.** `score.space` is the artboard, and the
   composition scales once at the root (a `transform: scale(--scale)` on the clip root
   with `--scale: calc(1920 / 1240)` or similar). A rect in the code and a rect in the
   keyframe are then the same number — the highest-leverage decision in the GROW+ build.
5. **Score it in seconds, convert once.** Edits are discussed in seconds and rendered
   in frames. `fps` is written once at the top of `score.json`; every human-facing
   number in the score is authored in seconds and multiplied through by `fps`
   consistently.

## Rules

- The keyframes are the approved design. **Do not improve them.** Where the render is
  arithmetically clean and a designer would want it ragged, note it as a limit rather
  than changing it. If you cannot resist a "small improvement", write it into
  `score.continuity` as a proposal and gate on it; do not silently apply it.
- **Do not register a campaign palette as a brand.** A look for one deck is not a
  reusable identity, and conflating the two corrupts the brand file. If a
  `brand-brief.json` is generated for this run, mark it `"scope": "one-off"`.
- **Expose no props.** Every number is a keyframe; props would imply they are choices.
  If the film is destined for HyperFrames, this maps to: no CSS custom property is
  authorable outside the score; the composition binds all of them from `score.json`.

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

The QA stills below satisfy the `storyboard-stills` precondition of `/hyperframes-build`:
record `{stage: "storyboard-stills"}` in `approvals.json` when the user approves them.

## Approval gate

When `storyboard.json` and `score.json` are both written:

1. Present one QA still per state — a rendered PNG or a frame reference — with the
   original keyframe alongside for comparison.
2. Present the `persists` map: for each state, list the objects that carry over from
   the previous state, and highlight any that could be read as a remount.
3. Ask, per state: **"Does the render match the approved design at this frame?"** A no
   on any state is a build issue, not a translation issue — return the answer and
   have `/hyperframes-build` re-work that scene.
4. Ask once: **"Are the continuity notes complete?"** These are the rules the build
   stage cannot infer from the stills.

## Done when

`node scripts/check-artifacts.mjs` (or the HyperFrames equivalent —
`npx hyperframes lint <project>`) passes, one QA still per keyframe matches the
approved design at the same coordinates, and the user has approved.
