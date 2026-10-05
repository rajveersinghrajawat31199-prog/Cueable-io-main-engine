"""Pointer-sprite tracking: scale-aware template match of an outline mask (dark) and a fill mask (white). Sprites live in sprites/*.npz and are learned once from
one frame with a hint (learn_sprite). No model calls."""
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.signal import fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
SPRITES = os.path.join(HERE, "sprites")


def learn_sprite(fr, tip_x, tip_y, name, box=(-20, -6, 40, 52), dark=95, white=200):
    """cut a clean cursor sprite out of one frame (the cursor over a plain area) around its fingertip/arrow tip and store outline + fill masks."""
    g = fr.astype(np.float32).dot(np.array([0.299, 0.587, 0.114], np.float32))
    x0, y0, x1, y1 = tip_x + box[0], tip_y + box[1], tip_x + box[2], tip_y + box[3]
    cg = g[y0:y1, x0:x1]
    d = cg < dark
    lab, n = ndi.label(d, structure=np.ones((3, 3)))
    if n == 0:
        raise ValueError("no dark outline near the hint")
    areas = ndi.sum(d, lab, range(1, n + 1))
    big = int(np.argmax(areas)) + 1                                  # the outline is the biggest dark piece
    keep = (lab == big)
    sil = ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=2))
    d_all = d & ndi.binary_dilation(sil, iterations=1)               # outline + creases inside the silhouette
    fill = ndi.binary_erosion(sil & ~d_all & (cg > white), iterations=1)
    ys, xs = np.where(sil)
    sx0, sy0, sx1, sy1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    os.makedirs(SPRITES, exist_ok=True)
    np.savez_compressed(os.path.join(SPRITES, name + ".npz"), outline=d_all[sy0:sy1, sx0:sx1], fill=fill[sy0:sy1, sx0:sx1], tip=np.array([tip_x - x0 - sx0, tip_y - y0 - sy0], float))
    return name


def load_sprite(name):
    z = np.load(os.path.join(SPRITES, name + ".npz"))
    return dict(outline=z["outline"].astype(np.float32), fill=z["fill"].astype(np.float32), tip=z["tip"].astype(float), name=name)


def available():
    return sorted(f[:-4] for f in os.listdir(SPRITES) if f.endswith(".npz")) if os.path.isdir(SPRITES) else []


def _resize(m, s):
    h, w = m.shape
    nw, nh = max(3, int(round(w * s))), max(3, int(round(h * s)))
    return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS), np.float32) / 255.0


class CursorTracker:
    def __init__(self, sprite, scales=(0.42, 0.5, 0.6, 0.72, 0.86, 1.0, 1.2), accept=0.6, keep=0.55):
        self.sp, self.scales, self.accept, self.keep = sprite, scales, accept, keep
        self.cache = {}
        self.pos = None          # (tip_x, tip_y, scale)
        self.lost = 99
        self.fresh = False       # True on the frame the cursor was (re)acquired
        self.track = []          # (frame, tip_x, tip_y, scale, score)

    def _tpl(self, s):
        k = round(s, 3)
        if k not in self.cache:
            o, f = _resize(self.sp["outline"], s), _resize(self.sp["fill"], s)
            sil = np.maximum(o, f) > 0.2
            ring = ndi.binary_dilation(sil, iterations=3) & ~ndi.binary_dilation(sil, iterations=1)
            ring = ring.astype(np.float32)
            tg = np.where(o > 0.5, 25.0, np.where(f > 0.5, 240.0, np.nan)).astype(np.float32)
            self.cache[k] = (o, f, self.sp["tip"] * s, max(o.sum(), 1.0), max(f.sum(), 1.0), ring, max(ring.sum(), 1.0), tg)
        return self.cache[k]

    def _score(self, g, s, region):
        """best (score, tip_x, tip_y) at scale s inside region=(x0,y0,x1,y1) of gray image g."""
        o, f, tip, no, nf, ring, nr, tg = self._tpl(s)
        x0, y0, x1, y1 = region
        sub = g[y0:y1, x0:x1]
        if sub.shape[0] < o.shape[0] + 2 or sub.shape[1] < o.shape[1] + 2:
            return 0.0, 0, 0
        dthr = 95 if s >= 0.8 else 140
        D = (sub < dthr).astype(np.float32)
        Wm = (sub > 225).astype(np.float32)
        sc = np.minimum(fftconvolve(D, o[::-1, ::-1], mode="valid") / no, fftconvolve(Wm, f[::-1, ::-1], mode="valid") / nf)
        dark_ring = fftconvolve((sub < 110).astype(np.float32), ring[::-1, ::-1], mode="valid") / nr      # a real pointer sits on a mostly non-dark surround
        sc = sc * np.clip(1.0 - np.maximum(0.0, dark_ring - 0.6) * 2.5, 0.0, 1.0)
        i = np.unravel_index(int(np.argmax(sc)), sc.shape)
        return float(sc[i]), x0 + i[1] + tip[0], y0 + i[0] + tip[1]

    def ncc(self, g, x, y, s):
        """normalised correlation of the grey patch with the sprite (outline dark, fill light) over the sprite's own pixels: a shape check the mask scores cannot give."""
        o, f, tip, no, nf, ring, nr, tg = self._tpl(s)
        x0, y0 = int(round(x - tip[0])), int(round(y - tip[1]))
        h, w = tg.shape
        H, W = g.shape
        if x0 < 0 or y0 < 0 or x0 + w > W or y0 + h > H:
            return 0.0
        m = ~np.isnan(tg)
        a = g[y0:y0 + h, x0:x0 + w][m]
        b = tg[m]
        if a.std() < 1e-3:
            return 0.0
        return float(np.corrcoef(a, b)[0, 1])

    def _local(self, g, cx, cy, s0, rad, scales):
        H, W = g.shape
        best = (0.0, cx, cy, s0)
        for s in scales:
            o, f, tip, no, nf, ring, nr, tg = self._tpl(s)
            reg = (int(max(0, cx - tip[0] - rad)), int(max(0, cy - tip[1] - rad)), int(min(W, cx - tip[0] + o.shape[1] + rad)), int(min(H, cy - tip[1] + o.shape[0] + rad)))
            sc, x, y = self._score(g, s, reg)
            if sc > best[0]:
                best = (sc, x, y, s)
        return best

    def update(self, f, g, scan_every=2):
        """g: full-res gray (HxW float32). Returns (tip_x, tip_y, scale, score) or None."""
        res = None
        self.fresh = False
        if self.pos is not None and self.lost <= 3:
            x, y, s = self.pos
            sc, nx, ny, ns = self._local(g, x, y, s, 40 + 30 * self.lost, [s * 0.88, s, s * 1.14])
            disp = float(np.hypot(nx - x, ny - y))
            held = (sc >= 0.45 and disp <= 25 or sc >= 0.38 and disp <= 10) and abs(ns / s - 1) <= 0.12      # a parked pointer on busy content scores lower: trust position continuity
            nc = self.ncc(g, nx, ny, ns) if (sc >= 0.38) else 0.0
            if (sc >= self.keep and nc >= 0.45) or (held and nc >= 0.35):
                res = (nx, ny, float(np.clip(ns, 0.3, 1.5)), sc)
        if res is None and (f % scan_every == 0 or self.lost <= 3):
            gh = g[::2, ::2]
            best = (0.0, 0, 0, 1.0)
            for s in self.scales:
                sc, x, y = self._score(gh, s * 0.5, (0, 0, gh.shape[1], gh.shape[0]))
                if sc - (0.08 if s < 0.6 else 0.0) > best[0] - (0.08 if best[3] < 0.6 else 0.0):
                    best = (sc, x * 2, y * 2, s)
            if best[0] >= (0.5 if best[3] < 0.6 else self.accept - 0.04):
                sc, nx, ny, ns = self._local(g, best[1], best[2], best[3], 14, [best[3] * 0.9, best[3], best[3] * 1.1])
                if sc >= (0.52 if ns < 0.6 else self.accept) and self.ncc(g, nx, ny, ns) >= 0.5:
                    res = (nx, ny, ns, sc)
        if res is None:
            self.lost += 1
            return None
        self.fresh = self.lost > 3
        self.lost = 0
        self.pos = res[:3]
        self.track.append((f,) + tuple(round(float(v), 2) for v in res))
        return res

    def back_fill(self, f, g, nxt):
        """try frame f (before the acquisition frame) with the next frame's pose as the prior; returns the pose and stores it, or None."""
        x, y, s = nxt[:3]
        sc, nx, ny, ns = self._local(g, x, y, s, 70, [s * 0.88, s, s * 1.14])
        if sc >= self.keep and self.ncc(g, nx, ny, ns) >= 0.45:
            r = (nx, ny, float(np.clip(ns, 0.3, 1.5)), sc)
            self.track.append((f,) + tuple(round(float(v), 2) for v in r))
            return r
        return None

    def bbox(self, res, pad=3):
        x, y, s, _ = res
        o, f, tip, no, nf, ring, nr, tg = self._tpl(s)
        return (int(x - tip[0]) - pad, int(y - tip[1]) - pad, int(x - tip[0] + o.shape[1]) + pad, int(y - tip[1] + o.shape[0]) + pad)

    def clean(self, min_run=6, max_jump=140):
        """drop detection runs that cannot be a pointer: shorter than min_run frames, or jumping more than max_jump px per frame."""
        self.track.sort(key=lambda t: t[0])
        runs, cur_ = [], []
        for t in self.track:
            if cur_ and (t[0] - cur_[-1][0] > 3 or float(np.hypot(t[1] - cur_[-1][1], t[2] - cur_[-1][2])) > max_jump * max(1, t[0] - cur_[-1][0])):
                runs.append(cur_)
                cur_ = []
            cur_.append(t)
        if cur_:
            runs.append(cur_)
        keep_ = [r for r in runs if len(r) >= min_run and (float(np.median([t[4] for t in r])) >= 0.62 or len(r) >= 40)]
        self.track = [t for r in keep_ for t in r]
        return self.track

    def presses(self, drop=0.12):
        """frames where the scale dips by >= drop below its running median (a click squashes the pointer)."""
        self.track.sort(key=lambda t: t[0])
        if len(self.track) < 8:
            return []
        fr = np.array([t[0] for t in self.track]); sc = np.array([t[3] for t in self.track])
        med = ndi.median_filter(sc, size=15, mode="nearest")
        dip = sc < med * (1 - drop)
        out, i = [], 0
        while i < len(dip):
            if dip[i]:
                j = i
                while j + 1 < len(dip) and dip[j + 1] and fr[j + 1] - fr[j] <= 2:
                    j += 1
                if j - i + 1 >= 2:
                    out.append([int(fr[i]), int(fr[j])])
                i = j + 1
            else:
                i += 1
        return out
