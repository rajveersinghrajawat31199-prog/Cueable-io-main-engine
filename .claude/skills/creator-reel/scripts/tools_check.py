#!/usr/bin/env python3
"""Print the creator-reel tool registry (tools.json) with what is installed. Run it at the START of every creator job:
the point is to use the registered tool for each stage instead of improvising. Never prints secret values."""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
T = json.load(open(os.path.join(HERE, "..", "tools.json")))


def has_secret(name):
    if os.environ.get(name):
        return True
    p = os.path.expanduser("~/.config/hyperframes/secrets.env")
    return os.path.exists(p) and any(l.strip().lstrip("export ").startswith(name + "=") for l in open(p))


def probe(chk):
    kind, _, val = (chk or "none:").partition(":")
    if kind == "path":
        p = os.path.expanduser(val)
        return os.path.exists(p if os.path.isabs(p) else os.path.join(REPO, p))
    if kind == "env":
        return has_secret(val)
    if kind == "cmd":
        return shutil.which(val) is not None
    if kind == "engine":
        return True            # shipped with the pinned hyperframes CLI (npx); not executed here
    return None


quiet = "--short" in sys.argv
print("creator-reel tools (%s)\n" % T["updated"])
for name, s in T["slots"].items():
    st = s.get("status") or ("order: " + " > ".join(s["order"]["default"]) if "order" in s else "")
    print("%-17s %-34s use first: %s" % (name, st[:34], s["use_first"][:100]))
    if quiet:
        continue
    chks = [(s.get("check"), s["use_first"])] if s.get("check") else []
    for i in s.get("installed", []):
        ok = probe(i.get("check"))
        print("    %s %-62s %s" % ({True: "ok ", False: "MISSING", None: "-"}[ok] if ok is not False else "MISSING", i["name"][:62], i.get("kind", "")))
    if s.get("check"):
        ok = probe(s["check"])
        print("    %s %s" % ("ok " if ok else "MISSING", s["check"]))
print("\nUnregistered stage = a gap: say so to the user instead of improvising in silence.")
