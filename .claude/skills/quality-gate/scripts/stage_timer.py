#!/usr/bin/env python3
"""Per-stage wall-clock + (optional) token/cost log, so 'minutes' is a measured number.

  stage_timer.py run   --stage render-final [--tag preview|final] -- <command...>     time a command, keep its exit code
  stage_timer.py start --stage authoring [--tag authoring]     /   stop --stage authoring [--model M --tokens-in N --tokens-out N --note ...]
  stage_timer.py mark  --stage X --seconds S [--model M --tokens-in N --tokens-out N]  log a stage you timed elsewhere
  stage_timer.py report [--project .]                                                 table, time to first preview, total, cost

Log: <project>/quality/timing.jsonl. Tokens come from whoever calls the model (the SaaS backend's API usage fields, or the
agent). Nothing here can see them: no tokens logged = no cost line, never a guess. Prices: prices.json, generated from the pricing sheet by
job-receipt/scripts/pricing_from_sheet.py (do not edit by hand). Input + output tokens only: for cache-aware dollars per job use job_receipt.py.
"""
import argparse, json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "start", "stop", "mark", "report"])
ap.add_argument("--project", default="."); ap.add_argument("--stage"); ap.add_argument("--tag", default="")
ap.add_argument("--seconds", type=float); ap.add_argument("--model"); ap.add_argument("--tokens-in", type=int); ap.add_argument("--tokens-out", type=int); ap.add_argument("--note", default="")
argv = sys.argv[1:]
rest = argv[argv.index("--") + 1:] if "--" in argv else []
a = ap.parse_args(argv[:argv.index("--")] if "--" in argv else argv)
Q = os.path.join(os.path.abspath(a.project), "quality"); os.makedirs(Q, exist_ok=True)
LOG, OPEN = os.path.join(Q, "timing.jsonl"), os.path.join(Q, ".open-stages.json")
def log(rec): open(LOG, "a").write(json.dumps(rec) + "\n")
def base(): return {"stage": a.stage, "tag": a.tag, "model": a.model, "tokens_in": a.tokens_in, "tokens_out": a.tokens_out, "note": a.note}

if a.cmd == "run":
    cmd = rest
    if not cmd: sys.exit("give the command after --")
    t0 = time.time(); r = subprocess.run(cmd)
    log(dict(base(), start=t0, end=time.time(), seconds=round(time.time() - t0, 2), exit=r.returncode))
    print(f"[stage {a.stage}] {time.time() - t0:.1f} s exit {r.returncode}", file=sys.stderr); sys.exit(r.returncode)
if a.cmd == "start":
    o = json.load(open(OPEN)) if os.path.exists(OPEN) else {}; o[a.stage] = time.time(); json.dump(o, open(OPEN, "w")); print(f"started {a.stage}")
if a.cmd == "stop":
    o = json.load(open(OPEN)) if os.path.exists(OPEN) else {}; t0 = o.pop(a.stage, None)
    if t0 is None: sys.exit(f"stage {a.stage} was not started")
    json.dump(o, open(OPEN, "w")); log(dict(base(), start=t0, end=time.time(), seconds=round(time.time() - t0, 2))); print(f"{a.stage}: {time.time() - t0:.1f} s")
if a.cmd == "mark":
    now = time.time(); log(dict(base(), start=now - (a.seconds or 0), end=now, seconds=a.seconds)); print("logged")
if a.cmd == "report":
    rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
    if not rows: sys.exit("no timing log yet")
    prices = json.load(open(os.path.join(HERE, "prices.json"))); tot = 0.0; cost = 0.0; unpriced = False
    print(f"{'stage':22} {'tag':10} {'seconds':>9}  model / tokens")
    for r in rows:
        tot += r.get("seconds") or 0; extra = ""
        if r.get("model"):
            extra = r["model"]
            if r.get("tokens_in") is not None and r.get("tokens_out") is not None:
                p = prices.get(r["model"]) or {}
                if p.get("in") is None: unpriced = True; extra += f"  {r['tokens_in']}/{r['tokens_out']} tok (no price for this model)"
                else: c = (r["tokens_in"] * p["in"] + r["tokens_out"] * p["out"]) / 1e6; cost += c; extra += f"  {r['tokens_in']}/{r['tokens_out']} tok = ${c:.2f}"
        print(f"{r['stage']:22} {r.get('tag', ''):10} {r.get('seconds') or 0:9.1f}  {extra}")
    print(f"\ntotal logged stage time: {tot:.0f} s ({tot / 60:.1f} min)")
    acc = 0.0
    for r in rows:
        acc += r.get("seconds") or 0
        if r.get("tag") == "preview": print(f"time to first preview: {acc:.0f} s ({acc / 60:.1f} min): sum of the logged stages up to and including it. A LOWER BOUND: authoring, waiting and human time count only if logged as stages."); break
    print(f"model cost logged: ${cost:.2f}" + ("  (some stages have no price: incomplete)" if unpriced else "") if cost or unpriced else "model cost: not logged (no tokens recorded)")
