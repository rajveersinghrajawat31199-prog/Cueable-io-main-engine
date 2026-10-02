#!/usr/bin/env python3
"""video-critique: objective review of a RENDERED video (mp4) against its HyperFrames project.
usage: critique.py <render.mp4> [--project DIR] [--words words.json] [--moments moments.json] [--allow-edge] [--no-sheets]
Exit code 1 if any FAIL. Prints PASS/WARN/FAIL lines and writes contact sheets to <project>/snapshots/.
It measures; it cannot hear or judge taste. Always also LOOK at the sheets (see references/visual-review.md)."""
import sys, re, json, os, subprocess, argparse, math, numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("mp4"); ap.add_argument("--project", default="."); ap.add_argument("--words"); ap.add_argument("--moments")
ap.add_argument("--allow-edge", action="store_true"); ap.add_argument("--no-sheets", action="store_true")
args = ap.parse_args()
mp4 = os.path.abspath(args.mp4); os.chdir(args.project)
SR, FPS = 44100, 15
issues = {"FAIL": 0, "WARN": 0}
def say(level, msg):
    if level in issues: issues[level] += 1
    print(f"[{level}] {msg}")
db = lambda x: 20*np.log10(max(float(x), 1e-9))
def rms_db(x): return db(np.sqrt((x.astype(np.float64)**2).mean())) if len(x) else -99.0
def decode(path):
    raw = subprocess.run(["ffmpeg","-v","error","-i",path,"-vn","-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True,check=True).stdout
    return np.frombuffer(raw, np.float32)

# ---------- audio ----------
mix = decode(mp4); dur = len(mix)/SR
html = open("index.html").read()
tracks = {"vo": np.zeros(len(mix), np.float32), "music": np.zeros(len(mix), np.float32), "sfx": np.zeros(len(mix), np.float32)}
cues, n_by_kind = [], {"vo": 0, "music": 0, "sfx": 0}
def kind(id_, src):
    s = (id_ + " " + src).lower()
    if re.search(r"(?<![a-z])(bgm|music|score)(?![a-z])", s): return "music"
    if re.search(r"(?<![a-z])(vo|voice|narr\w*|dialogue)(?![a-z])", s): return "vo"
    return "sfx"
vo_starts = []
for t in re.findall(r"<audio\b([^>]*)>", html):
    a = dict(re.findall(r'([\w-]+)="([^"]*)"', t))
    if "src" not in a or not os.path.exists(a["src"]): continue
    x = decode(a["src"]); x = x[int(float(a.get("data-media-start", 0))*SR):]
    if "data-duration" in a: x = x[:int(float(a["data-duration"])*SR)]
    st, vol = float(a.get("data-start", 0)), float(a.get("data-volume", 1))
    k = kind(a.get("id", ""), a["src"]); n_by_kind[k] += 1
    i = int(st*SR); n = max(0, min(len(x), len(mix)-i))
    tracks[k][i:i+n] += x[:n]*vol
    if k == "sfx": cues.append((a.get("id", a["src"]), st, len(x)/SR, x, vol))
    if k == "vo": vo_starts.append(st)
vo, music, sfx = tracks["vo"], tracks["music"], tracks["sfx"]
print(f"{os.path.basename(mp4)}: {dur:.2f}s | voice clips {n_by_kind['vo']}, music {n_by_kind['music']}, sfx cues {n_by_kind['sfx']}")

win = int(0.05*SR)
def env_db(x): return 20*np.log10(np.sqrt(np.convolve(x.astype(np.float64)**2, np.ones(win)/win, mode="same"))+1e-9)
speech_start = speech_end = None; onsets = None
if n_by_kind["vo"]:
    e = env_db(vo); voiced = e > -45; idx = np.where(voiced)[0]
    if len(idx): speech_start, speech_end = idx[0]/SR, idx[-1]/SR
    # energy-derived speech onsets: a voiced run that follows >= 0.12s of quiet
    on, quiet_run = [], 0
    for i in range(0, len(voiced), win//2):
        if voiced[i]:
            if quiet_run >= 0.12*SR/(win//2) or not on: on.append(i/SR)
            quiet_run = 0
        else: quiet_run += 1
    onsets = np.array(on)
    wf = args.words or next((p for p in ["assets/vo/vo-words.json", "transcript.json"] if os.path.exists(p)), None)
    if wf and len(vo_starts) == 1:
        W = json.load(open(wf)); W = W["words"] if isinstance(W, dict) and "words" in W else W
        onsets = np.array([float(w["start"]) + vo_starts[0] for w in W])
if speech_start is not None:
    print(f"speech {speech_start:.2f}-{speech_end:.2f}s")
else: say("WARN", "no voice track found: voice/gap/sync checks skipped")

head = (vo + sfx)[:int(0.12*SR)]
if rms_db(head) > -45: say("FAIL", f"abrupt opening: voice/SFX already at {rms_db(head):.1f} dBFS in the first 120 ms")
else: say("PASS", "opening is clean (no voice/SFX hit in the first 120 ms)")
if cues and speech_start is not None:
    first = min(c[1] for c in cues)
    if first < speech_start-0.25: say("WARN", f"first SFX at {first:.2f}s plays before the first spoken word ({speech_start:.2f}s)")
if speech_start is not None:
    e = env_db(vo); quiet = e < -48; gaps, s = [], None
    for i in range(int(speech_start*SR), int(speech_end*SR)):
        if quiet[i] and s is None: s = i
        if (not quiet[i]) and s is not None:
            if (i-s)/SR > 0.45: gaps.append((s/SR, i/SR))
            s = None
    for a, b in gaps: say("WARN", f"voice gap {a:.2f}-{b:.2f}s ({b-a:.2f}s of silence inside the speech)")
    if not gaps: say("PASS", "no voice gap longer than 0.45s (a natural sentence pause is ~0.3s)")
    hold = dur - speech_end
    say("PASS" if hold < 2.2 else "WARN", f"hold after the last word: {hold:.2f}s (want < 2.2s)")

bad = 0
for id_, st, d, x, vol in cues:
    pk = db(np.abs(x).max()*vol); lo, hi = int(max(0, st-0.1)*SR), int((st+d+0.1)*SR)
    vpk = db(np.abs(vo[lo:hi]).max()) if hi > lo and n_by_kind["vo"] else -99
    if pk > -9: say("WARN", f"{id_} @ {st:.2f}s peaks at {pk:.1f} dBFS (want <= -9)"); bad += 1
    elif vpk > -40 and pk - vpk > -8: say("WARN", f"{id_} @ {st:.2f}s only {abs(pk-vpk):.1f} dB under the voice (want >= 8)"); bad += 1
if cues and not bad: say("PASS", "every SFX cue sits >= 8 dB under the voice and <= -9 dBFS")
if cues:
    ss = sorted(c[1] for c in cues); dens = max(sum(1 for t in ss if a <= t < a+1.0) for a in np.arange(0, dur, 0.25))
    say("PASS" if dens <= 5 else "WARN", f"peak SFX density {dens} cues in any 1s window (want <= 5)")

if n_by_kind["music"] and speech_start is not None:
    m_env, seg = env_db(music), slice(int(speech_start*SR), int(speech_end*SR))
    rel = rms_db(music[seg]) - rms_db(vo[seg])
    say("PASS" if -18 <= rel <= -9 else "WARN", f"music bed is {abs(rel):.1f} dB under the voice on average (want 9-18 dB; louder masks speech, quieter is inaudible)")
    live = (m_env > -50).mean()
    say("PASS" if live > 0.9 else "WARN", f"music covers {live*100:.0f}% of the video (want >= 90%)")
    a, b = rms_db(music[int(0.5*SR):int(2*SR)]), rms_db(music[-int(0.4*SR):])
    say("PASS" if b < a-6 else "WARN", f"music tail is {a-b:.1f} dB below its opening (want a fade-out >= 6 dB)")
    bgm_on = music[:int(0.12*SR)]
    say("WARN" if rms_db(bgm_on) > -44 else "PASS", f"music level in the first 120 ms is {rms_db(bgm_on):.1f} dBFS (want <= -44: fade it in, do not start at full level)")

ebur = subprocess.run(["ffmpeg","-nostats","-i",mp4,"-af","ebur128=peak=true","-f","null","-"],capture_output=True,text=True).stderr
I = re.findall(r"I:\s+(-?[\d.]+) LUFS", ebur); P = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebur)
if I and P: say("PASS" if -20 <= float(I[-1]) <= -12 and float(P[-1]) <= -0.5 else "WARN", f"loudness {I[-1]} LUFS, true peak {P[-1]} dBFS (want -20..-12 LUFS, peak <= -1)")

# ---------- video ----------
vraw = subprocess.run(["ffmpeg","-v","error","-i",mp4,"-vf",f"fps={FPS},scale=320:180,format=gray","-f","rawvideo","-"],capture_output=True,check=True).stdout
F = np.frombuffer(vraw, np.uint8).reshape(-1, 180, 320).astype(np.float32)
D = np.abs(np.diff(F, axis=0)); tot = D.mean(axis=(1, 2)); L = D[:, :, :160].mean(axis=(1, 2)); R = D[:, :, 160:].mean(axis=(1, 2))
act = (D > 12).sum(axis=(1, 2)); t_of = lambda i: (i+1)/FPS
runs, s = [], None
for i, v in enumerate(act < 25):
    if v and s is None: s = i
    if (not v or i == len(act)-1) and s is not None:
        e = i if not v else i+1
        if (e-s)/FPS >= 0.7: runs.append((t_of(s), t_of(e-1)))
        s = None
for a, b in runs:
    inside = speech_end is None or a < speech_end
    say("WARN" if inside else "PASS", f"static screen {a:.2f}-{b:.2f}s ({b-a:.2f}s with no visible motion){'' if inside else ' (after the voice: ok)'}")
if not runs: say("PASS", "no static stretch longer than 0.7s")
fa = next((t_of(i) for i in range(len(act)) if act[i] >= 25), None)
if fa is not None and speech_start is not None and fa - speech_start > 0.3: say("WARN", f"first visible motion at {fa:.2f}s but the voice starts at {speech_start:.2f}s")

if onsets is not None and len(onsets):
    for c in [t_of(i) for i in np.where(tot > 12)[0]]:
        d = onsets - c; j = np.argmin(np.abs(d)); lead = d[j]
        say("PASS" if -0.05 <= lead <= 0.25 else "WARN", f"hard cut at {c:.2f}s is {lead*1000:+.0f} ms ahead of the nearest speech onset (want -50..+250 ms: on or just before the voice)")
for id_, st, d_, x, vol in cues:
    if re.search(r"whoosh|swipe|slide|tick|confirm|blink|riser|sweep|swell|ambien", id_.lower()): continue
    a, b = int(max(0, st-0.08)*FPS), int((st+0.20)*FPS)+1
    if b > a and act[a:b].max() < 25: say("WARN", f"{id_} @ {st:.2f}s fires with nothing visibly changing (orphan SFX)")

def first_change(series, a, b, thr):
    for i in range(int(max(a, 0)*FPS), min(int(b*FPS), len(series))):
        if series[i] > thr: return t_of(i)
mf = args.moments or next((p for p in ["critique.moments.json", "scripts/sync_moments.json"] if os.path.exists(p)), None)
for p in (json.load(open(mf)) if mf else []):
    tl_, tr_ = first_change(L, p["t"]-0.3, p["t"]+1.0, 0.25), first_change(R, p["t"]-0.3, p["t"]+1.0, 0.25)
    if tl_ is None or tr_ is None: say("WARN", f"sync '{p['label']}': left side moves at {tl_}, right side at {tr_} (one never moved)"); continue
    gap = tr_-tl_; say("PASS" if abs(gap) <= 0.15 else "FAIL", f"sync '{p['label']}': left {tl_:.2f}s, right {tr_:.2f}s (offset {gap*1000:+.0f} ms, want within 150)")

if not args.allow_edge:
    bands = {"bottom": lambda f: f[-3:, :], "top": lambda f: f[:3, :], "left": lambda f: f[:, :3], "right": lambda f: f[:, -3:]}
    for side, get in bands.items():
        flags = []
        for f in F[::3]:
            bg = np.bincount(f.astype(np.uint8).ravel(), minlength=256).argmax()
            flags.append((np.abs(get(f) - bg) > 40).mean() > 0.03)
        i = 0
        while i < len(flags):
            if flags[i]:
                j = i
                while j+1 < len(flags) and flags[j+1]: j += 1
                if (j-i+1)*3/FPS >= 0.5: say("WARN", f"content touches the {side} edge {i*3/FPS:.2f}-{(j+1)*3/FPS:.2f}s (cropped or off-screen? pass --allow-edge if full-bleed is intended)")
                i = j+1
            else: i += 1

if not args.no_sheets:
    os.makedirs("snapshots", exist_ok=True); n = math.ceil(dur/12)
    for k in range(n):
        subprocess.run(["ffmpeg","-y","-v","error","-ss",str(k*12),"-t","12","-i",mp4,"-vf","fps=2,scale=480:270,tile=4x6","-frames:v","1",f"snapshots/critique-sheet-{k+1}.png"])
    print(f"contact sheets: snapshots/critique-sheet-1..{n}.png (0.5s per cell, 12s per sheet). LOOK at them.")
print(f"\nSUMMARY: {issues['FAIL']} FAIL, {issues['WARN']} WARN")
sys.exit(1 if issues["FAIL"] else 0)
