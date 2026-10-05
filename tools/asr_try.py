#!/usr/bin/env python3
"""Run several vibe-server CLI variants in parallel on one audio file and score them against a reference transcript.
Recall = share of the reference's Devanagari word tokens that the candidate also contains (English words are excluded because
engines disagree on script). Hallucination = repeats of the classic Whisper 'subscribe' ghost."""
import json, re, subprocess, sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "vibe")
AUDIO = sys.argv[1]; REF = sys.argv[2]; OUT = sys.argv[3]
MODEL = os.path.join(V, "models", "ggml-large-v3-q5_0.bin"); VAD = os.path.join(V, "models", "ggml-silero-v5.1.2.bin")
P_MIX = "आज मैं Hyrox के checkout page तक पहुंच गया था। यह Hinglish बातचीत है: Hindi और English मिलकर, जैसे scarcity, social proof, registration, laptop, startup."
P_ROM = "Aaj main Hyrox ke checkout page tak pahunch gaya tha. Phir main ruk gaya. Yeh Hinglish hai: Hindi aur English mixed, jaise scarcity, social proof, registration, laptop, startup."
VARIANTS = {
  "V2 hi + prompt(mixed)": ["-l", "hi", "--vad-model", VAD, "--beam-size", "5", "--prompt", P_MIX],
  "V3 auto-lang + prompt(roman)": ["--detect-language", "--vad-model", VAD, "--beam-size", "5", "--prompt", P_ROM],
  "V4 hi + prompt + enhance-audio": ["-l", "hi", "--vad-model", VAD, "--beam-size", "5", "--prompt", P_MIX, "--enhance-audio"],
}
procs = {}
for name, args in VARIANTS.items():
    t0 = time.time()
    procs[name] = (subprocess.Popen([os.path.join(V, "vibe-server"), "transcribe", MODEL, AUDIO] + args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL), t0)
ref = json.load(open(REF))
ref_words = [w["text"] for w in ref["words"] if w["type"] == "word"]
dev = lambda s: re.sub(r"[^ऀ-ॿ]", "", s)
ref_dev = [dev(w) for w in ref_words if re.search(r"[ऀ-ॿ]", w)]
def recall(text):
    toks = [dev(t) for t in re.split(r"\s+", text) if re.search(r"[ऀ-ॿ]", t)]
    pool = list(toks); hit = 0
    for r in ref_dev:
        if r in pool: pool.remove(r); hit += 1
    return hit / len(ref_dev), len(toks)
results = {}
for name, (p, t0) in procs.items():
    out = p.communicate()[0].decode("utf-8", "replace"); dt = time.time() - t0
    text = re.sub(r"\[[0-9:. >-]+\]", "", out).strip()
    r, n = recall(text)
    results[name] = dict(seconds=round(dt), recall=round(r, 2), tokens=n, subscribe_ghosts=len(re.findall("सब्सक्राइब|subscribe", text, re.I)), text=text)
    print("%-34s %4ds  recall %.0f%%  tokens %3d  'subscribe' ghosts %d" % (name, dt, 100 * r, n, results[name]["subscribe_ghosts"]))
    print("   ", text[:330].replace("\n", " "))
json.dump(results, open(OUT, "w"), ensure_ascii=False, indent=1)
