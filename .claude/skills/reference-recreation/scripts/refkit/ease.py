"""Named eases (GSAP-compatible shapes) and keyframe compression of per-frame series."""
import math

import numpy as np


def _pow(n):
    return dict(
        **{"power%d.in" % n: lambda t, n=n: t ** n},
        **{"power%d.out" % n: lambda t, n=n: 1 - (1 - t) ** n},
        **{"power%d.inOut" % n: lambda t, n=n: (2 ** (n - 1)) * t ** n if t < 0.5 else 1 - ((-2 * t + 2) ** n) / 2.0})


EASES = {"none": lambda t: t}
for _n in (1, 2, 3, 4):
    EASES.update(_pow(_n))
EASES.update({
    "sine.in": lambda t: 1 - math.cos(t * math.pi / 2), "sine.out": lambda t: math.sin(t * math.pi / 2), "sine.inOut": lambda t: -(math.cos(math.pi * t) - 1) / 2,
    "expo.in": lambda t: 0.0 if t == 0 else 2 ** (10 * t - 10), "expo.out": lambda t: 1.0 if t == 1 else 1 - 2 ** (-10 * t),
    "expo.inOut": lambda t: 0.0 if t == 0 else 1.0 if t == 1 else (2 ** (20 * t - 10)) / 2 if t < 0.5 else (2 - 2 ** (-20 * t + 10)) / 2,
    "back.out(1.7)": lambda t: 1 + 2.70158 * (t - 1) ** 3 + 1.70158 * (t - 1) ** 2,
})
_NAMES = list(EASES)
_TAB = np.array([[EASES[n](u) for u in np.linspace(0, 1, 41)] for n in _NAMES])


def fit_ease(vals):
    """best named ease for a monotone run (list of values); returns (name, rms error in value units)."""
    v = np.asarray(vals, float)
    if len(v) < 3 or abs(v[-1] - v[0]) < 1e-9:
        return "none", 0.0
    p = (v - v[0]) / (v[-1] - v[0])
    u = np.linspace(0, 1, len(v))
    best = ("none", 1e9)
    for name, row in zip(_NAMES, _TAB):
        q = np.interp(u, np.linspace(0, 1, 41), row)
        e = float(np.sqrt(np.mean((q - p) ** 2))) * abs(v[-1] - v[0])
        if e < best[1]:
            best = (name, e)
    return best


def keyframes(frames, values, eps=0.35):
    """per-frame series -> ([[frame, value, ease], ...], max error vs raw). The ease at a key governs the segment ending there; holds repeat the value.
    Splits at direction changes and holds; a segment no named ease fits within 1.5 value units is emitted sample by sample (linear)."""
    f = list(frames)
    v = np.asarray(values, float)
    if len(f) == 0:
        return [], 0.0
    keys = [[f[0], float(v[0]), "none"]]
    i, n = 0, len(v)
    while i < n - 1:
        d = v[i + 1] - v[i]
        if abs(d) <= eps:
            j = i + 1
            while j + 1 < n and abs(v[j + 1] - v[j]) <= eps:
                j += 1
            keys.append([f[j], float(v[j]), "none"])
            i = j
            continue
        sgn = 1 if d > 0 else -1
        j = i + 1
        while j + 1 < n and (v[j + 1] - v[j]) * sgn > eps * 0.5:
            j += 1
        name, err = fit_ease(v[i:j + 1])
        if err > 1.5 and j - i >= 3:
            for k in range(i + 1, j + 1):
                keys.append([f[k], float(v[k]), "none"])
        else:
            keys.append([f[j], float(v[j]), name])
        i = j
    worst = 0.0
    idx = {x: k for k, x in enumerate(f)}
    for a, b in zip(keys, keys[1:]):
        for x in f:
            if a[0] <= x <= b[0]:
                t = (x - a[0]) / float(b[0] - a[0]) if b[0] > a[0] else 1.0
                worst = max(worst, abs(a[1] + (b[1] - a[1]) * EASES.get(b[2], EASES["none"])(t) - float(v[idx[x]])))
    return [[int(a), round(b, 2), c] for a, b, c in keys], round(worst, 2)
