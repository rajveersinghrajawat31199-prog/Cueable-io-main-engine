---
name: storyboard
description: "Stage 3 of the brand-brief-video pipeline. Turns the approved creative-direction into a state list — one entry per pacingArc id — with a self-critique pass that catches 'frames that behave like a diagram rather than like the brand'. Also loads on triggers: 'storyboard this', 'what are the visual states', 'sketch the frames', 'plan the beats'."
---

# Storyboard (Stage 3)

**Role:** `storyboarder` · **Input:** `creative-direction.json` + `brand-brief.json` +
AssetManifest (selected refs only) · **Output:**
`<project>/.pipeline/storyboard.json` · **Budget:** ~16k in, ~4k out, ≤6 images.

You are answering: **what are the important visual states?**

States, not shots. A continuity film's states are readings of one persistent object;
only a film that genuinely cuts sets `cut: true`.

## Order of work

1. **One state per entry in the direction's `pacingArc`, with the same ids.** The
   pipeline checks this; a mismatch is a failed run. If a state does not fit that
   structure, the direction was wrong — go back one stage rather than papering over it
   in the storyboard.
2. For each state write `visual` at frame scale — what a designer would say out loud
   about the frame. No pixel values; the Score owns those. If you write a number, it
   is a *ratio* ("row cell is roughly one-tenth of the frame width"), not a coordinate.
3. Fill `persists` / `entering` / `leaving` honestly. This is where continuity is
   either real or decorative. An element in `entering` in one state and `entering`
   again two states later is a remount, and a remount is a cut. If the direction chose
   `mode: "continuity"` and your storyboard has three remounts, something is wrong at
   the direction level — surface it, do not silently break the concept.
4. Write the copy verbatim. Copy invented later is copy nobody critiqued.

## Then critique your own storyboard, as static design

**This pass is not optional and it is the cheapest quality in the pipeline.** Render
the states at full size (design mockups are fine — even ASCII if that is all you have)
and look at them as design, not as a plan. Hookflo's rev 1 produced seven findings, all
of them the same finding: *the frames had the brand's colours and type but were
behaving like a diagram rather than like the brand.* Look for exactly that.

The three findings that recurred and are worth checking first:

- **Bare text where the brand pairs a thing with its mark.** Source names without their
  monograms read as an abstract diagram of a log rather than a log. This was the
  single largest gain in the whole project.
- **A brand device you left out.** A missing mono label above the panel was a direct
  violation of the brand's own rule and left the top sixth of every frame empty — and
  it was also the film's only way to speak without narrating.
- **A void nobody placed.** Unplaced emptiness is the difference between asymmetry and
  imbalance. Give the empty quadrant a job or close it up.

Also check, per state: *is the state's central claim visible in a still?* Hookflo's
DROP beat says *the system does not know yet*, and that was invisible until a running
counter was added.

Record every finding in `critique` with its fix, then apply the fixes. Later stages
read the fixed states; the critique array is there so nobody re-derives it.

## Still-frame sheet (before any animation)

After the state list is approved, build **one static HTML frame per state** in
`<project>/stills/` (real UI rules above apply here, so wrong UI is caught before motion
work), render them with `npx hyperframes snapshot` into a single contact-sheet grid, and
present it. Ask: **"Are these the frames?"** Only on an explicit yes, record
`{stage: "storyboard-stills"}` in `approvals.json`. `/hyperframes-build` will not start
without that entry.

## Rules

- Cite refs by id. Do not re-describe screenshots.
- Check each state against `direction.densityArc` and `direction.forbiddenBehaviours`
  before you write it down. A state whose density does not match its densityArc entry
  is either a wrong storyboard entry or a wrong densityArc entry — decide which.

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

## Approval gate

When storyboard.json is written and the critique fixes are applied:

1. Present a table with columns: `id | beat | visual (one line) | persists | copy`.
2. Present the critique findings and, per finding, whether it was applied.
3. Ask: **"Are these the beats, in this order? Any missing state? Any state that isn't
   earning its place?"**
4. Wait for explicit yes. On no, either add/remove a state (which requires re-running
   `/creative-direction` to re-fit the `pacingArc`), or amend a state's `visual` /
   `persists` in place. Gate again.

## Done when

Every state has been through the critique pass, every state id matches a
`direction.pacingArc` entry, no state violates a `direction.forbiddenBehaviours` entry,
and the user has approved. This is the last stage where restructuring is cheap; after
this, changes cost scene files.
