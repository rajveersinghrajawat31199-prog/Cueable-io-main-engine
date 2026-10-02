# System principles

Universal. Every skill in the brand-brief-video pipeline assumes these and none of them
repeats them. Ported from the `showreel` motion-system with light HyperFrames additions.

## Craft

1. **Brand specificity over generic polish.** A film that could carry any other logo has
   failed, however well made. Ask of every gesture: could this belong to anyone else?
   If yes, it is a default, not a decision.
2. **Motion must have a reason.** Every movement answers "what is this telling the
   viewer?" Decoration is the failure mode, not the goal.
3. **Constraints are part of the identity.** What a brand refuses to do is as
   descriptive as what it does. A `never` list is not a challenge.
4. **Prefer evidence to claims.** Show the product doing the thing. A sentence
   asserting a benefit is the most advertising-shaped object available; cut it.
5. **Preserve continuity when the concept requires it.** If a film's idea is one object
   being re-read, it is mounted once and its properties animate. Unmounting and
   re-creating something that looks the same is a different film.
6. **Stillness is a beat.** Holds are where a piece can be read. Budget them.
7. **One thing asks for attention at a time.**

## Structure

8. **Primitives support art direction; they do not determine it.** Reach for a
   HyperFrames block or component (or a registry item, or GSAP primitive) when it fits.
   Do not bend the concept to reach one.
9. **Custom creative glue is allowed and expected.** Real films are 20-80% custom to
   reused, and both ends are legitimate.
10. **Promote to shared only after it proves reusable.** Something becomes a reusable
    HyperFrames block/component after it has appeared independently in two films.
11. **Progress, not frames.** Where a part can, it takes `t: 0–1`. The composition owns
    time; the parts own shape. In HyperFrames this maps to GSAP timeline progress and
    `data-*` timing.
12. **No coordinate lives in composition HTML that could have lived in the score.**
    Numbers whose value the user might edit later go in `score.json`, and the composition
    reads them via CSS variables / data attributes / a small config block. This is what
    makes a refinement pass cheap.

## Cost

13. **Read once, summarise once.** An expensive raw source (a website capture, a PDF, a
    Figma export) is converted into a compact artifact exactly one time. Every downstream
    stage reads the artifact instead.
14. **Artifacts are memory.** Trust the artifact upstream produced. Do not re-derive its
    reasoning to check it — critique the *output*, not the reasoning that made it.
15. **Retrieve, don't dump.** Locate the module you need. Never load a folder of
    primitives or another film's implementation "for reference".
16. **JSON before prose.** Anything another stage will read is structured and short.
    Long-form markdown is for humans, written at the end.

## Approval

17. **No stage advances without an explicit user yes.** This overrides everything above
    when the two conflict. A pipeline that ran fast but skipped a gate did not save
    anything; it produced a film the user did not order.
18. **The approval trail is an artifact too.** `approvals.json` in `.pipeline/` records
    every gate the user opened, and every rework of a gated stage appends rather than
    overwrites.
