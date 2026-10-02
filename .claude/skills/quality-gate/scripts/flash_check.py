#!/usr/bin/env python3
"""Flash / strobe detector. Finds whole-frame brightness PULSES: mean luma jumps up within one frame and falls back within ~0.5 s.
A scene cut is a step that stays; a pulse comes back. Any such pulse that nobody asked for is a defect (customers see it as a 'white flash').
usage: flash_check.py <video> [--json]   exit 1 if any pulse. Also imported by machine_scores.py (axis 'flashes').
Fixed thresholds on purpose: rise >= 2.5 luma levels (0-255) in <= 2 frames at 30 fps, returning to <= 40% of the rise within 15 frames,
AND uniform: >= 75% of pixels brighten (a white overlay brightens everything; a card or swatch entering only changes a region)."""
import json, subprocess, sys
import numpy as np

def find_flashes(video, fps=30, rise_thr=2.5, back_frames=15):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps={fps},scale=160:90,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 90, 160).astype(np.float32); L = f.mean((1, 2)); out = []; i = 2
    while i < len(L) - 1:
        rise = L[i] - L[max(0, i - 2)]
        if rise >= rise_thr:
            base = L[max(0, i - 2)]; peak_i = i + int(np.argmax(L[i:i + 3])); peak = L[peak_i]
            tail = L[peak_i + 1: peak_i + 1 + back_frames]
            if len(tail) and tail.min() <= base + 0.4 * (peak - base):           # it came back: a pulse, not a cut
                uniform = float(((f[peak_i] - f[max(0, i - 2)]) >= 1.0).mean())   # share of pixels that brightened
                if uniform >= 0.75:
                    out.append({"t": round(peak_i / fps, 2), "rise": round(float(peak - base), 1), "base": round(float(base), 1), "uniform": round(uniform, 2)}); i = peak_i + back_frames; continue
        i += 1
    return out

if __name__ == "__main__":
    ev = find_flashes(sys.argv[1])
    if "--json" in sys.argv: print(json.dumps(ev))
    else:
        print(f"{len(ev)} brightness pulse(s)" + ("" if not ev else ": " + ", ".join(f"{e['t']}s (+{e['rise']} on {e['base']})" for e in ev[:40])))
    sys.exit(1 if ev else 0)
