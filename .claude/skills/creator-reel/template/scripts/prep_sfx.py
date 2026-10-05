#!/usr/bin/env python3
"""Prepare the soft WORD-ACCENT sounds (creator reels use no whooshes or transition sounds: rejected three times by the user).
Decode, trim leading silence, peak-normalise to -3 dBFS, write assets/sfx/<role>.wav + _meta.json. Roles used by build.py:
pop, click, select, tick, up, slide. A role's source is assets/sfx/picks/<role>.(mp3|wav|ogg) if the user picked it from the sampler
(videos/hyrox-creator-reel/sfx-sampler), else the library default below."""
import glob
import json
import os
import subprocess
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.expanduser("~/hyperframes-assets/sfx/")
S6 = "sonniss-gdc/2024/Sonniss.com-GDC2024-GameAudioBundle6of9/Rogue Waves - Kawaii UI/"
S1 = "sonniss-gdc/2024/Sonniss.com-GDC2024-GameAudioBundle1of9/CB Sounddesign - Activation 2/"
DEFAULT = {
    "pop": LIB + S6 + "UIClick_Hand Pop UI Diminished 1_RogueWaves_KawaiiUI.wav",
    "click": LIB + S1 + "UIClick_UI Click 33_CB Sounddesign_ACTIVATION2.wav",
    "up": LIB + S1 + "UIMisc_Feedback 36 up_CB Sounddesign_ACTIVATION2.wav",
    "tick": LIB + "kenney/interface-sounds/Audio/click_001.ogg",
    "select": LIB + "kenney/interface-sounds/Audio/select_003.ogg",
    "slide": LIB + "kenney/casino-audio/Audio/card-slide-1.ogg",
}
SR = 48000
out_dir = os.path.join(ROOT, "assets", "sfx")
os.makedirs(out_dir, exist_ok=True)
meta = {}
for role, default in DEFAULT.items():
    picks = glob.glob(os.path.join(out_dir, "picks", role + ".*"))
    src = picks[0] if picks else default
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
    amp = np.abs(x).max(1)
    x = x[max(int(np.argmax(amp > 0.02 * amp.max())) - int(0.004 * SR), 0):]
    x = x / (np.abs(x).max() + 1e-9) * (10 ** (-3 / 20))
    n = min(int(0.01 * SR), len(x))
    x[-n:] *= np.linspace(1, 0, n)[:, None]
    env = np.convolve(np.abs(x).max(1), np.ones(int(0.02 * SR)) / int(0.02 * SR), mode="same")
    meta[role] = dict(dur=round(len(x) / SR, 3), apex=round(float(np.argmax(env)) / SR, 3))
    with wave.open(os.path.join(out_dir, role + ".wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    print("%-7s %.2fs  <- %s" % (role, meta[role]["dur"], os.path.basename(src)))
json.dump(meta, open(os.path.join(out_dir, "_meta.json"), "w"), indent=1)
