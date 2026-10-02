# LinkedIn launch and read-results checklist

**Status: grade O and DATED.** Distilled from Demand Curve's LinkedIn file (Phases 1-8, l.113-323). LinkedIn's Campaign Manager UI and options change often: verify every item in the account before advising it, and never present this as a fact-checked procedure. It exists so a customer who launches our test pack has a sane starting point. Our deliverable is the creative, not media buying.

## Before launch
- Admin on the ad account AND the company page (needed for Direct Sponsored Content, which does not publish to the public page).
- LinkedIn conversion tracking installed; down-funnel conversion (email captured -> qualified) tracked in the customer's own analytics, because platform-reported conversions may under-count (the source says about half: grade U).
- Landing page is mobile-friendly and continues the ad's message (same promise, same visuals), not the homepage.
- UTMs on every ad: `utm_source=linkedin&utm_medium=paid-social&utm_campaign=<brand>-<offer>&utm_content=<variant name>` (the name from `make_variants.py`).
- Audience of roughly 50,000+ people per campaign (source says smaller audiences fatigue), one campaign per seniority level.
- Consider turning off audience expansion and the LinkedIn Audience Network for the TEST so results stay attributable (source's advice, O; the Audience Network is a real placement in LinkedIn's spec page).
- Exclude existing customers, your own company, and recent site visitors.

## Structure of the test
- Challenger vs incumbent: put the new creative beside the current one in the same campaign (duplicate), because the platform favours older ads (O).
- 3-6 radically different concepts; about 10,000 impressions per creative before judging (O); more than one run.
- Set a total budget cap as well as a daily one to avoid runaway spend (O; the source's formula is acceptable CAC x 3 / 7 for a first week).

## Read results
- Review at day 1, 4 and 7 (source), then weekly.
- Use the customer's analytics tool as the source of truth for conversions, not only Campaign Manager.
- Diagnose with `performance-core/references/aida-diagnosis.md`; one creative change per weak stage, as `-v2`.
- Refresh creative around 4 weeks (source: CTR falls after 28-33 days, grade U/O): test it, do not assume it.
