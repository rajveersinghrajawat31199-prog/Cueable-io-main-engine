#!/usr/bin/env python3
"""Expand a validated brief into named variants + an empty results sheet, so every ad can be traced back to its concept when results come in.

Name:  <brand>-<persona>-<concept>-<length>s-v<n>     (lowercase slugs, <= 100 chars; use it as the ad name AND utm_content)
Files: variants.csv (name, persona, concept, angle, hook_type, hook_line, cta, length_s, proof_ids), results.csv (template rows), utm.txt (suggested URL params)

usage: make_variants.py brief.json [--out .] [--version 1] [--personas ops-director,...] [--per-persona-concepts 4]
Does NOT choose winners: with real results filled into results.csv the agent reads them with the AIDA diagnosis (references/aida-diagnosis.md).
"""
import argparse, csv, json, os, re, sys
ap = argparse.ArgumentParser(); ap.add_argument("brief"); ap.add_argument("--out", default="."); ap.add_argument("--version", type=int, default=1)
ap.add_argument("--personas"); a = ap.parse_args()
B = json.load(open(a.brief))
slug = lambda s: re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).lower())).strip("-")
pers = [p for p in B["personas"] if not a.personas or p["id"] in a.personas.split(",")]
rows = []
for p in pers:
    for c in B["concepts"]:
        for L in c["lengths_s"]:
            name = f"{slug(B['brand']['name'])}-{slug(p['id'])}-{slug(c['id'])}-{int(L)}s-v{a.version}"
            if len(name) > 100: sys.exit(f"name too long: {name}")
            rows.append({"name": name, "persona": p["id"], "concept": c["id"], "angle": c["angle"], "hook_type": c["hook"]["type"], "hook_line": c["hook"]["line"], "cta": c["cta"], "length_s": L, "proof_ids": "|".join(c.get("proof_ids", []))})
assert len({r["name"] for r in rows}) == len(rows), "duplicate variant names"
os.makedirs(a.out, exist_ok=True)
with open(os.path.join(a.out, "variants.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "results-template.csv")).read().strip().split(",")
with open(os.path.join(a.out, "results.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(tpl)
    for r in rows: w.writerow([r["name"], B["platform"]] + [""] * (len(tpl) - 2))
open(os.path.join(a.out, "utm.txt"), "w").write("Append to the destination URL (one per variant, utm_content = the variant name):\n?utm_source=" + B["platform"] + "&utm_medium=paid-social&utm_campaign=" + slug(B["brand"]["name"]) + "-" + slug(B["offer"]["type"]) + "&utm_content=<variant name>\n")
print(f"{len(rows)} variants -> {a.out}/variants.csv, results.csv, utm.txt")
for r in rows[:6]: print("  ", r["name"])
