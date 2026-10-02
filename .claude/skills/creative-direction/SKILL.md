---
name: creative-direction
description: "Stage 2 of the brand-brief-video pipeline. Reads brand-brief.json (never the raw sources) and pitches three ≤60-word directions, scores them, promotes one, and salvages the useful parts of the losing two. Also loads on triggers: 'pitch creative directions', 'concept the film', 'what film should this be', 'creative director'."
---

# Creative direction (Stage 2)

**Role:** `creativeDirector` · **Input:** `brand-brief.json` + AssetManifest ·
**Output:** `<project>/.pipeline/creative-direction.json` +
`<project>/.pipeline/direction-candidates.json` ·
**Budget:** ~12k in, ~2.5k out, ≤3 images looked at.

You have the brief. You do not have the website, and you do not need it. The whole point
of Stage 1 was to make Stage 2 answerable from the brief alone.

## Order of work

1. **Pitch three directions, ≤60 words each.** Candidates are *pitched*, not
   *specified*. Do not storyboard them. Write them like a director talking to a room:
   the idea, the mechanism, the feeling, one line each.
2. **Score them on stated criteria** — brand specificity, product truth, continuity,
   legibility, restraint, typographic role, pacing, endability, buildability,
   memorability. Give a number 1–5 per criterion and a one-line rationale. Scoring is
   how a losing idea dies quickly and honestly.
3. **Iterate the leader until it feels right**, at least one refinement loop with the user
   (tighten idea, mechanism, feeling). Keep three scored candidates; do not switch to five
   angles.
4. **Promote one.** Write it out in full as the `CreativeDirection` shape (see
   PIPELINE.md).
5. **Salvage before discarding.** The losers are rarely wrong whole. Hookflo's winner
   took its detection mechanism from the losing "Scan" and its persistent clock from
   the losing "Silent Night" — and those two borrowings are what made eight states read
   as one event. Record what you took in `salvaged`.
6. **Write the candidates file and forget it.** Nothing downstream reads
   `direction-candidates.json` — it exists for the audit trail and for the moment three
   weeks later when someone asks "why not the other one?"

## Choose the composition mode here, once

Read your promoted pitch and ask: **could these beats be reordered without breaking the
film?**

- **Yes → `mode: "edit"`.** The film is a sequence of shots with transitions.
  Downstream `score.json` will be `CompositionPlan`-shaped. Right for showreels,
  most product promos, launch teasers.
- **No → `mode: "continuity"`.** The film is one system evolving. Reordering breaks
  causality. Downstream `score.json` will be full-Score shape. Right when the concept is
  *one object being re-read* — a diagram unfolding, a dashboard populating, a mark
  finishing itself.

Write the choice into `creative-direction.json.mode`. Every later stage keys off it.

## What decides the winner

Brand specificity and continuity, in that order. A concept derived from something that
could belong to no other company beats a more beautiful mechanism that teaches the
viewer nothing about the product. If Direction A is 20% more polished but 40% less
specific, promote B.

## Fill these carefully

- `heroMotif` — one object or behaviour carries the film. Name it. If you cannot name
  it in six words, you have not chosen a direction, you have chosen a mood.
- `continuityRules` — what survives across state changes and how. If the answer is
  "nothing, it is a shot film", say so and leave the array empty. Do not invent
  continuity to look rigorous.
- `forbiddenBehaviours` — the hard constraints the critic will check. Copy in the
  `failureModes` from the brief that apply, and add the ones *this concept specifically
  invites*. This array does more work than any other field.
- `densityArc` — 0–1 per state. Deciding now that the failure is the film's densest
  frame and the detection its emptiest is what stops the storyboard drifting into
  evenness.

## Approval gate

When candidates and direction files exist:

1. Present all three candidate pitches (verbatim, ≤60 words each) with their aggregate
   scores.
2. Present the promoted direction: `heroMotif`, `mode`, `duration`, `spatialLogic`,
   `pacingArc`, `densityArc`, all of `forbiddenBehaviours`, all of `salvaged`.
3. Ask: **"Is this the film? If not, would a different candidate be closer?"**
4. Wait for an explicit yes. On "pick Candidate B instead", re-promote and re-write the
   direction file with B's material (salvaging from the other two). On "close, but…",
   amend the specific field and gate again.

## Done when

State names in `pacingArc` are the ones the storyboard and score will use (they are
the addressable identities across the pipeline — do not rename them later without
running the whole pipeline again). The file serialises under ~2,000 tokens. The user
has approved the direction.
