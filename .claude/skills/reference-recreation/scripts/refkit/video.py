"""Frame access through ffmpeg pipes."""
import json
import subprocess

import numpy as np


def probe(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_frames,duration", "-of", "json", path],
                       capture_output=True, text=True).stdout
    s = json.loads(o)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    fps = int(n) / int(d)
    nb = int(s["nb_frames"]) if str(s.get("nb_frames", "")).isdigit() else int(round(float(s["duration"]) * fps))
    return dict(width=int(s["width"]), height=int(s["height"]), fps=fps, frames=nb)


def iter_frames(path, a=0, b=None, step=1, chunk=16, info=None):
    """yield (frame_number, HxWx3 uint8) for a..b (inclusive); step>1 keeps every step-th frame (decodes everything up to b)."""
    info = info or probe(path)
    W, H = info["width"], info["height"]
    sel = "gte(n,%d)" % a
    if b is not None:
        sel += "*lte(n,%d)" % b
    if step > 1:
        sel += "*not(mod(n-%d,%d))" % (a, step)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", "select='%s'" % sel, "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    fsz = W * H * 3
    n = 0
    while True:
        buf = p.stdout.read(fsz * chunk)
        if not buf:
            break
        k = len(buf) // fsz
        arr = np.frombuffer(buf[:k * fsz], np.uint8).reshape(k, H, W, 3)
        for i in range(k):
            yield a + (n + i) * step, arr[i]
        n += k
    p.stdout.close()
    p.wait()


def read_frame(path, n, info=None):
    for f, fr in iter_frames(path, n, n, info=info):
        return fr.copy()
    raise IndexError(n)


def small_series(path, info=None, w=270, h=152):
    """(gray frames small, per-frame border median colour) for cut detection; one pass."""
    info = info or probe(path)
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=%d:%d" % (w, h), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    a = np.frombuffer(p, np.uint8).reshape(-1, h, w, 3)
    gray = a.astype(np.float32).mean(axis=3)
    ring = np.concatenate([a[:, :3].reshape(len(a), -1, 3), a[:, -3:].reshape(len(a), -1, 3), a[:, :, :3].reshape(len(a), -1, 3), a[:, :, -3:].reshape(len(a), -1, 3)], axis=1)
    border = np.median(ring, axis=1)
    return gray, border
