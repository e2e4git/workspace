# -*- coding: utf-8 -*-
"""
trace_curves.py — follow every drawn curve of the CAD sketch pixel by pixel.

Unlike a skeleton/thinning approach this walks the ink itself, which keeps
the vertices of the profile exactly where they are.  The result is written as
a coloured PNG (one colour per curve) so the topology can be checked at a
glance, and as a table with the fitted radius / direction of every curve.
"""
import math

import numpy as np
from PIL import Image
from scipy import ndimage

IMG = "/workspace/src/drawings/Screenshot (2).png"
OUT_PNG = "/workspace/FreeCAD_Models/drawing_traced.png"
CX, CY = 455.5, 366.0

A = np.array(Image.open(IMG).convert("L"))
INK = A < 200
H, W = INK.shape

# ------------------------------------------------------------------ #
# drop filled arrow heads and text glyphs
# ------------------------------------------------------------------ #
dense = ndimage.uniform_filter(INK.astype(np.float32), size=3)
solid = ndimage.binary_dilation((dense > 0.995) & INK, np.ones((3, 3)))
CURVE = INK & ~solid
lab, n = ndimage.label(CURVE, structure=np.ones((3, 3)))
objs = ndimage.find_objects(lab)
keep = np.ones(n + 1, bool)
for i, sl in enumerate(objs, start=1):
    ys, xs = sl
    h, w = ys.stop - ys.start, xs.stop - xs.start
    area = (lab[sl] == i).sum()
    if h <= 24 and w <= 24 and area >= 12 and area / float(h * w) > 0.25:
        keep[i] = False
CURVE[~keep[lab]] = False

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def neighbours(y, x):
    out = []
    for dy, dx in N8:
        yy, xx = y + dy, x + dx
        if 0 <= yy < H and 0 <= xx < W and CURVE[yy, xx]:
            out.append((yy, xx))
    return out


def walk(start, first):
    """follow the ink from (start,first) keeping the direction."""
    path = [start, first]
    prev, cur = start, first
    d = (cur[0] - prev[0], cur[1] - prev[1])
    while True:
        cand = []
        for n in neighbours(*cur):
            if n == prev:
                continue
            nd = (n[0] - cur[0], n[1] - cur[1])
            dot = nd[0] * d[0] + nd[1] * d[1]
            if dot <= 0:                    # only continue "forwards"
                continue
            cand.append((dot, n, nd))
        if not cand:
            break
        cand.sort(key=lambda t: -t[0])
        if len(cand) > 1:
            # ambiguous -> junction: take the most forward one but stop soon
            dot, nxt, nd = cand[0]
            if len(cand) > 1 and cand[1][0] > 0:
                # only stop if the branch is really a fork
                cross = d[0] * nd[1] - d[1] * nd[0]
                if abs(cross) > 0.6:
                    break
        else:
            dot, nxt, nd = cand[0]
        path.append(nxt)
        prev, cur = cur, nxt
        d = nd
        if len(path) > 4000:
            break
    return path


visited = set()
curves = []
ys, xs = np.nonzero(CURVE)
for y, x in zip(ys, xs):
    if (y, x) in visited:
        continue
    nbrs = neighbours(y, x)
    if not nbrs:
        continue
    for n in nbrs:
        if (n in visited) and (y, x) in visited:
            continue
        p = walk((y, x), n)
        for q in p:
            visited.add(q)
        if len(p) >= 14:
            curves.append(p)

print("curves traced:", len(curves))
curves.sort(key=len, reverse=True)

# ------------------------------------------------------------------ #
# fit and report
# ------------------------------------------------------------------ #
COLS = [(255, 0, 0), (0, 140, 255), (0, 180, 0), (255, 140, 0), (160, 0, 220),
        (0, 190, 190), (230, 0, 120), (120, 90, 0), (0, 0, 220), (0, 190, 90),
        (200, 0, 200), (90, 90, 90)]

base = Image.open(IMG).convert("RGB")
from PIL import ImageDraw
dr = ImageDraw.Draw(base)

report = []
for i, p in enumerate(curves):
    pts = np.array([(q[1], q[0]) for q in p], float)
    x, y = pts[:, 0], pts[:, 1]
    # circle fit
    M = np.column_stack([x, y, np.ones(len(x))])
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(M, b, rcond=None)
    ccx, ccy = sol[0] / 2, sol[1] / 2
    r = math.sqrt(max(sol[2] + ccx * ccx + ccy * ccy, 0))
    err = float(np.abs(np.hypot(x - ccx, y - ccy) - r).max())
    # line fit
    mx, my = x.mean(), y.mean()
    sxx = ((x - mx) ** 2).sum()
    syy = ((y - my) ** 2).sum()
    sxy = ((x - mx) * (y - my)).sum()
    th = 0.5 * math.atan2(2 * sxy, sxx - syy)
    nx, ny = -math.sin(th), math.cos(th)
    lerr = float(np.abs((x - mx) * nx + (y - my) * ny).max())
    d0 = math.hypot(ccx - CX, ccy - CY)
    a0 = math.degrees(math.atan2(CY - ccy, ccx - CX)) % 360
    a1 = math.degrees(math.atan2(CY - y[-1], x[-1])) % 360
    kind = "ARC " if err < lerr else "LINE"
    report.append((kind, len(p), err, lerr, r, ccx, ccy, d0, a0,
                   (x[0], y[0]), (x[-1], y[-1])))

    col = COLS[i % len(COLS)]
    dr.line([(q[1], q[0]) for q in p], fill=col, width=2)

print("\n%-5s %-6s %-7s %-7s %-9s %-16s %-7s %-16s %s" %
      ("kind", "n", "cErr", "lErr", "R", "centre", "dCtr", "dir", "endpoints"))
for r_ in report:
    kind, n, err, lerr, R, ccx, ccy, d0, a0, s, e = r_
    print("%-5s %-6d %-7.2f %-7.2f %-9.1f (%7.1f,%7.1f) %-7.1f %-16.1f "
          "(%.0f,%.0f)-(%.0f,%.0f)" %
          (kind, n, err, lerr, R, ccx, ccy, d0, a0, s[0], s[1], e[0], e[1]))

base.save(OUT_PNG)
print("\nPNG:", OUT_PNG)
