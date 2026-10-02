# Ad-creative rules (platform-free), each with its evidence grade

Grades: V verified in the platform's own docs, S cited study / unfetched official summary, O practitioner opinion (hypothesis), U unsourced, X stale. See `performance-core/references/evidence-grades.md`. **How checked** = who enforces it: `machine` (quality-gate ad-creative profile), `vision` (review round axis), `export` (check_export.py + adapter), `brief` (validate_brief.py), `house` (our studio rule).

## Structure and timing
| # | Rule | Grade | Source | How checked |
|---|---|---|---|---|
| AC-01 | The first real change starts within 1 s (a morph, cut or big move, not an idle pulse); hook score 8 at <= 1.0 s | O | our hypothesis, informed by Demand Curve "first 3 seconds" (Meta file l.124) and LinkedIn "establish your point in the first 5 seconds" (V, adapter). Stricter than both on purpose; test it. | machine `hook` |
| AC-02 | The first 2 s must name a person, pain or number (not a logo or generic product shot) | O | Demand Curve hook advice (l.1345) + B2B logic | vision `hook_relevance` |
| AC-03 | No still stretch longer than about 1 s; a new event about every 2-3 s | O | our studio rules + Meta "keep attention" | machine `dead_time`, `variety` |
| AC-04 | One idea, one persona, one ask per ad | O | Demand Curve (l.451-470); test hygiene | vision `single_message`, brief |
| AC-05 | The ask is explicit, singular, readable for at least about 2 s, and matches the offer | V (LinkedIn: "feature a clear CTA") + O for the 2 s | LinkedIn best practices | vision `cta_clear` |
| AC-06 | Proof is concrete (real UI moment, sourced number, real named customer); no invented proof; illustrative numbers labelled and replaced before spend | house | studio rule | vision `proof`, brief validator |
| AC-07 | Length: master 15-30 s; cut-downs 6-10 s and 15 s from the same master | V for 15-30 s "qualify for all placements" (LinkedIn); O for cut-downs | adapter | export (WARN outside range) |
| AC-08 | Short videos complete more often: LinkedIn data reports 7-15 s with up to a 300% lift in completion; for demand generation longer performed equivalently | V (LinkedIn's own statistic, 2025) | adapter guidance | informs cut-down set only |

## Sound-off and legibility
| # | Rule | Grade | Source | How checked |
|---|---|---|---|---|
| AC-10 | The whole message is carried without audio: burn in captions/on-screen text | V (LinkedIn: "think like a silent film director", "consider burning in subtitles") | adapter | vision `sound_off` |
| AC-11 | "85% watch without sound" / "80% of LinkedIn videos are watched without sound" | U | Meta file l.126; third-party blogs | never quoted to customers |
| AC-12 | Primary text at least 48 px tall on a 1080-wide canvas (readable at 360 px wide) | house | studio phone-readability rule | vision `phone_readability` |
| AC-13 | Keep captions and CTAs clear of platform UI areas; default to the middle 80% of the frame and away from the bottom 15% | O | Meta file l.516 (Stories CTA overlap); LinkedIn safe zones NOT stated (adapter `not_stated`) | vision `sound_off` |
| AC-14 | Third-party "minimum 24pt / 32pt captions" | U | blogs | ignore; use AC-12 |

## Variants and testing
| # | Rule | Grade | Source | How checked |
|---|---|---|---|---|
| AC-20 | Ship a test set, not a single ad: 3-6 concepts that are radically different (angle AND hook type), not tweaks | O | Meta file l.1248-1254 | brief validator |
| AC-21 | About 10,000 impressions per creative before judging; never judge on one run | O | Meta file l.1250, 1256, 1368 | test_plan |
| AC-22 | Every variant has a traceable name (`brand-persona-concept-length-vN`) reused as the ad name and `utm_content` | house | performance-core | make_variants.py |
| AC-23 | Refresh creative around 4 weeks: CTR reported to fall after 28-33 days on LinkedIn | U/O | LinkedIn file l.111 | test_plan `refresh_after_days`, tested not assumed |

## Delivery
| # | Rule | Grade | Source | How checked |
|---|---|---|---|---|
| AC-30 | Author or render each aspect natively (9:16, 1:1, 4:5, 16:9); never crop a master into another aspect | house | studio | export_for.py refuses mismatched masters |
| AC-31 | Export through the platform adapter: mp4, H.264, within size/duration/resolution limits; thumbnail JPG/PNG <= 2 MB. **Frame rate, PAID ads: below 30 (LinkedIn spec), so the paid export is converted from the 60 fps master to 29.97 by frame blending. Organic posts: 10-60 fps, keep 60.** | V (LinkedIn's paid-ads spec page and its organic video page, both read 2026-09-29) + confirmed by the studio owner's paid-ad experience | adapter | `check_export.py` (`--use paid` FAILs at 30+ fps; `--use organic` accepts 10-60) |
| AC-32 | Ad copy within platform limits (LinkedIn: intro text 150 recommended / 3,000 max; headline 70 / 200) | V | adapter | agent + brief |
| AC-33 | Do not promise results to a customer; say what the test can teach | house | performance-core | agent rule |

**Frame rate policy (studio owner's decision, 2026-09-29, then refined):** masters are 60 fps by default, for everything. A PAID LinkedIn ad must be below 30 fps (verified: LinkedIn's video-ads spec; owner's experience agrees), so a paid export is made from the master with `export_for.py` (default `--use paid`): it converts to 29.97 fps automatically, by BLENDING frames (averaging the source frames in each output frame) instead of dropping them, because dropping every other frame would halve the motion-blur shutter (180 deg at 60 fps becomes about 90 deg at 30). Organic LinkedIn video accepts 10-60 fps (verified: LinkedIn's Pages video spec), so `--use organic` keeps the master's rate. Verified on the demo: the blended export equals the average of the source frame pairs (mean difference 0.02 vs 0.19 for dropping; 0.02 vs 2.87 at the fastest motion). Frames are never invented (a master already under the limit is left alone; asking for a higher rate fails). 29.97 instead of 30 satisfies both LinkedIn's "less than 30" and the owner's "30 or less". Rendering the master at the delivery rate (`render_blur.sh --fps 30 --sub 8`, same cost) is an alternative, not the default. The master itself is never lowered.
