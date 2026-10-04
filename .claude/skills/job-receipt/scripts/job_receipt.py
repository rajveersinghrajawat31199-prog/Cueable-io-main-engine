#!/usr/bin/env python3
"""Job receipt: how long a video job really took, how many model tokens it used, what it cost, what external credits it spent.

  job_receipt.py start  [--project .] [--name N]          mark the start of a job (receipt window opens, this session is recorded)
  job_receipt.py mark   [--project .] STAGE               a stage begins here (the previous one ends)
  job_receipt.py credit [--project .] PROVIDER AMOUNT [--unit credits|usd] [--note ...]   external spend (Pollo, ElevenLabs, ...)
  job_receipt.py usage  [--project .] --model M --in N --out N [--cache-read N --cache-write N]   tokens when there is no transcript (SaaS backend)
  job_receipt.py stop   [--project .]                      close the window
  job_receipt.py report [--project .] [--since T --until T | --session] [--name N] [--what-if] [--transcript PATH] [--idle 300] [--json]
  job_receipt.py sessions [--since YYYY-MM-DD] [--json]   every Claude Code session of this project: time, tokens, cost
  job_receipt.py verify                                    re-price Claude Code's own recorded totals with pricing.json and compare dollars
        T = "YYYY-MM-DD HH:MM" (local time) or ISO. Without --since the window comes from the project's marks.

Sources (nothing is guessed):
  tokens, model calls, tool calls, images viewed, cache-write duration (5 min / 1 h), fast mode, region: the Claude Code session transcript
      (~/.claude/projects/<slug>/<session>.jsonl plus <session>/subagents/*.jsonl). Only timestamps, usage numbers and tool names are read, never message text.
      The session that ran the job is found from the Claude Code process that runs this shell (--resume=<id>), not from "newest file":
      two sessions can be live in one project at the same time.
  machine seconds: <project>/quality/timing.jsonl (stage_timer.py).   external credits / API tokens: <project>/quality/receipt-events.jsonl.
  prices: job-receipt/pricing/pricing.json, generated from the pricing sheet next to it (pricing_from_sheet.py). Cost = API LIST-PRICE EQUIVALENT:
      a Claude Code subscription is not billed per token, but this is what the same tokens cost through the API (what the SaaS backend pays).
      `verify` checks the method against Claude Code's own cost records. It cannot see Claude Code's background calls (titles, suggestions): those
      add roughly 2-9 % where Claude Code kept its own total, so a receipt is a slight under-count, never an over-count.
Active time = wall clock minus idle gaps (default: gaps over 5 min, e.g. the customer being away).
"""
import argparse, collections, datetime as dt, glob, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
STUDIO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PRICING = os.path.join(SKILL, "pricing", "pricing.json")
VERIFY_JSON = os.path.join(SKILL, "pricing", "last-verify.json")
WHATIF = ["claude-haiku-4-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1"]
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def parse_t(s):
    if s is None:
        return None
    s = s.strip()
    if s.endswith("Z") or "+" in s[10:] or s[10:].count("-") > 0:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    fmt = "%Y-%m-%d %H:%M:%S" if s.count(":") == 2 else ("%Y-%m-%d %H:%M" if s.count(":") == 1 else "%Y-%m-%d")
    return dt.datetime.strptime(s, fmt).timestamp()


def iso_t(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def hhmm(t):
    return dt.datetime.fromtimestamp(t).strftime("%H:%M")


def stamp(t):
    return dt.datetime.fromtimestamp(t).strftime("%m-%d %H:%M")


# ---- which transcript belongs to this job

def project_dir():
    return os.path.expanduser("~/.claude/projects/" + re.sub(r"[^A-Za-z0-9]", "-", STUDIO))


def project_transcripts():
    return sorted(glob.glob(os.path.join(project_dir(), "*.jsonl")))


def session_path(sid):
    p = os.path.join(project_dir(), sid + ".jsonl")
    if os.path.exists(p):
        return p
    g = glob.glob(os.path.expanduser("~/.claude/projects/*/%s.jsonl" % sid))
    return g[0] if g else None


def ancestor_session_id():
    """The Claude Code process that runs this shell carries --resume=<uuid> or --session-id <uuid> on its command line."""
    pid = os.getpid()
    for _ in range(12):
        try:
            out = subprocess.run(["ps", "-ww", "-o", "ppid=,command=", "-p", str(pid)], capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            return None
        parts = out.split(None, 1)
        if len(parts) < 2:
            return None
        cmd = parts[1]
        if not re.match(r"(\S*/)?(zsh|bash|sh|dash|fish)\b", cmd):
            mm = re.search(r"--(?:resume|session-id)[= ](%s)" % UUID, cmd)
            if mm:
                return mm.group(1)
        try:
            pid = int(parts[0])
        except ValueError:
            return None
        if pid <= 1:
            return None
    return None


def first_ts(path):
    try:
        with open(path, "r", errors="ignore") as fh:
            for i, line in enumerate(fh):
                if '"timestamp"' in line:
                    try:
                        return iso_t(json.loads(line)["timestamp"])
                    except Exception:
                        pass
                if i > 300:
                    break
    except OSError:
        pass
    return None


def transcript_files(main):
    """A session's own transcript plus the transcripts of the subagents it spawned."""
    return [main] + sorted(glob.glob(os.path.join(main[:-len(".jsonl")], "subagents", "*.jsonl")))


def window_candidates(since, until):
    out = []
    for f in project_transcripts():
        if os.path.getmtime(f) < since:
            continue
        ft = first_ts(f)
        if ft is not None and ft > until:
            continue
        out.append(f)
    return out


# ---- reading transcripts

def usage_numbers(u):
    """Billable tokens of one message. If the API reports several iterations (compaction, advisor), they all count."""
    its = u.get("iterations") or []
    src = its if len(its) > 1 else [u]
    r = dict(inp=0, cw5=0, cw1=0, cwu=0, cr=0, out=0)
    for x in src:
        cc = x.get("cache_creation") or {}
        c5, c1 = cc.get("ephemeral_5m_input_tokens") or 0, cc.get("ephemeral_1h_input_tokens") or 0
        tot = x.get("cache_creation_input_tokens") or 0
        r["inp"] += x.get("input_tokens") or 0
        r["cw5"] += c5
        r["cw1"] += c1
        r["cwu"] += max(0, tot - c5 - c1)
        r["cr"] += x.get("cache_read_input_tokens") or 0
        r["out"] += x.get("output_tokens") or 0
    r["think"] = (u.get("output_tokens_details") or {}).get("thinking_tokens") or 0
    r["web"] = (u.get("server_tool_use") or {}).get("web_search_requests") or 0
    return r


def read_transcript(paths, since=None, until=None):
    """-> dict(events [epoch], calls {message id: dict}, tools Counter, images int, title str). Streams the files; reads no message text."""
    if isinstance(paths, str):
        paths = [paths]
    events, calls, tools, images, title = [], {}, collections.Counter(), 0, None
    img_ext = (".png", ".jpg", ".jpeg", ".webp", ".gif")
    for pi, path in enumerate(paths):
        with open(path, "r", errors="ignore") as fh:
            for line in fh:
                if '"custom-title"' in line:
                    try:
                        d = json.loads(line)
                        if d.get("type") == "custom-title" and d.get("customTitle"):
                            title = d["customTitle"]
                    except Exception:
                        pass
                    continue
                if '"timestamp"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                ts = d.get("timestamp")
                if not ts or d.get("type") not in ("user", "assistant"):
                    continue
                try:
                    t = iso_t(ts)
                except Exception:
                    continue
                if (since and t < since) or (until and t > until):
                    continue
                events.append(t)
                if d.get("type") != "assistant":
                    continue
                m = d.get("message") or {}
                mid = m.get("id") or d.get("uuid")
                u = m.get("usage") or {}
                r = usage_numbers(u)
                c = calls.setdefault(mid, dict(t=t, model=m.get("model"), inp=0, cw5=0, cw1=0, cwu=0, cr=0, out=0, think=0, speed=None, geo=None, web=0, sub=pi > 0))
                for k in ("inp", "cw5", "cw1", "cwu", "cr", "out", "think", "web"):
                    c[k] = max(c[k], r[k])
                c["speed"] = u.get("speed") or c["speed"]
                c["geo"] = u.get("inference_geo") or c["geo"]
                for blk in m.get("content") or []:
                    if isinstance(blk, dict) and blk.get("type") == "tool_use":
                        tools[blk.get("name")] += 1
                        fp = ((blk.get("input") or {}).get("file_path") or "").lower()
                        if blk.get("name") == "Read" and fp.endswith(img_ext):
                            images += 1
    return dict(events=events, calls=calls, tools=tools, images=images, title=title)


def active_seconds(events, idle):
    ev = sorted(events)
    act = idle_total = 0.0
    for a, b in zip(ev, ev[1:]):
        g = b - a
        if g <= idle:
            act += g
        else:
            idle_total += g
    return act, idle_total


def load_jsonl(p):
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def fmt_n(n):
    return "%.2fM" % (n / 1e6) if n >= 1e6 else ("%.1fk" % (n / 1e3) if n >= 1e3 else str(int(n)))


def fmt_min(s):
    s = int(round(s))
    return "%d min %02d s" % (s // 60, s % 60) if s >= 60 else "%d s" % s


# ---- prices

def norm_model(m):
    if not m:
        return None
    m = m.lower()
    m = re.sub(r"-\d{8}$", "", m)
    return re.sub(r"-latest$", "", m)


def load_pricing():
    return json.load(open(PRICING)) if os.path.exists(PRICING) else None


def rates(m, fast=False):
    """-> input, output, cache_write_5m, cache_write_1h, cache_read  (USD per MTok)"""
    if fast and m.get("fast_input"):
        i = m["fast_input"]
        return i, m["fast_output"], i * 1.25, i * 2.0, i * m["cache_read_multiplier"]
    return m["input"], m["output"], m["cache_write_5m"], m["cache_write_1h"], m["cache_read"]


def cost_of(calls, pricing, force_model=None):
    """-> (parts Counter USD: input, cache_write, cache_read, output, web_search | by_model {model: Counter} | unpriced Counter | notes Counter)."""
    parts, by_model, unpriced, notes = collections.Counter(), collections.defaultdict(collections.Counter), collections.Counter(), collections.Counter()
    if not pricing:
        return parts, by_model, unpriced, notes
    for c in calls.values():
        if c["model"] == "<synthetic>":
            continue
        mid = force_model or norm_model(c["model"])
        m = pricing["models"].get(mid)
        if not m:
            unpriced[mid] += 1
            continue
        fast = c.get("speed") == "fast" and not force_model
        ri, ro, w5, w1, rd = rates(m, fast)
        mult = pricing["modifiers"]["data_residency_us_multiplier"] if c.get("geo") == "us" else 1.0
        p = dict(input=c["inp"] * ri, cache_write=c["cw5"] * w5 + c["cw1"] * w1 + c["cwu"] * w5, cache_read=c["cr"] * rd, output=c["out"] * ro)
        for k, v in p.items():
            v = v * mult / 1e6
            parts[k] += v
            by_model[mid][k] += v
        ws = c.get("web", 0) * pricing["modifiers"]["web_search_per_1000"] / 1000.0
        parts["web_search"] += ws
        by_model[mid]["web_search"] += ws
        if c["cwu"]:
            notes["unsplit_calls"] += 1
            notes["unsplit_tokens"] += c["cwu"]
            notes["unsplit_extra_usd"] += c["cwu"] * (w1 - w5) / 1e6
        notes["fast_calls"] += 1 if fast else 0
        notes["geo_calls"] += 1 if mult != 1.0 else 0
        notes["web_searches"] += c.get("web", 0)
    return parts, by_model, unpriced, notes


def money(x):
    return "$%.2f" % x if x >= 0.01 or x == 0 else "$%.3f" % x


def price_note(pricing):
    if not pricing:
        return "no pricing.json"
    v = pricing["meta"].get("verified")
    age = (dt.date.today() - dt.date.fromisoformat(v)).days if v else None
    s = "prices verified %s%s" % (v, ("" if age is None or age <= 45 else "  WARNING: %d days old, refresh pricing/claude-model-pricing-sheet.md" % age))
    if os.path.exists(VERIFY_JSON):
        try:
            r = json.load(open(VERIFY_JSON))
            s += "; matches Claude Code's own cost records on %d of %d model entries (largest gap %s)" % (r["within_tolerance"], r["records"], money(r["max_abs_diff_usd"]))
        except Exception:
            pass
    return s


def assumption_lines(notes):
    out = []
    if notes.get("unsplit_calls"):
        out.append("%d calls have no 5-min/1-h cache split (%s tokens): priced at the 5-min rate, so up to %s more if they were 1-hour" % (notes["unsplit_calls"], fmt_n(notes["unsplit_tokens"]), money(notes["unsplit_extra_usd"])))
    if notes.get("fast_calls"):
        out.append("%d calls ran in fast mode and are priced at the fast-mode rates" % notes["fast_calls"])
    if notes.get("geo_calls"):
        out.append("%d calls used US data residency and carry the 1.1x multiplier" % notes["geo_calls"])
    if notes.get("web_searches"):
        out.append("%d web searches billed at $10 per 1000" % notes["web_searches"])
    return out


def summarize(calls):
    tot = collections.Counter()
    for c in calls.values():
        tot["inp"] += c["inp"]
        tot["cw"] += c["cw5"] + c["cw1"] + c["cwu"]
        tot["cr"] += c["cr"]
        tot["out"] += c["out"]
        tot["think"] += c["think"]
    return tot


def short_model(m):
    return (m or "?").replace("claude-", "")


# ---- commands

def cmd_sessions(a, pricing):
    floor = parse_t(a.since) if a.since else None
    rows, seen = [], set()
    all_parts, all_by_model, all_notes = collections.Counter(), collections.Counter(), collections.Counter()
    mains = sorted(project_transcripts(), key=lambda f: first_ts(f) or 0)
    for f in mains:
        data = read_transcript(transcript_files(f))
        calls = {k: v for k, v in data["calls"].items() if k not in seen}
        seen.update(calls)
        if not data["events"] or (floor and max(data["events"]) < floor):
            continue
        act, _ = active_seconds(data["events"], a.idle)
        parts, bm, unp, notes = cost_of(calls, pricing)
        tot = summarize(calls)
        for k, v in parts.items():
            all_parts[k] += v
        for m, v in bm.items():
            all_by_model[m] += sum(v.values())
        for k, v in notes.items():
            all_notes[k] += v
        rows.append(dict(session=os.path.basename(f)[:8], title=data["title"] or "", start=min(data["events"]), end=max(data["events"]), active_s=round(act), calls=len(calls), subagent_calls=sum(1 for c in calls.values() if c["sub"]),
                         output=tot["out"], cache_write=tot["cw"], cache_read=tot["cr"], cost=round(sum(parts.values()), 2),
                         models=sorted(set(short_model(norm_model(c["model"])) for c in calls.values() if c["model"] != "<synthetic>")), unpriced=dict(unp)))
    rows.sort(key=lambda r: r["start"])
    if a.json:
        print(json.dumps(dict(sessions=rows, total_usd=round(sum(all_parts.values()), 2), by_token_type_usd={k: round(v, 2) for k, v in all_parts.items()}, by_model_usd={k: round(v, 2) for k, v in all_by_model.items()}), indent=1))
        return
    print("CLAUDE CODE SESSIONS  (API list-price equivalent; %s)" % price_note(pricing))
    print("  session   title                       start        active     calls  (sub)   output  cache-write  cache-read      cost  models")
    for r in rows:
        print("  %-8s  %-26s  %-11s  %9s  %6d  %5d  %7s  %11s  %10s  %8s  %s" % (r["session"], (r["title"] or "-")[:26], stamp(r["start"]), fmt_min(r["active_s"]), r["calls"], r["subagent_calls"], fmt_n(r["output"]), fmt_n(r["cache_write"]), fmt_n(r["cache_read"]),
                                                                                  money(r["cost"]), ",".join(r["models"])))
    print("  %-8s  %-26s  %-11s  %9s  %6d  %5d  %7s  %11s  %10s  %8s" % ("TOTAL", "", "", fmt_min(sum(r["active_s"] for r in rows)), sum(r["calls"] for r in rows), sum(r["subagent_calls"] for r in rows), fmt_n(sum(r["output"] for r in rows)),
                                                                          fmt_n(sum(r["cache_write"] for r in rows)), fmt_n(sum(r["cache_read"] for r in rows)), money(sum(all_parts.values()))))
    print("  by token type: input %s | cache write %s | cache read %s | output %s%s" % (money(all_parts["input"]), money(all_parts["cache_write"]), money(all_parts["cache_read"]), money(all_parts["output"]), (" | web search " + money(all_parts["web_search"])) if all_parts["web_search"] else ""))
    print("  by model: " + " | ".join("%s %s" % (short_model(m), money(v)) for m, v in sorted(all_by_model.items(), key=lambda kv: -kv[1])))
    for line in assumption_lines(all_notes):
        print("  note: " + line)
    print("  note: sessions are listed by the transcripts' own timestamps; the table cannot see Claude Code's background calls (titles, suggestions), roughly 2-9 % more where it kept its own total (run `verify`).")


def cmd_verify(a, pricing):
    rows = []
    for f in project_transcripts():
        last = None
        for line in open(f, errors="ignore"):
            if '"cost-state"' in line:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if o.get("type") == "cost-state":
                    last = o
        if not last:
            continue
        for model, mu in (last.get("modelUsage") or {}).items():
            mid = norm_model(model)
            m = pricing["models"].get(mid)
            cli = mu.get("costUSD") or 0.0
            if not m:
                rows.append(dict(session=os.path.basename(f)[:8], model=mid, cli=cli, repriced=None, diff=None, ok=False, note="no price entry"))
                continue
            web = (mu.get("webSearchRequests") or 0) * pricing["modifiers"]["web_search_per_1000"] / 1000.0
            mine = (mu["inputTokens"] * m["input"] + mu["outputTokens"] * m["output"] + mu["cacheReadInputTokens"] * m["cache_read"] + mu["cacheCreationInputTokens"] * m["cache_write_1h"]) / 1e6 + web
            diff = mine - cli
            rows.append(dict(session=os.path.basename(f)[:8], model=mid, cli=cli, repriced=round(mine, 4), diff=round(diff, 4), ok=abs(diff) <= max(0.10, 0.01 * cli), exact=abs(diff) <= 0.005, note=""))
    res = dict(date=dt.date.today().isoformat(), records=len(rows), exact=sum(1 for r in rows if r.get("exact")), within_tolerance=sum(1 for r in rows if r["ok"]),
               max_abs_diff_usd=round(max([abs(r["diff"]) for r in rows if r["diff"] is not None] or [0]), 4), method="Claude Code cost-state token counts re-priced with pricing.json (cache writes at the 1-hour rate)", rows=rows)
    json.dump({k: v for k, v in res.items() if k != "rows"}, open(VERIFY_JSON, "w"), indent=1)   # summary only: per-session dollars stay out of the repo
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        print("VERIFY  pricing.json vs the totals Claude Code recorded itself (cost-state in each transcript; %s)" % price_note(pricing))
        print("  session   model                          Claude Code $   re-priced $      diff")
        for r in rows:
            print("  %-8s  %-28s  %13.4f  %11s  %8s  %s" % (r["session"], r["model"], r["cli"], "-" if r["repriced"] is None else "%.4f" % r["repriced"], "-" if r["diff"] is None else "%+.4f" % r["diff"],
                                                           "" if r["ok"] else "<-- CHECK " + r["note"]))
        print("  %d model entries: %d exact to the cent, %d within 1%% or $0.10, largest gap %s. Written to pricing/last-verify.json." % (res["records"], res["exact"], res["within_tolerance"], money(res["max_abs_diff_usd"])))
    if res["within_tolerance"] < res["records"]:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["start", "mark", "credit", "usage", "stop", "report", "sessions", "verify"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--project", default=".")
    ap.add_argument("--name", default=None)
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--session", action="store_true")
    ap.add_argument("--what-if", action="store_true")
    ap.add_argument("--transcript")
    ap.add_argument("--idle", type=float, default=300.0)
    ap.add_argument("--unit", default="credits")
    ap.add_argument("--note", default="")
    ap.add_argument("--model")
    ap.add_argument("--in", dest="tin", type=int, default=0)
    ap.add_argument("--out", dest="tout", type=int, default=0)
    ap.add_argument("--cache-read", type=int, default=0)
    ap.add_argument("--cache-write", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_intermixed_args()
    pricing = load_pricing()
    if a.cmd == "sessions":
        return cmd_sessions(a, pricing)
    if a.cmd == "verify":
        if not pricing:
            sys.exit("no pricing/pricing.json: run scripts/pricing_from_sheet.py")
        return cmd_verify(a, pricing)

    Q = os.path.join(os.path.abspath(a.project), "quality")
    os.makedirs(Q, exist_ok=True)
    EV = os.path.join(Q, "receipt-events.jsonl")

    def log(rec):
        rec["t"] = time.time()
        open(EV, "a").write(json.dumps(rec) + "\n")

    if a.cmd == "start":
        log({"kind": "start", "name": a.name or os.path.basename(os.path.abspath(a.project)), "session": ancestor_session_id()}); print("receipt window opened", hhmm(time.time())); return
    if a.cmd == "mark":
        log({"kind": "stage", "stage": " ".join(a.args)}); print("stage:", " ".join(a.args)); return
    if a.cmd == "credit":
        if len(a.args) < 2:
            sys.exit("credit PROVIDER AMOUNT")
        log({"kind": "credit", "provider": a.args[0], "amount": float(a.args[1]), "unit": a.unit, "note": a.note}); print("logged"); return
    if a.cmd == "usage":
        log({"kind": "usage", "model": a.model, "in": a.tin, "out": a.tout, "cache_read": a.cache_read, "cache_write": a.cache_write}); print("logged"); return
    if a.cmd == "stop":
        log({"kind": "stop"}); print("receipt window closed", hhmm(time.time())); return

    # ---- report
    evs = load_jsonl(EV)
    starts = [e for e in evs if e["kind"] == "start"]
    stops = [e for e in evs if e["kind"] == "stop"]
    derived = not a.since and not a.session
    pref = (starts[-1].get("session") if starts and derived else None) or ancestor_session_id()
    others = []
    data = dict(events=[], calls={}, tools=collections.Counter(), images=0, title=None)
    tpath = None
    if a.transcript:
        tpath = a.transcript
    elif a.session:
        tpath = (session_path(pref) if pref else None) or (project_transcripts() or [None])[-1]
    if a.session and tpath:
        whole = read_transcript(transcript_files(tpath))
        since, until = (min(whole["events"]), max(whole["events"])) if whole["events"] else (None, None)
    else:
        since = parse_t(a.since) if a.since else (starts[-1]["t"] if starts else None)
        until = parse_t(a.until) if a.until else (stops[-1]["t"] if stops and (not starts or stops[-1]["t"] > starts[-1]["t"]) else time.time())
    if since is None:
        sys.exit("no window: run `job_receipt.py start`, pass --since, or use --session")
    if tpath:
        data = read_transcript(transcript_files(tpath), since, until)
    else:
        found = {}
        for f in window_candidates(since, until):
            d = read_transcript(transcript_files(f), since, until)
            if d["calls"]:
                found[f] = d
        if found:
            pick = next((f for f in found if os.path.basename(f)[:-len(".jsonl")] == pref), None) or max(found, key=lambda f: len(found[f]["calls"]))
            tpath, data = pick, found[pick]
            others = [(os.path.basename(f)[:8], len(d["calls"])) for f, d in found.items() if f != pick]
    name = a.name or (starts[-1].get("name") if starts and derived else None) or ("whole session" if a.session else os.path.basename(os.path.abspath(a.project)))
    events, calls, tools, images = data["events"], data["calls"], data["tools"], data["images"]
    wall = until - since
    act, idle_total = active_seconds(events, a.idle) if events else (0.0, 0.0)
    api = [e for e in evs if e["kind"] == "usage" and since <= e["t"] <= until]
    for i, e in enumerate(api):
        calls["api%d" % i] = dict(t=e["t"], model=e.get("model"), inp=e["in"], cw5=e.get("cache_write", 0), cw1=0, cwu=0, cr=e.get("cache_read", 0), out=e["out"], think=0, speed=None, geo=None, web=0, sub=False)
    tot = summarize(calls)
    parts, by_model, unpriced, notes = cost_of(calls, pricing)
    machine = [r for r in load_jsonl(os.path.join(Q, "timing.jsonl")) if since <= (r.get("start") or 0) <= until]
    machine_s = sum(r.get("seconds") or 0 for r in machine)
    credits = [e for e in evs if e["kind"] == "credit" and since <= e["t"] <= until]
    stages = [e for e in evs if e["kind"] == "stage" and since <= e["t"] <= until]
    stage_rows = []
    if stages:
        bounds = [(since, "(before first stage)")] + [(e["t"], e["stage"]) for e in stages] + [(until, None)]
        for (t0, s), (t1, _) in zip(bounds, bounds[1:]):
            cs = {k: c for k, c in calls.items() if t0 <= c["t"] < t1}
            ts = [x for x in events if t0 <= x < t1]
            a_s, _i = active_seconds(ts, a.idle) if ts else (0, 0)
            sp, _bm, _u, _n = cost_of(cs, pricing)
            stage_rows.append(dict(stage=s, wall=t1 - t0, active=a_s, calls=len(cs), out=sum(c["out"] for c in cs.values()), cr=sum(c["cr"] for c in cs.values()), cost=round(sum(sp.values()), 2)))
    total_cost = sum(parts.values())
    what_if = {}
    if a.what_if and pricing:
        for mid in WHATIF:
            p2, _b, _u, _n = cost_of(calls, pricing, force_model=mid)
            what_if[mid] = round(sum(p2.values()), 2)
    sid = os.path.basename(tpath)[:8] if tpath else None
    rec = dict(name=name, session=sid, session_title=data["title"], since=since, until=until, wall_s=round(wall), active_s=round(act), idle_s=round(idle_total), model_calls=len(calls), subagent_calls=sum(1 for c in calls.values() if c.get("sub")),
               tool_calls=sum(tools.values()), tools=dict(tools.most_common()), images_viewed=images, tokens=dict(new_input=tot["inp"], cache_write=tot["cw"], cache_read=tot["cr"], output=tot["out"], thinking=tot["think"]), machine_s=round(machine_s, 1),
               credits=[dict(provider=e["provider"], amount=e["amount"], unit=e["unit"], note=e["note"]) for e in credits],
               cost_usd=None if not pricing or (unpriced and not parts) else round(total_cost, 2), cost_breakdown_usd={k: round(v, 2) for k, v in parts.items()},
               cost_by_model={m: round(sum(v.values()), 2) for m, v in by_model.items()}, unpriced_models=dict(unpriced), price_note=price_note(pricing), what_if_same_tokens=what_if, stages=stage_rows,
               other_active_sessions=[dict(session=s, calls=n) for s, n in others], transcript=tpath)
    json.dump(rec, open(os.path.join(Q, "receipt.json"), "w"), indent=1)
    if a.json:
        print(json.dumps(rec, indent=1)); return
    print("JOB RECEIPT  %s   %s -> %s (local)" % (name, stamp(since) if until - since > 86400 else hhmm(since), stamp(until) if until - since > 86400 else hhmm(until)))
    if sid:
        print("  session    %s%s" % (sid, (' "%s"' % data["title"]) if data["title"] else ""))
    print("  time       wall %s | active %s (idle gaps over %d s excluded: %s) | machine (renders, gates) %s" % (fmt_min(wall), fmt_min(act), a.idle, fmt_min(idle_total), fmt_min(machine_s)))
    mc = ", ".join("%s %d" % (k, v) for k, v in tools.most_common(6))
    sub = rec["subagent_calls"]
    print("  work       %d model calls%s | %d tool calls (%s) | %d images viewed" % (len(calls), (" (%d by subagents)" % sub) if sub else "", sum(tools.values()), mc, images))
    print("  tokens     new input %s | cache write %s | cache read %s | output %s (thinking %s, included in output)" % (fmt_n(tot["inp"]), fmt_n(tot["cw"]), fmt_n(tot["cr"]), fmt_n(tot["out"]), fmt_n(tot["think"])))
    models = collections.Counter(norm_model(c["model"]) or "?" for c in calls.values() if c["model"] != "<synthetic>")
    print("  models     " + (", ".join("%s (%d calls)" % (m, n) for m, n in models.items()) if models else "none"))
    print("  credits    " + ("; ".join("%s %g %s" % (c["provider"], c["amount"], c["unit"]) for c in rec["credits"]) if credits else "none logged (no external paid calls recorded)"))
    if rec["cost_usd"] is None:
        print("  cost       not computed (%s)%s" % (price_note(pricing), (" no price for " + ", ".join(str(k) for k in unpriced)) if unpriced else ""))
    else:
        print("  cost       %s API-equivalent: input %s | cache write %s | cache read %s | output %s%s" % (money(total_cost), money(parts["input"]), money(parts["cache_write"]), money(parts["cache_read"]), money(parts["output"]),
                                                                                                         (" | web search " + money(parts["web_search"])) if parts["web_search"] else ""))
        print("             (%s)" % price_note(pricing))
        if unpriced:
            print("             NOT PRICED: %s (no entry in pricing.json): total is a lower bound" % ", ".join(str(k) for k in unpriced))
    for line in assumption_lines(notes):
        print("             note: " + line)
    if others:
        print("  note       %d other session%s also active in this window (%s): not counted here, `sessions` lists them" % (len(others), "" if len(others) == 1 else "s", ", ".join("%s %d calls" % o for o in others)))
    if what_if:
        print("  what-if    the same tokens on: " + " | ".join("%s %s" % (m.replace("claude-", ""), money(v)) for m, v in what_if.items()))
        print("             (token counts are model-dependent: Claude 4.7+ tokenizers give ~30% more tokens than 4.6 and earlier, and a stronger model may need fewer steps: a guide, not a quote)")
    if stage_rows:
        print("  stage                          wall    active  calls  output   cache-read    cost")
        for r in stage_rows:
            print("  %-28s %7s %8s %6d %7s %11s %7s" % (r["stage"][:28], fmt_min(r["wall"]), fmt_min(r["active"]), r["calls"], fmt_n(r["out"]), fmt_n(r["cr"]), money(r["cost"])))


if __name__ == "__main__":
    main()
