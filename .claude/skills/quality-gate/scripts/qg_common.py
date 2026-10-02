"""Shared helpers for the quality-gate scripts (frame loading, activity metric, score curves)."""
import json, os, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RUBRIC = os.path.join(HERE, "..", "rubric")

def probe(video):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,r_frame_rate,width,height,duration", "-of", "json", video], capture_output=True, text=True).stdout
    streams = json.loads(o)["streams"]
    v = next(s for s in streams if s["codec_type"] == "video")
    n, d = v["r_frame_rate"].split("/")
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": float(n) / float(d), "dur": float(v.get("duration") or 0), "audio": any(s["codec_type"] == "audio" for s in streams)}

def load_gray(video, width=216):
    """All frames as float32 gray at `width` px wide (aspect preserved). Returns (F[n,h,w], fps, info)."""
    info = probe(video); w = width; h = int(round(width * info["h"] / info["w"])) // 2 * 2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"scale={w}:{h}:flags=area,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32), info["fps"], info

def activity(F, fps):
    """Per-step change measured over 1/30 s so thresholds do not depend on the render fps.
    Returns (frac, mean): fraction of pixels visibly changing (|d|>12), and mean abs change."""
    K = max(1, int(round(fps / 30)))
    D = np.abs(F[K:] - F[:-K]); px = F.shape[1] * F.shape[2]
    return (D > 12).sum(axis=(1, 2)) / px, D.mean(axis=(1, 2))

def curve(x, pts):
    """Piecewise-linear score curve: pts = [[x0, s0], [x1, s1], ...] (any monotone direction); clamps outside."""
    pts = sorted(pts, key=lambda p: p[0])
    if x <= pts[0][0]: return float(pts[0][1])
    if x >= pts[-1][0]: return float(pts[-1][1])
    for (a, sa), (b, sb) in zip(pts, pts[1:]):
        if a <= x <= b: return float(sa + (sb - sa) * (x - a) / (b - a))

def load_profile(name):
    p = os.path.join(RUBRIC, "profiles", name + ".json")
    if not os.path.exists(p): raise SystemExit(f"no profile '{name}' in {os.path.join(RUBRIC, 'profiles')}")
    base = json.load(open(os.path.join(RUBRIC, "profiles", "default.json")))
    prof = json.load(open(p))
    if name != "default":
        m = dict(base.get("machine", {})); m.update(prof.get("machine", {})); base.update(prof); base["machine"] = m
        return base
    return prof

def load_json(p, default=None):
    return json.load(open(p)) if os.path.exists(p) else default
