# Ad grammar (universal): structure, hook types, formats, engines

## Structure (defaults, grade O: adjust per concept, but keep the order)
| Beat | 15 s | 30 s | Job |
|---|---|---|---|
| **Hook** | 0-2 | 0-2 | First real change by 1 s. Name the person/pain/number. Nothing decorative. |
| **Relevance / problem** | 2-5 | 2-8 | Make the viewer feel seen: the situation in their words. |
| **Proof / demo** | 5-11 | 8-22 | Show the product doing the thing (real UI), or the number, or the real customer. |
| **Proof 2 (optional)** | | 22-26 | One more concrete proof point. |
| **Ask** | 11-15 | 26-30 | One CTA that matches the offer, on screen at least 2 s, brand mark, then stop. |

## Hook types (validator counts distinct types; use at least 3 across a test set)
`pain-callout` ("RevOps: still stitching Monday's numbers by hand?") . `number` ("6 hours -> 40 minutes") . `contrarian` ("Your dashboard is not the problem.") . `demo-first` ("Weekly review, built in 10 seconds") . `question` . `before-after` . `customer-story` (ONLY with a real, sourced customer proof).

## Formats (from the Meta file l.113-121, graded O) and what builds them
| Format | Builds with | Notes |
|---|---|---|
| Product demo / UI in motion | `/ui-morph-loop` (silent-first loops) or `/launch-video` mechanics (rebuilt UI, one-take VO) | strongest fit for B2B SaaS; needs the customer's real UI |
| Motion / kinetic type (pain, number, contrarian) | `/motion-graphics`, `/general-video` | fastest to make; no product footage needed |
| Hype rapid-cut | `/general-video` | needs brand assets |
| Testimonial | `/talking-head-recut` | ONLY real customer footage with permission. Never synthesised. |
| UGC-style | not built | needs real people; we do not fake them |

## Pipeline (gates marked ◆)
0. **Brief** ◆: `ad-brief.json` from a performance agent (or the customer), `validate_brief.py` 0 FAIL. No brief on LinkedIn -> run the `linkedin-performance-marketer` agent first.
1. **Pick the engine per concept** (table above). One brand design system across all variants.
2. **State list on the timeline** ◆: seconds for hook / problem / proof / ask, the captions text, the CTA. Show it before building.
3. **Build** each variant natively per aspect. Captions burned in; primary text >= 48 px at 1080 wide.
4. **Sound** (optional, silent-first): light UI SFX only; music only if the customer approves a real track.
5. **Gate**: `/quality-gate` with `--profile ad-creative --tier <fast|standard|studio>`; fix until it returns PREVIEW/SHIP.
6. **Export** per platform: `export_for.py master.mp4 --platform linkedin --aspect 9:16` (paid: blends 60 -> 29.97, native size), or `--use organic` (keeps 60 fps), then it runs `check_export.py`.
7. **Pack**: exports + thumbnails + `variants.csv` + `results.csv` + `utm.txt` + the ad copy (intro text/headline within adapter limits).

## Not built yet (be honest with customers)
- A dedicated ad builder: hook caption layer, CTA end card, burned-in caption track as reusable engine parts. The first real ad builds will surface them; until then ads are assembled with existing skills.
- SRT caption export, real-people formats, results ingestion.
