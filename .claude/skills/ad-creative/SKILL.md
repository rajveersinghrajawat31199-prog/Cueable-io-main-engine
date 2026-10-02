---
name: ad-creative
description: "Universal playbook for making a short AD video (any platform, any client): structure hook -> relevance -> proof -> one ask, silent-first captions, hook by 1 s, concrete sourced proof, 3-6 radically different variants, native aspect per format. Platform limits live in swappable ADAPTERS (platforms/linkedin.json, verified 2026-09-29) enforced by check_export.py / export_for.py; quality is judged by /quality-gate --profile ad-creative (hook speed, dead time, variety + hook relevance, proof, clear ask, works with sound off, one message). Use for any performance/paid-social/ad video request. The strategy (who, what angle, what to test) comes from a performance agent's ad brief, not from this skill."
---

# Ad creative (universal playbook)

**Scope.** How to MAKE an ad video correctly, whatever the platform. It is not platform strategy (that is a performance agent: `linkedin-performance-marketer`, Meta later) and it is not media buying. Platform differences are data files (adapters), so a B2C client or a platform we have not built yet still gets the same playbook.

## Non-negotiables
1. **Hook by 1 s.** First real change within 1 s; the first 2 s name a person, pain or number. (Hypothesis O, tested by the gate.)
2. **Silent-first.** The whole message survives with the audio off: burned-in captions/on-screen text, primary text >= 48 px at 1080 wide.
3. **One persona, one idea, one ask.** The ask matches the offer and stays readable about 2 s.
4. **Concrete proof, never invented.** Real UI, sourced numbers, real customers with permission. Illustrative figures are labelled and replaced before spend. No fabricated testimonials or people.
5. **A test set, not a single ad.** 3-6 radically different concepts (angle and hook type), named for traceability.
6. **Native per aspect, exported through the adapter.** Never crop one master into another aspect. Masters are 60 fps. A PAID LinkedIn export is automatically blended down to 29.97 fps (paid ads must be below 30); an organic export keeps 60.
7. **Gate before delivery; never promise results.** Say what the test can teach. Audio and taste are unverified by ear.

## Run it
```bash
# validate the brief the performance agent wrote, expand to named variants
python3 .claude/skills/performance-core/scripts/validate_brief.py brief.json
python3 .claude/skills/performance-core/scripts/make_variants.py brief.json --out videos/<p>/pack
# build (see references/ad-grammar.md), then judge:
bash .claude/skills/quality-gate/scripts/run_gate.sh videos/<p> renders/master.mp4 --profile ad-creative --tier standard
python3 .claude/skills/quality-gate/scripts/gate.py evaluate --tier standard --profile ad-creative --project videos/<p>
# deliver per platform (checks limits, makes the thumbnail):
python3 .claude/skills/ad-creative/scripts/export_for.py videos/<p>/renders/master.mp4 --platform linkedin --aspect 9:16 --out videos/<p>/exports   # PAID (default): 60 -> 29.97 fps by blending, native size
#   organic post instead:  ... --use organic   (keeps 60 fps)     explicit rate:  ... --fps 25
python3 .claude/skills/ad-creative/scripts/check_export.py <any.mp4> --platform linkedin
```

## Files
`platforms/<name>.json` adapters (LinkedIn verified; add Meta from its docs) · `scripts/check_export.py`, `export_for.py` · `references/rules.md` (every rule graded V/S/O/U/X with its source and who checks it) · `references/ad-grammar.md` (structure, hook types, formats, engine routing, pipeline) · quality profile `quality-gate/rubric/profiles/ad-creative.json`.

## Verified so far (2026-09-29)
- The gate profile scores an ad-style film and rejects a slow hook (see the quality-gate notes); the vision axes `hook_relevance`, `proof`, `cta_clear`, `sound_off`, `single_message` are new and have anchors.
- The LinkedIn adapter comes from LinkedIn's own help page. PAID ads must be below 30 fps (LinkedIn's paid spec; the owner's experience agrees) while ORGANIC video accepts 10-60 fps (LinkedIn's Pages spec, also fetched). `check_export.py --use paid` FAILs a 60 fps file, `--use organic` passes it; `export_for.py` makes the paid version by frame blending (tested: equals the average of the source pairs).
- **No ad video has been produced end to end yet.** The playbook, gate, adapter and brief tooling exist and are tested piecewise; the first real ad will test the chain.
