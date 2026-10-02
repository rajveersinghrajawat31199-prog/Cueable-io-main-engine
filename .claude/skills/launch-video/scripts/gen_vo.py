#!/usr/bin/env python3
"""ONE continuous ElevenLabs take for the whole SCRIPT.md, with word timings, cut into per-frame clips at the midpoint
of the gap between lines. Writes assets/vo/vo_NN.mp3, assets/vo/vo_full_<name>.mp3 (+ .words.json) and audio_meta.json
(product-launch shape: {bgm,voices:[{frame,path,duration_s,words}],sfx}).

Why one take: per-line TTS (the stock pipeline) gives every line its own edge pacing and end-of-utterance decay; one
take keeps cross-sentence rhythm and only the true last word has the decay risk.

usage:  ELEVENLABS_API_KEY=... gen_vo.py [--project .]
config: launch.config.json -> voice: {id, name, respell:{"ShopOS":"Shop O S"}, model, settings:{stability,similarity_boost,style}}
The key is read from the environment only; never printed, never written.
"""
import os, re, sys, json, base64, subprocess, urllib.request

args = sys.argv[1:]
ROOT = os.path.abspath(args[args.index("--project") + 1]) if "--project" in args else os.getcwd()
cfg = json.load(open(os.path.join(ROOT, "launch.config.json")))
V = cfg["voice"]
RESPELL = V.get("respell", {})

# ---- parse SCRIPT.md -> [(frame, text)]   ("## Line N — label (Frame N)" then an indented spoken block)
lines, cur = [], None
for ln in open(os.path.join(ROOT, "SCRIPT.md"), encoding="utf8"):
    h = re.match(r"^#{2,3}\s+.*?\(frame\s+(\d+)\)", ln, re.I)
    if h:
        cur = [int(h.group(1)), ""]; lines.append(cur); continue
    m = re.match(r"^(?: {4,}|\t)(.+)$", ln.rstrip("\n"))
    if cur is not None and m:
        cur[1] = (cur[1] + " " + m.group(1).strip()).strip()

def core(w):  # word without surrounding punctuation
    return re.sub(r"^\W+|\W+$", "", w)

def expand(word):
    c = core(word)
    return (word.replace(c, RESPELL[c]) if c in RESPELL else word).split()

def regroup(lines, counts, toks):
    """merge respelled TTS tokens back into the ORIGINAL script words (times span the merged tokens)"""
    out, i = [], 0
    for (f, text), cnt in zip(lines, counts):
        words = []
        for sw, n in zip(text.split(), cnt):
            grp = toks[i:i + n]; i += n
            words.append([sw, grp[0][1], grp[-1][2]])
        out.append((f, words))
    assert i == len(toks), f"token mismatch {i} vs {len(toks)} (respell map vs TTS tokenisation)"
    return out

if "--selftest" in args:   # offline: no API, no key needed
    RESPELL.update({"ShopOS": "Shop O S"})
    L = [(1, "This is ShopOS. Ask now.")]
    C = [[len(expand(w)) for w in t.split()] for f, t in L]
    T = [["This", 0, .2], ["is", .2, .3], ["Shop", .3, .5], ["O", .5, .6], ["S.", .6, .8], ["Ask", 1, 1.2], ["now.", 1.2, 1.4]]
    R = regroup(L, C, T)
    assert [w[0] for w in R[0][1]] == ["This", "is", "ShopOS.", "Ask", "now."], R
    assert R[0][1][2][1:] == [.3, .8], R
    print("selftest ok: respelled tokens merge back to 'ShopOS.' spanning 0.3-0.8s"); sys.exit(0)

# ---- TTS text (respelled) and per-script-word token counts
tts_lines, counts = [], []
for f, t in lines:
    toks, cnt = [], []
    for w in t.split():
        e = expand(w); toks += e; cnt.append(len(e))
    tts_lines.append((f, " ".join(toks))); counts.append(cnt)
full = " ".join(t for _, t in tts_lines)
print("chars:", len(full))

KEY = os.environ["ELEVENLABS_API_KEY"]
body = json.dumps({"text": full, "model_id": V.get("model", "eleven_multilingual_v2"),
                   "voice_settings": V.get("settings", {"stability": 0.45, "similarity_boost": 0.75, "style": 0.15})}).encode()
req = urllib.request.Request(
    f"https://api.elevenlabs.io/v1/text-to-speech/{V['id']}/with-timestamps?output_format=mp3_44100_128",
    data=body, headers={"xi-api-key": KEY, "Content-Type": "application/json"})
resp = json.load(urllib.request.urlopen(req, timeout=180))
os.makedirs(os.path.join(ROOT, "assets", "vo"), exist_ok=True)
NAME = V.get("name", "voice")
full_mp3 = os.path.join(ROOT, "assets", "vo", f"vo_full_{NAME}.mp3")
open(full_mp3, "wb").write(base64.b64decode(resp["audio_base64"]))

# ---- char alignment -> tokens (global times)
al = resp["alignment"]
toks, w, ws, we = [], "", None, None
for c, s, e in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
    if c.isspace():
        if w: toks.append([w, ws, we]); w, ws = "", None
        continue
    if not w: ws = s
    w += c; we = e
if w: toks.append([w, ws, we])

out = regroup(lines, counts, toks)

total = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", full_mp3]))
cuts = [0.0] + [(a[1][-1][2] + b[1][0][1]) / 2 for a, b in zip(out, out[1:])] + [total]
voices = []
for idx, (f, ws_) in enumerate(out):
    a, b = cuts[idx], cuts[idx + 1]
    clip = os.path.join(ROOT, "assets", "vo", f"vo_{f:02d}.mp3")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", full_mp3, "-ss", f"{a:.4f}", "-to", f"{b:.4f}", "-c:a", "libmp3lame", "-b:a", "128k", clip])
    voices.append({"frame": f, "path": f"assets/vo/vo_{f:02d}.mp3", "duration_s": round(b - a, 3),
                   "words": [{"id": f"w{j}", "text": w_[0], "start": round(w_[1] - a, 3), "end": round(w_[2] - a, 3)} for j, w_ in enumerate(ws_)]})

meta_path = os.path.join(ROOT, "audio_meta.json")
old = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
meta = {"bgm": old.get("bgm"), "bgm_pending": False, "voices": voices, "sfx": old.get("sfx", [])}
json.dump(meta, open(meta_path, "w"), indent=2)
json.dump({"voice_id": V["id"], "name": NAME, "total_s": total, "cuts": cuts, "global_words": [[f, w_] for f, ws_ in out for w_ in ws_]},
          open(os.path.join(ROOT, "assets", "vo", f"vo_full_{NAME}.words.json"), "w"), indent=1)

# ---- last-word loudness check (end-of-utterance decay): the final word of the WHOLE take vs a mid-take reference
def peak(a, b):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(a), "-to", str(b), "-i", full_mp3, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"max_volume: ([-\d.]+) dB", r); return float(m.group(1)) if m else None
lastw = out[-1][1][-1]; ref = out[0][1][len(out[0][1]) // 2]
pl, pr = peak(lastw[1], lastw[2]), peak(ref[1], ref[2])
print(f"total {total:.2f}s | last word '{lastw[0]}' peak {pl} dB vs reference '{ref[0]}' {pr} dB", "" if pl is None or pr is None or pr - pl < 15 else "  <-- WARNING: last word >=15 dB quieter; respell/re-roll it")
for v in voices:
    print(f"frame {v['frame']:>2}: {v['duration_s']:5.2f}s  first '{v['words'][0]['text']}' @ {v['words'][0]['start']:.2f}  last '{v['words'][-1]['text']}' ends {v['words'][-1]['end']:.2f}")
