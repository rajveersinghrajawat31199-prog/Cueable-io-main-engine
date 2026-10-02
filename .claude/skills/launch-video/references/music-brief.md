# Music brief: what to ask for and what to search

Give this to the user when they need to find a bed (they search a platform, send files, we measure with
`scripts/measure_music.py`). Say plainly: we cannot verify which track a named company uses; the reliable way to identify
one is Shazam on the video or the credit in its YouTube/Instagram description.

## Avoid these words (they return the "traditional" sound)
corporate, business, presentation, inspiring, motivational, cinematic, epic, event.

## Search terms, best first
1. upbeat minimal tech instrumental
2. modern product launch upbeat
3. plucky electronic pop instrumental
4. bright indie electronic no vocals
5. startup app promo upbeat
6. light tech house minimal
7. bouncy marimba electronic / playful pizzicato tech
8. fashion pop energetic upbeat funk promo  (worked well on the ShopOS benchmark)

## Filters
Genre electronic / pop-electronic; mood happy, bright, energetic; tempo ~110-128 BPM (or ~100-110 double-time); no vocals;
steady groove, no big drop; >= 60s.

## What "good" measures like (reference: an upbeat SaaS launch film)
pulse ~4.0-4.5 onsets/s; steadiness (std of 1s level) <= ~3 dB after the intro; brightness ~2.4-3.2 kHz; a quiet 10-15s
intro is a bonus (sits under the logo/claim).
