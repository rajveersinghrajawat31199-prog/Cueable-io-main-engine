---
name: visual-critique
description: "Stage 6 of the brand-brief-video pipeline. The critic. Reads the rendered contact sheet against creative-direction.forbiddenBehaviours and score.continuity — nothing else. Proposes removals and simplifications, not additions. Also loads on triggers: 'critique this film', 'review the render', 'what's wrong with the video', 'final pass'."
---

# Visual critique (Stage 6)

**Role:** `critic` · **Input:** contact sheet + `creative-direction.json`
(`forbiddenBehaviours` only) + `score.json` (`continuity` only) + the relevant
storyboard states · **Output:** findings appended to
`<project>/.pipeline/render-state.json.critique` · **Budget:** ~12k in, ~2k out,
≤2 images looked at closely.

**You do not see** the composition HTML, the score cues, the brand brief in full, or
the website. You see what was rendered and what it promised to be. This isolation is
deliberate: it stops the critic from re-deriving the direction, and stops the fixer
from being tempted to answer a critique by rewriting the concept.

## Method

Go through `direction.forbiddenBehaviours` and `score.continuity` one at a time. Each
finding cites what it violates — `direction.forbiddenBehaviours[3]`,
`brief.visualRules.R4`, `score.continuity[2]`. A finding with no citation is taste;
taste findings are allowed but must say so (`"kind": "taste"` on the finding entry).

Then ask, per state: **is this state's stated purpose actually visible?**

## What experience says to look for

The refinement pass on Hookflo produced four findings and **all four were removals or
simplifications. Nothing was added.** That is the expected shape.

- **A gesture that reads as a generic effect.** Nine dots each flying its own diagonal
  looked like a particle system — precisely what the brand file forbids. Rebuilt as
  two orthogonal legs, it read as a grid unfolding into a list.
- **An element that stays past its job.** A reading head that parks after it has found
  the thing is a decoration.
- **Evidence dropped under layout pressure.** A failing row lost its status chip when
  the panel contracted, at exactly the moment the alert claimed the error code. The
  chip is the evidence; the timestamp is not.
- **The one sentence that is a claim rather than a demonstration.** Cut it. Every
  sentence in the film should be a name for something the film is *showing*.

## Real-UI checks (mandatory)

Fail the scene if any of these is true:

- A UI element on screen does not trace to a source ref (captured screenshot, `.capture/`
  asset, or supplied reference).
- UI text is raster (an `<img>` of a screenshot) rather than DOM text.
- A product icon is a placeholder shape rather than the real icon.
- Text meant to be read is illegible at the final render size (roughly under 28px at 1080p).

Findings from these checks cite `real-ui` and are `simplification`/`removal` fixes (replace
the raster with a rebuild of only the needed region).

## What not to do

- **Do not propose additions.** If a state is weak, the fix is usually removal. A film
  that gained three elements in critique is a film whose direction was not finished.
- **Do not re-open a decision the direction already made.** A symmetrical composition
  held for four states may be deliberate — check `spatialLogic` before flagging it.
- **Do not rewrite the concept.** You are checking a film against its brief, not
  pitching a different film. If the concept is wrong, that is a Stage 2 problem —
  return `critique.status = "concept-wrong"` and stop; the router will re-open the
  direction gate.

## Output

Append to `render-state.json.critique.findings[]`. Each finding:

```jsonc
{
  "state": "drop",
  "violates": "direction.forbiddenBehaviours[3]",   // or "score.continuity[2]", or "taste"
  "finding": "the meter reads as a generic particle system",
  "fix": "rebuild as two orthogonal legs, gutter-only stroke",
  "kind": "removal"                                 // "removal" | "simplification" | "addition" | "taste"
}
```

Set `critique.status` to:

- `passed` — no findings, or every finding is `"kind": "taste"` and the user chose to
  ignore them.
- `changes-requested` — one or more `removal` / `simplification` findings still need
  to be applied.
- `concept-wrong` — the film's concept as-built cannot satisfy the direction; the
  router should re-open Stage 2.

## Approval gate

For each finding (in order), present it to the user:

1. The state, the finding, the violation cited, the proposed fix.
2. Ask: **"Apply this fix?"**
3. On yes: the fixer applies it (reads the finding, opens the named scene file, applies
   the specific fix, re-lints, re-checks, re-snapshots that scene). Re-critique after
   all approved fixes are applied.
4. On no with a reason: append `{ "userDeferred": <reason> }` to the finding and
   continue.

## Done when

`critique.status === "passed"`, every finding names the state and the fix, and every
applied fix passed lint + check on the modified scene. The final render then proceeds.
