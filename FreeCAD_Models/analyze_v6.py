# -*- coding: utf-8 -*-
"""
analyze_v6.py  —  quantitative extraction of the SKETCH geometry.
Prints scanlines (dark-pixel crossings) and a polar profile about the bore
centre, so that every drawn feature can be identified by pixel coordinates.
"""
import os
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SKETCH = "/workspace/src/drawings/Screenshot (2).png"
OUT = "/workspace/FreeCAD_Models/out"


def runs(idx):
    """group sorted indices into (start, end) inclusive runs"""
    out = []
    if len(idx) == 0:
        return out
    s = idx[0]
    p = idx[0]
    for v in idx[1:]:
        if v != p + 1:
            out.append((s, p))
            s = v
        p = v
    out.append((s, p))
    return out


def scanline(mask, y, x0=0, x1=None):
    x1 = mask.shape[1] if x1 is None else x1
    row = mask[y, x0:x1]
    idx = np.nonzero(row)[0] + x0
    return runs(idx)


def scancol(mask, x, y0=0, y1=None):
    y1 = mask.shape[0] if y1 is None else y1
    col = mask[y0:y1, x]
    idx = np.nonzero(col)[0] + y0
    return runs(idx)


def fit_circle(mask, region):
    x0, y0, x1, y1 = region
    sub = mask[y0:y1, x0:x1]
    ys, xs = np.nonzero(sub)
    xs = xs + x0
    ys = ys + y0
    A = np.stack([xs, ys, np.ones(len(xs))], 1).astype(float)
    b = (xs ** 2 + ys ** 2).astype(float)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = math.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 0.0))
    res = np.hypot(xs - cx, ys - cy) - r
    return cx, cy, r, float(np.abs(res).max()), len(xs)


g = np.array(Image.open(SKETCH).convert("L"))
H, W = g.shape
m = g < 170
print("sketch %dx%d" % (W, H))

# ---------------------------------------------------------------- bore ------
# small circle around the drawing centre: search a window and fit
best = None
for r0 in (12, 14, 16, 18, 20, 22):
    reg = (455 - r0 - 6, 365 - r0 - 6, 455 + r0 + 7, 365 + r0 + 7)
    cx, cy, r, err, n = fit_circle(m, reg)
    if err < 4.0 and 10 < r < 40:
        best = (cx, cy, r, err, n)
        break
print("bore circle fit:", best)
CX, CY = (455.0, 365.0)

# hexagon check: hough gave horizontal line y=365 from x=60..851
# hexagon vertices expected from R=395.5
R = 395.5
for a in range(0, 360, 60):
    x = CX + R * math.cos(math.radians(a))
    y = CY - R * math.sin(math.radians(a))
    print("   hex vertex %3d deg -> (%.1f, %.1f)" % (a, x, y))

# ------------------------------------------------------- scanlines ---------
print("\n=== horizontal scanlines (y : x-runs) ===")
for y in [25, 40, 60, 80, 100, 117, 130, 155, 165, 180, 200, 230, 260, 290,
          320, 350, 365, 380, 400, 430, 460, 490, 520, 550, 580, 610, 645, 660,
          680, 700]:
    print("y=%3d : %s" % (y, scanline(m, y)))

print("\n=== vertical scanlines (x : y-runs) ===")
for x in [70, 100, 150, 200, 250, 260, 270, 300, 340, 360, 390, 420, 455,
          485, 520, 560, 600, 640, 650, 660, 700, 750, 800, 840]:
    print("x=%3d : %s" % (x, scancol(m, x)))

# ------------------------------------------------- polar profile ----------
def polar(mask, cx, cy, n=2880, rmax=None):
    if rmax is None:
        ys, xs = np.nonzero(mask)
        rmax = int(math.hypot(ys.max() - cy, xs.max() - cx)) + 5
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    Hh, Ww = mask.shape
    out = np.full(n, np.nan)
    for i, a in enumerate(th):
        dx, dy = math.cos(a), -math.sin(a)          # math orientation (y up)
        rs = np.arange(0, rmax, 0.5)
        xs = np.rint(cx + rs * dx).astype(int)
        ys = np.rint(cy + rs * dy).astype(int)
        ok = (xs >= 0) & (xs < Ww) & (ys >= 0) & (ys < Hh)
        hit = np.zeros(len(rs), bool)
        hit[ok] = mask[ys[ok], xs[ok]]
        idx = np.nonzero(hit)[0]
        if len(idx):
            out[i] = rs[idx[-1]]
    return th, out


th, r = polar(m, CX, CY)
print("\n=== outer polar profile of the sketch (deg : r_px) every 3 deg ===")
prof = []
for i in range(0, len(th), 30):   # 2880/30 = 96 -> every 3.75 deg
    prof.append("%5.1f:%6.1f" % (math.degrees(th[i]), r[i]))
for i in range(0, len(prof), 6):
    print("   " + "  ".join(prof[i:i + 6]))
print("   max r = %.1f at %.1f deg" % (np.nanmax(r), math.degrees(th[np.nanargmax(r)])))
print("   min r = %.1f" % np.nanmin(r))
