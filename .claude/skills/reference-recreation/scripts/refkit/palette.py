"""Flat UI colours of a segment: large, compact, uniformly coloured regions (cards, pills, buttons, bands)."""
import numpy as np
from scipy import ndimage as ndi


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hex(c):
    return "#%02X%02X%02X" % tuple(int(round(v)) for v in c)


def flat_colors(samples, bg, min_cov=0.0012, max_colors=10, min_area=700):
    """samples: list of HxWx3 uint8 frames of one segment. Returns [dict(color=(r,g,b), coverage)] without the background colour."""
    if not samples:
        return []
    H, W = samples[0].shape[:2]
    N = H * W
    cand = {}
    for fr in samples:
        q = fr >> 2
        code = (q[..., 0].astype(np.int32) << 12) | (q[..., 1].astype(np.int32) << 6) | q[..., 2].astype(np.int32)
        u, c = np.unique(code.ravel(), return_counts=True)
        for cd, n in zip(u[c >= min_cov * N], c[c >= min_cov * N]):
            cand.setdefault(int(cd), []).append(n / N)
    need = 1 if len(samples) < 3 else 2
    kept = []
    first = samples[len(samples) // 2]
    for cd, covs in cand.items():
        if len(covs) < need:
            continue
        rgb = np.array([((cd >> 12) & 63) * 4 + 2, ((cd >> 6) & 63) * 4 + 2, (cd & 63) * 4 + 2], float)
        best, bn = None, 0
        for fr in samples:                                   # the sample where this colour is most present
            m = (np.abs(fr.astype(np.int16) - rgb.astype(np.int16)).max(axis=2) <= 4)
            n_ = int(m.sum())
            if n_ > bn:
                best, bn = (fr, m), n_
        if best is None or bn < min_cov * N:
            continue
        fr, m = best
        exact = np.median(fr[m], axis=0)
        I16 = fr.astype(np.int16)
        m2 = (np.abs(I16 - exact.astype(np.int16)).max(axis=2) <= 3)
        lab, n = ndi.label(m2, structure=np.ones((3, 3)))
        if n == 0:
            continue
        areas = ndi.sum(m2, lab, range(1, n + 1))
        if areas.max() < min_area or areas.max() < 0.5 * m2.sum():
            continue
        # a flat UI colour has sharp edges: widening the tolerance from 3 to 12 adds (almost) nothing inside the region's box;
        # a gradient (sky, skin, glow) keeps growing
        k_ = int(np.argmax(areas)) + 1
        sl = ndi.find_objects(lab)[k_ - 1]
        sub = I16[sl]
        n3 = int((np.abs(sub - exact.astype(np.int16)).max(axis=2) <= 3).sum())
        n12 = int((np.abs(sub - exact.astype(np.int16)).max(axis=2) <= 12).sum())
        if n12 > 1.25 * n3:
            continue
        kept.append(dict(color=tuple(int(round(v)) for v in exact), coverage=float(np.mean(covs))))
    kept.sort(key=lambda d: -d["coverage"])
    out = []
    for k in kept:
        c = np.array(k["color"])
        if np.abs(c - np.array(bg)).max() <= 5:
            continue
        if any(np.abs(c - np.array(o["color"])).max() <= 6 for o in out):
            continue
        out.append(k)
        if len(out) >= max_colors:
            break
    return out
