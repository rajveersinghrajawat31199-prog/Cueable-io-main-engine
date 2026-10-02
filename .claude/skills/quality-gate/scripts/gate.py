#!/usr/bin/env python3
"""The quality gate. Combines the machine axes with the agent's structured review rounds and returns one verdict for a tier.

  gate.py template --profile P              print a review-round JSON to fill in (axes, anchors, problem slots)
  gate.py evaluate --tier fast|standard|studio [--profile P] [--project .]

Files (per project, quality/): machine.json (machine_scores.py), review/round-N.json (the agent), review_log.md (written here),
timing.jsonl (stage_timer.py). Exit 0 = SHIP or PREVIEW, 1 = FIX.

Tiers change how much TASTE review must exist, never the machine floor (rubric/tiers.json). A tier that needs no review
returns PREVIEW: honest label that nobody has judged taste yet.
"""
import argparse, glob, json, os, sys, time
from qg_common import RUBRIC, load_json, load_profile

ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["template", "evaluate"])
ap.add_argument("--profile", default="default"); ap.add_argument("--tier", default="standard"); ap.add_argument("--project", default=".")
a = ap.parse_args()
AX = load_json(os.path.join(RUBRIC, "axes.json")); TIERS = load_json(os.path.join(RUBRIC, "tiers.json"))
project = os.path.abspath(a.project); Q = os.path.join(project, "quality")

if a.cmd == "template":
    VIS_T = dict(AX["vision"]); VIS_T.update(load_profile(a.profile).get("vision_extra", {}))
    print(json.dumps({
        "round": 1, "reviewer": "<model id>", "seconds_spent": None,
        "looked_at": ["hook.png", "phone.png", "contact.png", "strip-1.png", "strip-2.png", "strip-3.png"],
        "scores": {k: None for k in VIS_T},
        "problems": [{"axis": "<axis id>", "t": "<seconds or range>", "what": "<what is wrong, specific>", "fix": "<the edit>", "status": "open | fixed | accepted", "reason": "<required when accepted>"}],
        "fixed_from_previous": [], "unverified": ["audio and taste by ear"], "notes": ""}, indent=2))
    print("\n# axes:", file=sys.stderr)
    for k, v in VIS_T.items(): print(f"#  {k}: {v['question']}  anchors {v['anchors']}", file=sys.stderr)
    sys.exit(0)

T = TIERS[a.tier]; problems = []; lines = []
mach = load_json(os.path.join(Q, "machine.json"))
if not mach: sys.exit("no quality/machine.json: run machine_scores.py first")
VIS = dict(AX["vision"]); VIS.update(load_profile(mach["profile"]).get("vision_extra", {}))   # a format profile may add its own taste axes
lines.append(f"tier={a.tier} ({T['label']}: {T['note']})   profile={mach['profile']}   video={os.path.basename(mach['video'])} {mach['dur']} s")
lines.append("\nMACHINE AXES (deterministic)")
for k, v in mach["axes"].items():
    if v["score"] is None: lines.append(f"  {k:18} n/a    {v['note']}"); continue
    ok = v["score"] >= T["machine_min"]
    lines.append(f"  {k:18} {v['score']:4.1f}  {'PASS' if ok else 'FAIL'}   {v['value']} {v['unit']}  {v['note']}")
    if not ok: problems.append((v["score"], f"machine: {k} = {v['score']} ({v['value']} {v['unit']}); need >= {T['machine_min']}"))

rounds = sorted(glob.glob(os.path.join(Q, "review", "round-*.json")), key=lambda p: int(os.path.basename(p)[6:-5]))
R = [json.load(open(p)) for p in rounds]
need = T["vision_rounds"]
lines.append(f"\nVISION AXES (agent-scored from sheets)   rounds logged {len(R)}, tier needs {need}")
last = R[-1] if R else None
if need == 0:
    lines.append("  not required at this tier: taste is UNREVIEWED")
else:
    if len(R) < need: problems.append((0, f"review: {len(R)} round(s) logged, tier '{a.tier}' needs {need}"))
    for i, r in enumerate(R, 1):                                    # validate every round
        miss = [k for k in VIS if not isinstance(r.get("scores", {}).get(k), int) or not 1 <= r["scores"][k] <= 10]
        if miss: problems.append((0, f"round {i}: missing/invalid integer scores (1-10) for {', '.join(miss)}")); continue
        if not r.get("problems"): problems.append((0, f"round {i}: no problems listed (a review always names the biggest problems)"))
        if not r.get("reviewer") or str(r["reviewer"]).startswith("<"): problems.append((0, f"round {i}: reviewer model id not filled in"))
        for k, s in r["scores"].items():
            if s < T["vision_min"] and i == len(R) and not any(p.get("axis") == k for p in r.get("problems", [])):
                problems.append((s, f"round {i}: {k} scored {s} (< {T['vision_min']}) with no problem entry for it"))
    if last and not [1 for k in VIS if not isinstance(last.get("scores", {}).get(k), int)]:
        for k in VIS:
            s = last["scores"][k]; ok = s >= T["vision_min"]
            lines.append(f"  {k:18} {s:4d}  {'PASS' if ok else 'FAIL'}   {VIS[k]['title']}")
            if not ok: problems.append((s, f"vision: {k} = {s} (< {T['vision_min']}): " + "; ".join(p['what'] for p in last.get('problems', []) if p.get('axis') == k)))
        for p in last.get("problems", []):                               # every listed problem must be closed out
            st = p.get("status", "open")
            if st == "open": problems.append((5, f"open problem [{p.get('axis')}] @ {p.get('t')}: {p.get('what', '')[:110]}  -> {p.get('fix', '')[:80]}"))
            elif st == "accepted" and not p.get("reason"): problems.append((5, f"problem [{p.get('axis')}] is 'accepted' without a reason"))
            elif st not in ("fixed", "accepted"): problems.append((5, f"problem [{p.get('axis')}]: status must be open | fixed | accepted"))
        if len(R) >= 2 and T["vision_rounds"] >= 3 and not last.get("fixed_from_previous"): problems.append((0, "studio tier: the last round must list what it fixed from the previous round"))
        lines.append("  unverified by the reviewer: " + ", ".join(last.get("unverified", ["(none stated)"])))

# stage timing summary if present
tim = [json.loads(l) for l in open(os.path.join(Q, "timing.jsonl"))] if os.path.exists(os.path.join(Q, "timing.jsonl")) else []
if tim: lines.append(f"\nTIMING  {len(tim)} logged stage(s), {sum(t.get('seconds', 0) for t in tim):.0f} s total (stage_timer.py report for the table)")

worst = sorted(problems, key=lambda p: p[0])
if not problems: verdict = T["label"]
else: verdict = "FIX"
lines.append(f"\nVERDICT: {verdict}" + ("" if verdict != "PREVIEW" else "  (machine gates pass; taste not reviewed at this tier)"))
for _, p in worst: lines.append(f"  fix: {p}")
txt = "\n".join(lines); print(txt)

# review_log.md (regenerated each time)
if R:
    log = ["# Review log", f"_generated {time.strftime('%Y-%m-%d %H:%M')} by gate.py_\n"]
    for i, r in enumerate(R, 1):
        log.append(f"## Round {i}  ({r.get('reviewer')}, {r.get('seconds_spent', '?')} s)")
        log.append("scores: " + ", ".join(f"{k} {v}" for k, v in r.get("scores", {}).items()))
        for p in r.get("problems", []): log.append(f"- [{p.get('status', 'open')}] **{p.get('axis')}** @ {p.get('t')}: {p.get('what')}  -> _{p.get('fix')}_" + (f"  (accepted: {p['reason']})" if p.get("reason") else ""))
        if r.get("fixed_from_previous"): log.append("fixed since last round: " + "; ".join(r["fixed_from_previous"]))
        if r.get("unverified"): log.append("unverified: " + ", ".join(r["unverified"]))
        if r.get("notes"): log.append("notes: " + r["notes"])
        log.append("")
    open(os.path.join(Q, "review_log.md"), "w").write("\n".join(log))
sys.exit(1 if verdict == "FIX" else 0)
