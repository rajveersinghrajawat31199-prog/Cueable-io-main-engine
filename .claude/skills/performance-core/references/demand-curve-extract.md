# Demand Curve extract (source: two markdown course exports supplied 2026-09-29)

Line numbers refer to the images-stripped text of each file. LinkedIn file = "LinkedIn Ads by Demand Curve.md" (650 lines, last third is an unrelated 2019 benchmarks blog post). Meta file = "Meta ads Demand Curce.md" (1,758 lines). Grades per `evidence-grades.md`.

## LinkedIn file
| Claim (paraphrased) | Line | Grade | Use |
|---|---|---|---|
| 75% of visits are on phones; site must be mobile-friendly | 7-9 | U | Prompt to verify; supports mobile-first checks |
| LinkedIn records only about 50% of conversions; send full UTMs, read results in your analytics tool | 21-31 | U (and dated) | Keep UTM discipline; do not quote the 50% |
| Target by job function + seniority, not title alone; titles cover ~40-50% of members | 47, 158-161 | O | Persona structure: function x seniority |
| One campaign per seniority level (manager/director/VP/C-level) | 50-51, 166 | O | Persona-specific creative variants |
| Audiences under ~50,000 fatigue fast | 152 | O | Note in test plan |
| Don't advertise signup; advertise gated content (guide, whitepaper, ebook, webinar) and follow up | 57-60 | O | Offer hypothesis to TEST against a demo CTA |
| Choose content niche so the only solution is your product | 59 | O | Angle rule |
| "No 20% text rule" like Facebook | 64 | X for us (Facebook rule is gone; LinkedIn's own policies not verified) | Do not use |
| Test challenger vs incumbent, duplicated in the same campaign, because LinkedIn favours ad longevity | 73-74 | O | `test_plan.structure` |
| Lead forms: lower cost per lead, worse down-funnel conversion | 86-89 | O | Offer/CTA trade-off |
| Ads saturate slowly; CTR falls after 28-33 days, change images | 108-111 | U/O | `refresh_after_days` default 30, tested not assumed |
| Face imagery works for tiny text ads; female faces best | 80 | U | Ignore |
| Budget, bid, exclusion and setup steps (Phases 1-8) | 113-323 | O, media-buying, dated | Launch checklist only, marked verify-current |
| 2019 marketing benchmarks (SEM, email, direct mail...) | 521-617 | X | Ignore (different author, 2019, not video) |

## Meta file (creative-relevant parts only)
| Claim | Line | Grade | Use |
|---|---|---|---|
| Creative has the most leverage on Meta and also steers targeting | 46, 450 | O | Why we test creative variety |
| First 3 seconds matter most; 15-30 s; captions ("85% watch without sound"); 4:5 or 1:1 feed, 9:16 stories/reels | 124-126 | O; the 85% is U | Hypotheses in ad-creative rules |
| Video types: testimonial, transformation, product demo, UGC-like, hype cut, motion ad; demo good for SaaS | 113-121 | O | Format menu |
| Meta works for B2B/SaaS too; lead ads for high-LTV | 29, 161-170 | O | Meta agent later |
| 3-6 ads per ad set; about 10,000 impressions per creative; radically different concepts | 1248-1256 | O | `test_plan` and validator |
| Do not judge on one session; relaunch; find what the algorithm likes NOW | 1256, 1368 | O | Test hygiene |
| AIDA metrics and creative fixes | 1310-1335 | O | `aida-diagnosis.md` |
| Name ads by their differentiated copy; keep a copy master sheet | 1155-1160 | O | Variant naming (we use structured names instead) |
| Captions; keep them clear of the Stories CTA button; thumbnail matters | 481, 516, 1188 | O | Sound-off + safe-zone rules |
| Job-title targeting no longer advised on Meta | 783 | O | Confirms platform split |
| "$5-$10 CAC" on Meta | 42 | U | Ignore |
| Targeting steps, budgets, CBO/ABO, bid settings, UI clicks | 196-1150 | O, media-buying, changes often | Launch checklist only, verify-current |
