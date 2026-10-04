#!/usr/bin/env python3
"""Turn the pricing sheet (markdown) into pricing.json + the legacy quality-gate prices.json, and check it is self-consistent.

  pricing_from_sheet.py [SHEET.md] [--live-checked "2026-10-04 ..."]

Source of truth = pricing/claude-model-pricing-sheet.md (Anthropic's published API rates, USD per million tokens). To update prices: replace
that file with a newer sheet and re-run this script. It refuses nothing but PRINTS a warning for every row whose cache / batch / fast multipliers
do not match the documented rules (cache write 5m = 1.25x input, 1h = 2x, cache read = 0.1x [0.05x Opus 5.5, 0.025x Fable/Mythos 5.1], batch = 0.5x, fast = 2x).
"""
import datetime as dt, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument("sheet", nargs="?", default=os.path.join(SKILL, "pricing", "claude-model-pricing-sheet.md"))
_ap.add_argument("--live-checked", default=None)
_a = _ap.parse_args()
sheet, live = _a.sheet, _a.live_checked
text = open(sheet).read()


def money(s):
    m = re.search(r"\$([\d.]+)", s)
    return float(m.group(1)) if m else None


def api_id(name):
    n = name.lower().replace("claude ", "claude-").replace(" ", "-").replace(".", "-")
    return re.sub(r"\*", "", n)


def expand(cell):
    """'**Claude Sonnet 4.6 / 4.5 / 4**' -> ['Claude Sonnet 4.6','Claude Sonnet 4.5','Claude Sonnet 4']"""
    cell = re.sub(r"[*]", "", cell).strip()
    parts = [p.strip() for p in cell.split(" / ")]
    first = parts[0]
    fam = " ".join(first.split()[:-1])
    out = [first]
    for p in parts[1:]:
        if re.match(r"^[\d.]+$", p):
            out.append("%s %s" % (fam, p))
        elif p.lower().startswith("claude"):
            out.append(p)
        else:
            out.append("Claude " + p)
    return out


def tables(section_re):
    m = re.search(section_re, text, re.S)
    return m.group(0) if m else ""


models = {}
legacy_names = set()
lg = re.search(r"### Legacy.*?(?=\n\*\*Note on cache|\n## )", text, re.S)
if lg:
    for row in re.findall(r"^\|\s*(Claude[^|]+)\|", lg.group(0), re.M):
        legacy_names.update(expand(row))

# section 1 (current + legacy): Input | Output | Cache 5m | Cache 1h | Cache read
for blk in (tables(r"## 1\. Standard API Pricing.*?(?=### Legacy)"), lg.group(0) if lg else ""):
    for line in blk.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and re.search(r"Claude", cells[0]):
            vals = [money(c) for c in cells[1:6]]
            if None in vals:
                continue
            for nm in expand(cells[0]):
                models[api_id(nm)] = dict(name=nm, status="legacy" if nm in legacy_names else "current", input=vals[0], output=vals[1], cache_write_5m=vals[2], cache_write_1h=vals[3], cache_read=vals[4])

# section 2 batch
for line in tables(r"## 2\. Batch API Pricing.*?(?=\n## 3)").splitlines():
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) >= 3 and "Claude" in cells[0]:
        bi, bo = money(cells[1]), money(cells[2])
        for nm in expand(cells[0]):
            if api_id(nm) in models:
                models[api_id(nm)].update(batch_input=bi, batch_output=bo)
# section 3 fast
for line in tables(r"## 3\. Fast Mode Pricing.*?(?=\n## 4)").splitlines():
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) >= 3 and "Claude" in cells[0]:
        fi, fo = money(cells[1]), money(cells[2])
        for nm in expand(cells[0]):
            if api_id(nm) in models:
                models[api_id(nm)].update(fast_input=fi, fast_output=fo)

warn = []
for k, m in models.items():
    i = m["input"]
    if abs(m["cache_write_5m"] - 1.25 * i) > 0.011:
        warn.append("%s cache write 5m %.2f != 1.25 x input %.2f" % (k, m["cache_write_5m"], i))
    if abs(m["cache_write_1h"] - 2.0 * i) > 0.011:
        warn.append("%s cache write 1h %.2f != 2 x input %.2f" % (k, m["cache_write_1h"], i))
    mult = m["cache_read"] / i
    m["cache_read_multiplier"] = round(mult, 3)
    if round(mult, 3) not in (0.1, 0.05, 0.025):
        warn.append("%s cache read multiplier %.3f is not 0.1 / 0.05 / 0.025" % (k, mult))
    if m.get("batch_input") is not None and (abs(m["batch_input"] - 0.5 * i) > 0.011 or abs(m["batch_output"] - 0.5 * m["output"]) > 0.011):
        warn.append("%s batch is not 50%% of standard" % k)
    if m.get("fast_input") is not None and (abs(m["fast_input"] - 2 * i) > 0.011 or abs(m["fast_output"] - 2 * m["output"]) > 0.011):
        warn.append("%s fast mode is not 2x standard" % k)
ver = re.search(r"verified ([A-Za-z]+ \d+, \d{4})", text)
verified = dt.datetime.strptime(ver.group(1), "%b %d, %Y").date().isoformat() if ver else None
out = dict(meta=dict(source="https://platform.claude.com/docs/en/about-claude/pricing", sheet=os.path.relpath(sheet, SKILL), verified=verified, checked_against_live_page=live,
                     generated=dt.date.today().isoformat(), unit="USD per million tokens", warnings=warn,
                     notes=["thinking tokens are billed as output tokens (they are already inside usage.output_tokens)",
                            "cost computed from these rates is the API list-price equivalent: a Claude Code subscription is not billed per token",
                            "Claude 4.7+ models use a tokenizer that yields ~30% more tokens for the same text than 4.6 and earlier"]),
           modifiers=dict(data_residency_us_multiplier=1.1, web_search_per_1000=10.0, web_fetch_extra=0.0, code_execution_free_hours_per_org_month=1550, code_execution_per_hour_after=0.05,
                          managed_agent_session_hour=0.08, batch_discount=0.5),
           models=models)
json.dump(out, open(os.path.join(SKILL, "pricing", "pricing.json"), "w"), indent=1)
legacy = {"_doc": "GENERATED from job-receipt/pricing/claude-model-pricing-sheet.md by pricing_from_sheet.py (USD per MTok). Do not edit by hand."}
for k, m in models.items():
    legacy[k] = dict([("in", m["input"]), ("out", m["output"]), ("cache_write_5m", m["cache_write_5m"]), ("cache_write_1h", m["cache_write_1h"]), ("cache_read", m["cache_read"])])
json.dump(legacy, open(os.path.join(SKILL, "..", "quality-gate", "scripts", "prices.json"), "w"), indent=1)
cur = [k for k, m in models.items() if m["status"] == "current"]
print("parsed %d models (%d current, %d legacy), verified %s, live-checked %s" % (len(models), len(cur), len(models) - len(cur), verified, live or "not recorded"))
print("current:", ", ".join(cur))
print("consistency warnings: %s" % ("none" if not warn else "\n  " + "\n  ".join(warn)))
