# Story grammar for a launch video: a MENU of moves, not a template

Pick and order per brand. A reference video tells you which moves work; it never tells you the content, layout or copy.
Sizes are for a 45-75s film at 1920x1080. Aim: one idea per frame, ~3-6s per UI frame, value claim by beat 2.

## Moves (each = one frame or a short run)
| Move | Job | Notes that mattered |
|---|---|---|
| **Claim** | Say the promise in outcome language | Logo unit + one line. Hook speaks the viewer's outcome, not features. One emphasised word may take a secondary italic face with a thin gradient underline (see design-system.md). |
| **Scope / overwhelm** | Show how much a brand needs done | Cards drift in on the words that name each group; end on a busy held field + caption. Real sample names/numbers from the brand. |
| **One action** | The single thing the user does | e.g. drop a URL, click a button, scan, then the card morphs into the app home. Cursor really clicks; every click changes state. |
| **Specialist run** | Introduce N capabilities | ONE card shell (same position/size/header), contents swap. One verb-led caption line in a fixed slot. Skeleton slots (one per capability) fill the pause under the intro line. |
| **Connect / stack** | "Works with what you use" | Official logos via `/media-use`; tiles cascade; one "synced" chip. A breather beat. |
| **One conversation (thread)** | The heart: the whole workflow as one persistent surface | Same chat column position across 2-3 cuts (numeric handoff in the storyboard); messages accrue and the thread scrolls like a real chat. Plan -> draft/approve -> live/results. |
| **Proof / results** | Make the outcome readable | Few large numbers (>=120px focal), counting up. Brand's own published stat if it has one. |
| **Callback + close** | Land the brand + one action | Words from the run swap by hard cut, logo assembles (star/mark blooms, colour travels, settles on the exact supplied gradient), CTA pill takes the click. Hold ~1.4s. |

## Rules
- **Value before evidence.** Delete every evidence frame: the claim must still be stated. Delete the claim: it must not still "work".
- **Voice-over is discrete cues**, one phrase per reveal. Write each frame's VO as short phrases so the frame can pace to them.
- **The pause under a talking VO is never empty**: skeleton tiles, a typing caret, or a slow state change. No screen static > ~0.7s.
- **Silent tails are for UI action** (typing, approving, results). Spliced silence gives them room; cap tails ~2s and fill with SFX.
- **The storyboard is a proposal**: open with "This video tells <audience> that <message>", a frame table (beat, on screen, why), then ask approve / sketches-first.
- **Data world**: one fictional customer, recurring numbers, plausible names. Label every figure `[site]` (brand's own) or `[illustrative]`.
- **Copy**: never lift another video's lines (a reference's copy is theirs). Write for this brand's category.
- **Length follows the voice.** Never pad to a requested duration.

## Choosing frames for a URL-only brief
Read the brand's visible text + asset descriptions for: hero use case, 3-4 pillars, one published number, one real sample
(chat prompt, table rows, job names). Those become the frames' content. If the site has no product UI, use the fallback
ladder in SKILL.md.
