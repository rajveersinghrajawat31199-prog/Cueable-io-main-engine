---
name: score
description: "Stage 4 of the brand-brief-video pipeline. Turns the approved storyboard into score.json — the flat table of every timing, every coordinate, every content string the composition will read. INVARIANT: no frame number and no coordinate appears anywhere in the composition HTML; all of them live here. Also loads on triggers: 'score this film', 'lay out the timing', 'set the geometry', 'write the cue sheet', 'compose the plan'."
---

# Score (Stage 4)

**Role:** `scorer` · **Input:** `storyboard.json` + `creative-direction.json` ·
**Output:** `<project>/.pipeline/score.json` · **Budget:** ~12k in, ~3k out. Almost no
prose — this file is a table, not a document.

You are answering: **how does the visual system evolve through time?**

A Score is one of two composition modes:

- Use a **Plan** (edit mode, `mode: "edit"` in direction) when the film is an edit —
  ordered shots, transitions, beats that could be reordered or switched off. The output
  is `CompositionPlan`-shaped (see PIPELINE.md).
- Use a **Score** (continuity mode, `mode: "continuity"` in direction) when the film is
  one continuous system, where reordering the beats would destroy the causality. The
  output is full-Score-shaped.

The mode was chosen in `/creative-direction`. Do not switch it here.

## The invariant

**No frame number and no coordinate appears anywhere in the composition HTML or the
composition's inline JS.** All of them live here. This is what made Hookflo's whole
refinement pass touch cues and geometry without reading the render code, and it is what
lets a UI regenerate one cue later.

In HyperFrames practice: the composition HTML reads the score into CSS custom
properties on the clip root (`<div class="clip" style="--travel: 6s; --row-cell: 96px;
…">`) and via a small inline `<script>window.__score = {…};</script>` block populated
at build time. Anything in the HTML that is not a name, a role or a class was an
oversight.

## Contents (continuity mode)

- **`states`** — the storyboard's ids, in order, contiguous, starting at 0 and ending
  exactly at `duration`. Weight them by the storyboard's `weight`, then adjust for the
  holds the direction asks for. `duration` is in frames.
- **`cues`** — every animated moment, flat and addressable. A named number, or an array
  for a metronome. Suffix a duration with `Len`, a per-item interval with `Step`, an
  offset with `Delay`; the checker uses those suffixes to know what is a position and
  what is not. Naming these carefully is what makes the score readable at a glance
  three months later.
- **`geometry`** — every coordinate, nested by object, in `space` units. `space.w` and
  `space.h` are the design file's own artboard dimensions; the composition scales
  once at the root.
- **`content`** — the data tables the composition renders, so copy and timing are
  editable without touching code.
- **`continuity`** — restated from the direction, plus anything the arithmetic implies.
  The critic checks against this list.

## Contents (edit mode)

- `duration` in seconds.
- `story` — an ordered array of `{ beat, pattern, transition?, content }` entries. Each
  `pattern` is the name of a HyperFrames registry block (see `/hyperframes-registry`)
  whose behaviour matches the beat. The `content` table is the block's own contract.
- `transition` is either a name the brand supports or omitted (defaults to `cut`). The
  first beat's `transition` is always `cut`.
- Never repeat a pattern back to back. Alternate registers: type → media → layout →
  type.
- Energy curve: open medium/high, drop for detail, lift once for proof, land low.

## Two rules that came out of the films

- **Adopt the source's coordinate space and scale once at the root.** For a
  design-derived film, `space` is the design file's own artboard size — GROW+ is
  authored in 1240×698 and scaled once by `1920/1240`, so a rect in the code and a rect
  in the keyframe are literally the same number. It cost one `transform` and removed
  an entire class of error.
- **A cadence is an interval, not a stagger.** If things are emitted by a machine, give
  them a fixed step and break it deliberately where the story needs it. Hookflo's row
  metronome is 12 frames and misses exactly one beat; that gap is the failure and it
  carries more than any effect could.

## Approval gate

When `score.json` is written:

1. Present the score as three tables:
   - **Timeline**: `state | from(s) | to(s) | duration(s) | densityArc target | densityArc actual`
   - **Cues**: `name | value | suffix | interpretation` (a one-liner per cue)
   - **Geometry** (continuity mode only): `object.field | space-value | (px-value at 1920 space)`
2. Print the total duration in seconds and frames, side by side.
3. Present `continuity` list.
4. Ask: **"Does the timing feel right? Any state too long, too short, wrong shape?"**
5. On a "make X longer / shorter", adjust `states[X].to` and every subsequent state's
   boundaries. The total `duration` should not change unless the user says so. Gate again.

## Done when

- Continuity mode: `states` are contiguous and cover the duration; every cue is inside
  the film; `duration` matches the storyboard target within tolerance; every element
  in `direction.continuityRules` appears in `continuity`; user has approved.
- Edit mode: total duration of `story[].duration` (defaults included) equals top-level
  `duration`; every `pattern` exists in the brand's vocabulary or is a registry block;
  every `transition` is legal for the brand; user has approved.
