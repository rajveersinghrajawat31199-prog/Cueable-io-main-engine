# Review protocol (one round)

You are a harsh motion director, not the proud author. One round = look, score, list problems, fix, re-run the machine axes.

1. Run `run_gate.sh` (machine axes + sheets). Read `quality/machine.json` first: any axis under the tier minimum is already a problem.
2. LOOK at the images in this order (true aspect, unlike the old critic sheets):
   - `hook.png` (first 2 s at 6 fps) -> `first_2s`. Is frame 1 already specific and moving? Is the value or action visible by 2 s?
   - `phone.png` (1 fps, 360 px wide) -> `phone_readability`. Anything you cannot read at a glance is a problem; note text under about 10 px tall AT THAT SIZE.
   - `contact.png` -> `composition`, `brand_accuracy`, `message_clarity`. Dead space, hierarchy, palette/type/copy belong to THIS brand, invented numbers labelled.
   - `strip-1..3.png` (12 consecutive frames around the 3 biggest moments) -> `motion_quality`. Overlaps, pops, sliding instead of easing, blur on text you must read, digits double-exposed, flat mid-tone passes.
   - `seam.png` for loops.
3. Pull EXACT frames (`ffmpeg -ss t -frames:v 1`) for anything suspicious. Sheets show that something is off, frames show what.
4. Score each vision axis 1-10 against the anchors in `rubric/axes.json`. Integers only.
5. Write `quality/review/round-N.json` (`gate.py template` prints it). Each problem: axis, timestamp, what is wrong (specific), the exact fix, status `open`.
6. Fix the source (never the render), re-render, `run_gate.sh`, then set fixed problems to `fixed`. New round if the tier needs another.
7. `gate.py evaluate --tier ...`. Report the verdict, the machine numbers, and what you could not verify.

Always hunt for: text overlapping during swaps, anything sliding instead of easing, corner labels and frame borders, centred-on-gradient shots, blurry scaled text, a dead beat, a stutter at the loop seam, ghosted digits under motion blur, tiny secondary text.

Prompt for the reviewing model (use verbatim): "Open the sheets and look at them properly. Be a harsh motion director, not a proud author. Score the axes 1-10. List the biggest problems with timestamps, each with the exact fix. Do not pad the list and do not praise. Say what you cannot judge."
