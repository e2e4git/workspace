# -*- coding: utf-8 -*-
"""
probe_drawing.py — targeted extraction of individual curves from the drawing.

For every requested region it prints the ink runs per row / column and fits
a circle to the selected pixels, so the real radii of the arcs can be read off
instead of guessed.
"""
import math
import sys

import numpy as np
from PIL import Image

IMG = "/workspace/src/drawings/Screenshot (2).png"
CX, CY = 455.5, 366.0
PX2IN = 1.0 / 107.18          # 1 in = 107.18 px  (3.69 in <-> 395.5 px)

im = Image.open(IMG).convert("L")
A = np.array(im)
INK = A < 200
H, W = INK.shape


def runs_row(y, x0, x1, gap=3):
    r = INK[y, x0:x1]
    out, s = [], None
    for i, v in enumerate(r):
        if v and s is None:
            s = i + x0
        elif not v and s is not None:
            out.append((s, i + x0 - 1))
            s = None
    if s is not None:
        out.append((s, x1 - 1))
    m = []
    for a, b in out:
        if m and a - m[-1][1] <= gap:
            m[-1] = (m[-1][0], b)
        else:
            m.append((a, b))
    return m


def fit_circle(pts):
    pts = np.asarray(pts, float)
    x, y = pts[:, 0], pts[:, 1]
    M = np.column_stack([x, y, np.ones(len(x))])
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(M, b, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = math.sqrt(max(sol[2] + cx * cx + cy * cy, 0))
    rad = np.hypot(x - cx, y - cy)
    err = float(np.abs(rad - r).max())
    return cx, cy, r, err


def report(name, pts):
    if len(pts) < 4:
        print("%-28s not enough points (%d)" % (name, len(pts)))
        return
    cx, cy, r, err = fit_circle(pts)
    d = math.hypot(cx - CX, cy - CY)
    ang = math.degrees(math.atan2(CY - cy, cx - CX)) % 360
    print("%-28s n=%4d  R=%8.2f px (%6.3f in)  centre=(%7.1f,%7.1f) "
          "dist_from_part_centre=%7.2f px (%5.3f in) dir=%.1f deg  fit_err=%.2f"
          % (name, len(pts), r, r * PX2IN, cx, cy, d, d * PX2IN, ang, err))
    return cx, cy, r, err


print("=" * 100)
print("A. INNER HEXAGON  (expect side 240 px = 2.24 in, inradius 208 px = 1.94 in)")
for y, x0, x1, tag in [(574, 300, 620, "bottom side"),
                       (156, 300, 620, "top side"),
                       (366, 150, 400, "left-lower side"),
                       (366, 520, 780, "right-lower side")]:
    print("  row %d  %s -> %s" % (y, tag, runs_row(y, x0, x1)))

print()
print("B. BOTTOM ARC  (region under the hexagon bottom side, y 576..620)")
pts = []
for y in range(576, 622):
    for a, b in runs_row(y, 300, 620):
        mid = (a + b) / 2
        if 330 < mid < 580:
            pts.append((mid, y))
report("bottom arc (row midpoints)", pts)
for y in range(574, 622, 4):
    print("   row %3d: %s" % (y, runs_row(y, 300, 620)))

print()
print("C. TOP-LEFT ARC  (x 240..340, y 110..200)")
pts = []
for y in range(110, 205):
    for a, b in runs_row(y, 230, 345):
        pts.append(((a + b) / 2, y))
for y in range(110, 205, 4):
    print("   row %3d: %s" % (y, runs_row(y, 230, 345)))

print()
print("D. LEFT DOME / arcs around x 326..440, y 112..160")
for y in range(112, 162, 2):
    print("   row %3d: %s" % (y, runs_row(y, 320, 445)))

print()
print("E. VERTICAL LINES in the top arm (rows 160..320, x 370..540)")
for y in [160, 200, 240, 280, 320, 350]:
    print("   row %3d: %s" % (y, runs_row(y, 370, 545)))

print()
print("F. HUB / bore  (row 366, col 455)")
print("   row 366:", runs_row(366, 400, 520))
for y in range(330, 405, 5):
    print("   row %3d: %s" % (y, runs_row(y, 400, 520)))

print()
print("G. TOOTH PROFILE - radial profile of the outermost drawn curve")
for deg in range(0, 360, 3):
    a = math.radians(deg)
    hits = []
    prev = False
    r = 250.0
    while r < 345:
        x = int(round(CX + r * math.cos(a)))
        y = int(round(CY - r * math.sin(a)))
        if 0 <= x < W and 0 <= y < H:
            v = INK[y, x]
            if v and not prev:
                hits.append(round(r, 1))
            prev = v
        r += 0.25
    print("   %3d deg : %s" % (deg, hits))
