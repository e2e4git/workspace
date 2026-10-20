# -*- coding: utf-8 -*-
"""
fit_windows.py — extract the three window outlines of the gear (they are
closed curves in the drawing) and fit a conic (ellipse) to each of them.
"""
import math

import numpy as np
from PIL import Image
from scipy import ndimage

IMG = "/workspace/FreeCAD_Models/drawing_profile_only.png"
CX, CY = 455.5, 366.0
PX2IN = 1.0 / 107.18

A = np.array(Image.open(IMG).convert("L"))
INK = A < 200
H, W = INK.shape

seeds = {270: (455, 560), 30: (620, 250), 150: (290, 250)}

walls = ndimage.binary_dilation(INK, np.ones((3, 3)))
free = ~walls
lab, n = ndimage.label(free)
print("free regions:", n)

for ang, seed in seeds.items():
    r = lab[seed[1], seed[0]]
    m = (lab == r)
    ys, xs = np.nonzero(m)
    print("=" * 78)
    print("window at %3d deg: region %d px, bbox x %d..%d y %d..%d" %
          (ang, m.sum(), xs.min(), xs.max(), ys.min(), ys.max()))

    # contour of the region: pixels of the region that touch a non-region
    er = ndimage.binary_erosion(m, np.ones((3, 3)))
    contour = m & ~er
    cy_, cx_ = np.nonzero(contour)
    print("   contour pixels:", len(cx_))

    # ellipse fit on the contour
    x = cx_.astype(float)
    y = cy_.astype(float)
    D = np.column_stack([x * x, x * y, y * y, x, y, np.ones(len(x))])
    _, _, V = np.linalg.svd(D)
    a, b, c, d, e, f = V[-1]
    Mm = np.array([[a, b / 2.0], [b / 2.0, c]])
    if abs(np.linalg.det(Mm)) < 1e-12:
        print("   degenerate conic")
        continue
    cen = np.linalg.solve(2 * Mm, np.array([-d, -e]))
    Fc = (a * cen[0] ** 2 + b * cen[0] * cen[1] + c * cen[1] ** 2
          + d * cen[0] + e * cen[1] + f)
    Q = Mm / (-Fc)
    evals, evecs = np.linalg.eigh(Q)
    axes = 1.0 / np.sqrt(np.abs(evals))
    order = np.argsort(axes)[::-1]
    axes = axes[order]
    evecs = evecs[:, order]
    ang_ax = math.degrees(math.atan2(evecs[1, 0], evecs[0, 0])) % 180.0
    rcen = math.hypot(cen[0] - CX, cen[1] - CY)
    thcen = math.degrees(math.atan2(CY - cen[1], cen[0] - CX)) % 360.0
    print("   ellipse centre=(%.1f,%.1f) semi-axes %.1f / %.1f px "
          "(%.3f / %.3f in)  major-axis angle %.1f deg" %
          (cen[0], cen[1], axes[0], axes[1], axes[0] * PX2IN, axes[1] * PX2IN,
           ang_ax))
    print("   centre offset: r=%.1f px (%.3f in) dir=%.1f deg" %
          (rcen, rcen * PX2IN, thcen))
    v = np.column_stack([x - cen[0], y - cen[1]])
    q = np.einsum("ij,jk,ik->i", v, Q, v)
    resid = np.abs(q - 1.0)
    print("   conic residual: max %.4f rms %.4f" %
          (resid.max(), float(np.sqrt((resid ** 2).mean()))))
    # radial extent of the window
    rr = np.hypot(x - CX, y - CY)
    tt = (np.degrees(np.arctan2(CY - y, x - CX))) % 360.0
    print("   window radius range: %.1f .. %.1f px (%.3f .. %.3f in)" %
          (rr.min(), rr.max(), rr.min() * PX2IN, rr.max() * PX2IN))
    hist, edges = np.histogram(tt, bins=36, range=(0, 360))
    print("   angular occupancy per 10 deg:", list(hist))
