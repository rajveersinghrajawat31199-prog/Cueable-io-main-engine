#!/usr/bin/env python3
"""Regression test: analyzer output vs hand-measured ground truth.
  selftest.py REFERENCE_VIDEO [--json existing reference-style.json]   exit 1 on any FAIL
"""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
gt = json.load(open(os.path.join(HERE, "..", "tests", "inktober_ground_truth.json")))
args = sys.argv[1:]
js = args[args.index("--json") + 1] if "--json" in args else None
if not js:
    out = tempfile.mkdtemp(prefix="refselftest_")
    subprocess.run([sys.executable, os.path.join(HERE, "analyze.py"), args[0], "--out", out], capture_output=True)
    js = os.path.join(out, "reference-style.json")
j = json.load(open(js))
S = j["scenes"]
fails = 0


def check(name, ok, got, want):
    global fails
    fails += 0 if ok else 1
    print("%s  %-28s got %s  want %s" % ("PASS" if ok else "FAIL", name, got, want))


check("cut frames", [c["frame"] for c in j["cuts"]] == gt["cuts"], [c["frame"] for c in j["cuts"]], gt["cuts"])
check("scene count", len(S) == gt["scene_count"], len(S), gt["scene_count"])
check("transition 352", any(t["start_frame"] == 352 and t["frames"] == 6 for t in j["transitions"]), [(t["start_frame"], t["frames"]) for t in j["transitions"]], "352/6")
check("background colours", [s["bg"] for s in S] == gt["scene_bg"], [s["bg"] for s in S], gt["scene_bg"])
lp = S[2]["motion"].get("loop_period_frames")
check("scene 3 loop period", lp is not None and gt["scene3_loop_frames"][0] <= lp <= gt["scene3_loop_frames"][1], lp, gt["scene3_loop_frames"])
check("scene 4 step cadence", any("step-cadence(%dfps)" % gt["scene4_step_fps"] in t for t in S[3]["tags"]), S[3]["tags"], "8fps")
check("scene 6 static hold", "static-hold" in S[5]["tags"], S[5]["tags"], "static-hold")
au = j["audio"] or {}
check("tempo", au and gt["bpm"][0] <= au["tempo"]["bpm"] <= gt["bpm"][1], au["tempo"]["bpm"] if au else None, gt["bpm"])
check("loudness", au and gt["lufs"][0] <= au["loudness_lufs"] <= gt["lufs"][1], au.get("loudness_lufs"), gt["lufs"])
check("voice-over", au and au["speech"]["likelihood"] == gt["voice_over"], au["speech"]["likelihood"] if au else None, gt["voice_over"])
for k, frag in gt["text_contains"].items():
    txt = " ".join(t["text"] for t in S[int(k) - 1]["text"]).lower()
    check("scene %s text" % k, frag.lower() in txt, txt[:60], frag)
check("tier", j["feasibility"]["tier"] == gt["tier"], j["feasibility"]["tier"], gt["tier"])
print("\n%s (%d check(s) failed)  analysis time %.1f s" % ("OK" if not fails else "FAILED", fails, j["timings"]["total"]))
sys.exit(1 if fails else 0)
