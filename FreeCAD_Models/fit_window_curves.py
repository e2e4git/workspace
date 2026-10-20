# -*- coding: utf-8 -*-
"""
fit_window_curves.py — read the two boundary curves of one window straight out
of the polar profile of the drawing and fit a circle / ellipse to each.
"""
import math

import numpy as np
from PIL import Image

IMG = "/workspace/FreeCAD_Models/drawing_profile_only.png"
CX, CY = 455.5, 366.0
PX2IN = 1.0 / 107.18

A = np.array(Image.open(IMG).convert("L"))
CURVE = A < 200
H, W = CURVE.shape


def profile(deg, r0=30, r1=270, step=0.2):
    a = math.radians(deg)
    out, prev, r = [], False, r0
    while r < r1:
        x = int(round(CX + r * math.cos(a)))
        y = int(round(CY - r * math.sin(a)))
        if 0 <= x < W and 0 <= y < H:
            v = CURVE[y, x]
            if v and not prev:
                out.append(round(r, 2))
            prev = v
        r += step
    return out


def xy(r, deg):
    a = math.radians(deg)
    return (CX + r * math.cos(a), CY - r * math.sin(a))


def fit_circle(P):
    P = np.asarray(P, float)
    x, y = P[:, 0], P[:, 1]
    M = np.column_stack([x, y, np.ones(len(x))])
    sol, *_ = np.linalg.lstsq(M, x ** 2 + y ** 2, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = math.sqrt(max(sol[2] + cx * cx + cy * cy, 0))
    err = float(np.abs(np.hypot(x - cx, y - cy) - r).max())
    return cx, cy, r, err


def fit_ellipse(P):
    P = np.asarray(P, float)
    x, y = P[:, 0], P[:, 1]
    D = np.column_stack([x * x, x * y, y * y, x, y, np.ones(len(x))])
    _, _, V = np.linalg.svd(D)
    a, b, c, d, e, f = V[-1]
    Mm = np.array([[a, b / 2], [b / 2, c]])
    cen = np.linalg.solve(2 * Mm, np.array([-d, -e]))
    Fc = (a * cen[0] ** 2 + b * cen[0] * cen[1] + c * cen[1] ** 2
          + d * cen[0] + e * cen[1] + f)
    Q = Mm / (-Fc)
    evals, evecs = np.linalg.eigh(Q)
    axes = 1.0 / np.sqrt(np.abs(evals))
    o = np.argsort(axes)[::-1]
    axes, evecs = axes[o], evecs[:, o]
    v = np.column_stack([x - cen[0], y - cen[1]])
    q = np.einsum("ij,jk,ik->i", v, Q, v)
    res = float(np.sqrt(((q - 1) ** 2).mean()))
    return cen, axes, evecs, res


# ---- collect the two middle curves of the 30 deg window ------------------
inner, outer = [], []
for deg in range(-58, 59):
    if deg in (0, 60, -60, 90, -90, 120, -120, 150, -150, 180):
        continue
    h = profile(deg, 30, 270)
    h = [r for r in h if 30 < r < 250]
    if len(h) < 2:
        continue
    # the two smallest radii above the bore
    h2 = sorted(h)
    # pick the two curves closest to the hub that are inside r=250
    a, b = h2[0], h2[1]
    inner.append(xy(a, deg))
    outer.append(xy(b, deg))

for name, P in (("INNER curve", inner), ("OUTER curve", outer)):
    cx, cy, r, err = fit_circle(P)
    cen, axes, evecs, res = fit_ellipse(P)
    ang_ax = math.degrees(math.atan2(evecs[1, 0], evecs[0, 0])) % 180
    d = math.hypot(cen[0] - CX, cen[1] - CY)
    th = math.degrees(math.atan2(CY - cen[1], cen[0] - CX)) % 360
    print("=" * 74)
    print(name, " n =", len(P))
    print("  circle : R=%.2f px (%.3f in = %.2f mm)  centre=(%.1f,%.1f) "
          "d=%.1f@%.1f  maxerr=%.2f" %
          (r, r * PX2IN, r * PX2IN * 25.4, cx, cy, d, th, err))
    print("  ellipse: semi-axes %.2f / %.2f px (%.3f / %.3f in = %.2f / %.2f mm)"
          "  centre=(%.1f,%.1f) d=%.1f@%.1f  axis=%.1f deg  rms=%.4f" %
          (axes[0], axes[1], axes[0] * PX2IN, axes[1] * PX2IN,
           axes[0] * PX2IN * 25.4, axes[1] * PX2IN * 25.4,
           cen[0], cen[1], d, th, ang_ax, res))

print()
print("sampled inner curve (deg, r):")
for deg in range(-54, 55, 6):
    h = [r for r in profile(deg, 30, 270) if 30 < r < 250]
    if len(h) >= 2:
        print("   %4d : %6.1f %6.1f   (r,in)=%6.3f %6.3f" %
              (deg, sorted(h)[0], sorted(h)[1],
               sorted(h)[0] * PX2IN, sorted(h)[1] * PX2IN))
