"""Per-frame component detection (flat colour regions, textured photo regions, dark ink lines) and a small multi-object tracker."""
import math

import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import linear_sum_assignment

S8 = np.ones((3, 3), bool)
LUM = np.array([0.299, 0.587, 0.114], np.float32)


def gray(fr):
    return fr.astype(np.float32).dot(LUM)


def _box(sl):
    return (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop)


def frame_bg(fr, patch=14):
    """background colour: the colour two or more corner patches agree on (a full-bleed card never covers all four corners); falls back to the first corner."""
    H, W = fr.shape[:2]
    cs = [np.median(fr[y:y + patch, x:x + patch].reshape(-1, 3), axis=0) for (y, x) in ((0, 0), (0, W - patch), (H - patch, 0), (H - patch, W - patch))]
    best, bn = cs[0], 0
    for c in cs:
        n = sum(1 for d in cs if np.abs(d - c).max() <= 4)
        if n > bn:
            best, bn = c, n
    return tuple(int(v) for v in best)


def _corner_radius(lab, i, sl, H, W):
    """radius of the rounded corners of region i: walk the 45-degree diagonal from each unclipped bbox corner until the region starts (gap k px -> r = k*sqrt2/(sqrt2-1))."""
    y0, y1, x0, x1 = sl[0].start, sl[0].stop - 1, sl[1].start, sl[1].stop - 1
    rs = []
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        if cx in (0, W - 1) or cy in (0, H - 1):
            continue
        k = 0
        while k < 80 and 0 <= cx + dx * k < W and 0 <= cy + dy * k < H and lab[cy + dy * k, cx + dx * k] != i:
            k += 1
        if k < 80:
            rs.append(k * 1.4142 / 0.4142)
    return round(float(np.median(rs)), 1) if rs else None


def detect_regions(fr, bg, T=1.5, amin=150, std_max=3.5, grow=1):
    """flat colour regions without a palette: connected areas bounded by colour edges (on a 3x3 box-blurred copy, edge = step > T on any channel).
    A region is FLAT UI (card, pill, circle, band, button, window) when its colour barely varies (std <= std_max); gradients, photos and glows are left to detect_photo.
    Returns (detections, union mask of the accepted flat regions)."""
    I = ndi.uniform_filter(fr.astype(np.float32), size=(3, 3, 1))
    dx = np.abs(I[:, 1:] - I[:, :-1]).max(axis=2)
    dy = np.abs(I[1:] - I[:-1]).max(axis=2)
    H, W = fr.shape[:2]
    edge = np.zeros((H, W), bool)
    edge[:, 1:] |= dx > T
    edge[:, :-1] |= dx > T
    edge[1:] |= dy > T
    edge[:-1] |= dy > T
    lab, n = ndi.label(~edge)
    flat = lab.ravel()
    areas = np.bincount(flat, minlength=n + 1)
    ids = np.where(areas[1:] >= amin)[0] + 1
    if len(ids) == 0:
        return [], np.zeros((H, W), bool)
    objs = ndi.find_objects(lab)
    Iv = fr.astype(np.float64)
    s1 = [np.bincount(flat, weights=Iv[..., c].ravel(), minlength=n + 1) for c in range(3)]
    s2 = [np.bincount(flat, weights=(Iv[..., c] ** 2).ravel(), minlength=n + 1) for c in range(3)]
    keep = []
    out = []
    bgv = np.array(bg, float)
    for i in ids:
        a = areas[i]
        mean = np.array([s1[c][i] / a for c in range(3)])
        std = float(np.mean([math.sqrt(max(s2[c][i] / a - (s1[c][i] / a) ** 2, 0.0)) for c in range(3)]))
        if std > std_max:
            continue
        sl = objs[i - 1]
        touches = sl[0].start == 0 or sl[1].start == 0 or sl[0].stop == H or sl[1].stop == W
        if touches and np.abs(mean - bgv).max() <= 5:
            continue                                         # the background itself
        keep.append(i)
        x0, y0, x1, y1 = max(0, sl[1].start - grow), max(0, sl[0].start - grow), min(W, sl[1].stop + grow), min(H, sl[0].stop + grow)
        if x1 - x0 < 8 or y1 - y0 < 8:
            continue
        det = dict(cls="flat", c=0, box=(x0, y0, x1, y1), area=float(a), color=tuple(int(round(v)) for v in mean), std=round(std, 2))
        if a >= 1500:
            det["r"] = _corner_radius(lab, i, sl, H, W)
        out.append(det)
    union = np.isin(lab, keep) if keep else np.zeros((H, W), bool)
    return out, union


def detect_photo(fr, g, flat_union, bg, dist=14, cell=4, on_frac=0.35, amin_cells=156, min_dim_cells=10, fill_min=0.45):
    """non-flat, non-background regions (photos, footage, illustrations, globes, mosaics): far from the background colour, outside every flat colour,
    dense (text and thin lines are too sparse to count)."""
    H, W = g.shape
    far = np.abs(fr.astype(np.int16) - np.array(bg, np.int16)).max(axis=2) > dist
    mask = far & ~ndi.binary_dilation(flat_union, iterations=2)
    h4, w4 = H // cell, W // cell
    cells = mask[:h4 * cell, :w4 * cell].reshape(h4, cell, w4, cell).mean(axis=(1, 3)) >= on_frac
    cells = ndi.binary_closing(cells, structure=S8, iterations=1)
    lab, n = ndi.label(cells, structure=S8)
    out = []
    if n == 0:
        return out, mask
    areas = ndi.sum(cells, lab, range(1, n + 1))
    for k, sl in enumerate(ndi.find_objects(lab)):
        bw, bh = sl[1].stop - sl[1].start, sl[0].stop - sl[0].start
        if areas[k] < amin_cells or bw < min_dim_cells or bh < min_dim_cells or areas[k] < fill_min * bw * bh:
            continue
        x0, y0 = max(0, sl[1].start * cell - cell), max(0, sl[0].start * cell - cell)
        x1, y1 = min(W, sl[1].stop * cell + cell), min(H, sl[0].stop * cell + cell)
        sub = mask[y0:y1, x0:x1]
        rows = np.where(sub.sum(axis=1) >= 3)[0]
        cols = np.where(sub.sum(axis=0) >= 3)[0]
        if len(rows) == 0 or len(cols) == 0:
            continue
        out.append(dict(cls="photo", c=-1, box=(x0 + int(cols[0]), y0 + int(rows[0]), x0 + int(cols[-1]) + 1, y0 + int(rows[-1]) + 1), area=float(areas[k] * cell * cell)))
    return out, mask


def detect_ink(g, exclude, thr=120, amin=14):
    """dark glyph clusters (text lines, digits, icons) outside the excluded boxes."""
    ink = g < thr
    for (x0, y0, x1, y1) in exclude:
        ink[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = False
    d = ndi.maximum_filter1d(ndi.maximum_filter1d(ink.view(np.uint8), 15, axis=1), 3, axis=0).astype(bool)
    lab, n = ndi.label(d, structure=S8)
    out = []
    for k, sl in enumerate(ndi.find_objects(lab)):
        sub = ink[sl] & (lab[sl] == k + 1)
        a = int(sub.sum())
        if a < amin:
            continue
        ys, xs = np.where(sub)
        out.append(dict(cls="ink", c=-1, box=(sl[1].start + int(xs.min()), sl[0].start + int(ys.min()), sl[1].start + int(xs.max()) + 1, sl[0].start + int(ys.max()) + 1), area=float(a)))
    return out


def _geom(b):
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0, max(1.0, b[2] - b[0]), max(1.0, b[3] - b[1]))


class Tracker:
    """greedy-free multi-object tracker: Hungarian assignment per (class, colour) group with a constant-velocity prediction and a size term."""

    def __init__(self, gate=1.6, max_gap=2):
        self.gate, self.max_gap = gate, max_gap
        self.active, self.done, self.next_id = [], [], 0

    def _cost(self, tr, det, gap):
        pcx, pcy, pw, ph = tr["pred"](gap)
        dcx, dcy, dw, dh = _geom(det["box"])
        scale = max(30.0, 0.5 * (pw + ph))
        cost = math.hypot(dcx - pcx, dcy - pcy) / scale + 0.7 * (abs(math.log(dw / pw)) + abs(math.log(dh / ph)))
        if tr.get("color") is not None and det.get("color") is not None:
            cost += 0.9 * min(1.0, max(abs(a - b) for a, b in zip(tr["color"], det["color"])) / 70.0)
        return cost

    def update(self, f, dets):
        groups = {}
        for d in dets:
            groups.setdefault((d["cls"], d["c"]), []).append(d)
        trs = {}
        for t in self.active:
            trs.setdefault((t["cls"], t["c"]), []).append(t)
        matched = set()
        for key, ds in groups.items():
            ts = trs.get(key, [])
            if ts:
                C = np.full((len(ts), len(ds)), 1e6)
                for i, t in enumerate(ts):
                    gap = f - t["frames"][-1]
                    for j, d in enumerate(ds):
                        c = self._cost(t, d, gap)
                        if c <= self.gate:
                            C[i, j] = c
                ri, cj = linear_sum_assignment(C)
                used = set()
                for i, j in zip(ri, cj):
                    if C[i, j] < 1e5:
                        self._push(ts[i], f, ds[j])
                        matched.add(id(ts[i]))
                        used.add(j)
                new = [d for j, d in enumerate(ds) if j not in used]
            else:
                new = ds
            for d in new:
                self._new(f, d)
        keep = []
        for t in self.active:
            if f - t["frames"][-1] > self.max_gap:
                self.done.append(t)
            else:
                keep.append(t)
        self.active = keep

    def _new(self, f, d):
        t = dict(id=self.next_id, cls=d["cls"], c=d["c"], frames=[f], boxes=[tuple(d["box"])], areas=[d["area"]], vel=(0.0, 0.0),
                 colors=[d.get("color")], color=d.get("color"), radii=[d["r"]] if d.get("r") is not None else [])
        self.next_id += 1
        self._bind(t)
        self.active.append(t)

    def _push(self, t, f, d):
        pf = t["frames"][-1]
        pcx, pcy, _, _ = _geom(t["boxes"][-1])
        dcx, dcy, _, _ = _geom(d["box"])
        k = max(1, f - pf)
        t["vel"] = ((dcx - pcx) / k, (dcy - pcy) / k)
        t["frames"].append(f)
        t["boxes"].append(tuple(d["box"]))
        t["areas"].append(d["area"])
        t["colors"].append(d.get("color"))
        if d.get("r") is not None:
            t["radii"].append(d["r"])
        if d.get("color") is not None:
            t["color"] = d["color"]

    @staticmethod
    def _bind(t):
        def pred(gap, t=t):
            cx, cy, w, h = _geom(t["boxes"][-1])
            return cx + t["vel"][0] * gap, cy + t["vel"][1] * gap, w, h
        t["pred"] = pred

    def finish(self, min_len=3):
        out = []
        for t in self.done + self.active:
            if len(t["frames"]) >= min_len:
                out.append(t)
        for t in self.active:
            pass
        self.done, self.active = [], []
        return out


def fill_gaps(frames, boxes):
    """linear interpolation across the short gaps the tracker tolerated -> one box per frame from first to last."""
    ff, bb = [], []
    for i, (f, b) in enumerate(zip(frames, boxes)):
        if ff and f - ff[-1] > 1:
            pf, pb = ff[-1], bb[-1]
            for g in range(pf + 1, f):
                a = (g - pf) / float(f - pf)
                ff.append(g)
                bb.append(tuple(int(round(pb[k] + (b[k] - pb[k]) * a)) for k in range(4)))
        ff.append(f)
        bb.append(tuple(int(v) for v in b))
    return ff, bb
