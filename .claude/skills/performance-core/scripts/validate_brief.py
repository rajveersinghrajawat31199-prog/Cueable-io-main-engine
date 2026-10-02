#!/usr/bin/env python3
"""Validate an ad brief (templates/ad-brief.template.json shape). Enforces the rules that keep ads honest and testable:
  - required fields present; ids unique; references resolve
  - every proof item has a source or is labelled illustrative (no invented proof)
  - a 'testimonial' concept needs real customer proof with a source (no fabricated testimonials)
  - one persona per concept, one cta per concept, hook line present and short
  - test hygiene: 3-6 concepts per set, at least 3 DIFFERENT hook types and 3 different angles ("radically different", not tweaks)
  - lengths sane; total variant count under a cap
usage: validate_brief.py brief.json [--max-variants 12]        exit 1 on any FAIL
"""
import argparse, json, sys
ap = argparse.ArgumentParser(); ap.add_argument("brief"); ap.add_argument("--max-variants", type=int, default=12); a = ap.parse_args()
try: B = json.load(open(a.brief))
except Exception as e: sys.exit(f"cannot read brief: {e}")
fails = warns = 0
def say(l, m):
    global fails, warns; fails += l == "FAIL"; warns += l == "WARN"; print(f"{l:4}  {m}")
def need(obj, keys, where):
    for k in keys:
        v = obj.get(k) if isinstance(obj, dict) else None
        if v in (None, "", [], {}) or (isinstance(v, str) and v.startswith("<")): say("FAIL", f"{where}.{k} missing or still a placeholder"); return False
    return True
need(B, ["brand", "platform", "objective", "goal_metric", "offer", "proof", "personas", "concepts", "test_plan"], "brief")
br = B.get("brand", {}); need(br, ["name", "category", "tone"], "brand")
say("PASS" if br.get("assets_ready") else "WARN", "brand assets ready" if br.get("assets_ready") else "brand assets NOT confirmed ready (logo, fonts, real UI): the studio cannot rebuild the product UI without them")
need(B.get("offer", {}), ["type", "name", "why_this_offer"], "offer")
proof = {p.get("id"): p for p in B.get("proof", [])}
if len(proof) != len(B.get("proof", [])): say("FAIL", "proof ids are not unique")
for p in B.get("proof", []):
    ok = bool(p.get("illustrative")) or (p.get("source") and not str(p["source"]).startswith("<"))
    say("PASS" if ok else "FAIL", f"proof {p.get('id')}: " + ("labelled illustrative" if p.get("illustrative") else f"sourced ({p.get('source')})") if ok else f"proof {p.get('id')} has no source and is not labelled illustrative: never invent proof")
    if p.get("type") == "customer" and not p.get("source"): say("FAIL", f"proof {p.get('id')}: a customer claim needs a real source")
per = {p.get("id"): p for p in B.get("personas", [])}
if len(per) != len(B.get("personas", [])): say("FAIL", "persona ids are not unique")
for p in B.get("personas", []): need(p, ["id", "function", "seniority", "pain"], f"persona {p.get('id')}")
C = B.get("concepts", []); ids = [c.get("id") for c in C]
if len(set(ids)) != len(ids): say("FAIL", "concept ids are not unique")
say("PASS" if 3 <= len(C) <= 6 else "FAIL", f"{len(C)} concepts (want 3-6 per test set: too few teaches nothing, too many starves each of data)")
hooks = {c.get("hook", {}).get("type") for c in C}; angles = {c.get("angle") for c in C}
say("PASS" if len(hooks) >= 3 else "FAIL", f"{len(hooks)} distinct hook types (want >= 3: test radically different concepts, not tweaks)")
say("PASS" if len(angles) == len(C) else "FAIL", "every concept has its own angle" if len(angles) == len(C) else "two concepts share the same angle")
nv = 0
for c in C:
    w = f"concept {c.get('id')}"
    if not need(c, ["id", "angle", "format", "hook", "cta", "lengths_s"], w): continue
    line = c["hook"].get("line", "")
    say("PASS" if line and not line.startswith("<") and len(line.split()) <= 14 else "FAIL", f"{w}: hook line present and <= 14 words ({len(line.split())})")
    say("PASS" if isinstance(c["cta"], str) and c["cta"] and not c["cta"].startswith("<") else "FAIL", f"{w}: exactly one CTA string")
    for pid in c.get("proof_ids", []): 
        if pid not in proof: say("FAIL", f"{w}: proof_id {pid} does not exist")
    if not c.get("proof_ids"): say("WARN", f"{w}: no proof attached: the ad will be claims only")
    if c["format"] == "testimonial" and not any(proof.get(pid, {}).get("type") == "customer" and proof[pid].get("source") for pid in c.get("proof_ids", [])):
        say("FAIL", f"{w}: testimonial needs real customer proof with a source; testimonials are never fabricated")
    ls = c["lengths_s"]; say("PASS" if all(isinstance(x, (int, float)) and 3 <= x <= 90 for x in ls) else "FAIL", f"{w}: lengths {ls} within 3-90 s")
    nv += len(ls) * max(1, len(per))
say("PASS" if nv <= a.max_variants else "WARN", f"{nv} persona x concept x length combinations (cap {a.max_variants}: run the strongest personas first or cut lengths)" if nv > a.max_variants else f"{nv} variants (cap {a.max_variants})")
import os
adp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ad-creative", "platforms", str(B.get("platform")) + ".json")
use = B.get("deliver", {}).get("use", "paid")
say("PASS" if use in ("paid", "organic") else "FAIL", f"deliver.use = {use} (paid ads are exported at the platform's paid frame-rate limit; organic keeps 60 fps)")
if B.get("deliver", {}).get("aspects"):
    if os.path.exists(adp):
        sup = json.load(open(adp))["video"]["aspects"]
        for asp in B["deliver"]["aspects"]: say("PASS" if asp in sup else "FAIL", f"deliver aspect {asp} " + ("supported by the %s adapter" % B["platform"] if asp in sup else "NOT supported by the %s adapter (%s)" % (B["platform"], ", ".join(sup))))
    else: say("WARN", f"no adapter for platform '{B.get('platform')}': aspect support not checked")
else: say("WARN", "deliver.aspects not set: which native aspects will be authored?")
T = B.get("test_plan", {}); need(T, ["structure", "min_impressions_per_creative", "judge_after"], "test_plan")
say("PASS" if B.get("unverified") else "WARN", "unverified items listed" if B.get("unverified") else "no `unverified` list: every brief has claims/specs still to check; say so")
print(f"\nSUMMARY: {fails} FAIL, {warns} WARN"); sys.exit(1 if fails else 0)
