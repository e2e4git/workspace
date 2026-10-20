# -*- coding: utf-8 -*-
"""
extract_profile.py — strip every construction / dimension element from the CAD
screenshot and keep only the real part profile (tooth outline, web, windows,
bore).  The result is vectorised and fitted so the part can be rebuilt exactly.

Removed analytically:
  * the outer regular hexagon   (side 3.69 in)
  * the inner regular hexagon   (side 2.24 in / inradius 1.94 in)
  * the 8 radial construction rays through the centre
  * the five dimension lines and their arrow heads
  * the dimension text
"""
import math

import numpy as np
from PIL import Image
from scipy import ndimage

IMG = "/workspace/src/drawings/Screenshot (2).png"
OUT_PNG = "/workspace/FreeCAD_Models/drawing_profile_only.png"
CX, CY = 455.5, 366.0
PX2IN = 1.0 / 107.18

A = np.array(Image.open(IMG).convert("L"))
INK = A < 200
H, W = INK.shape

# ------------------------------------------------------------------ #
# 1. remove arrow heads + text
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


# ------------------------------------------------------------------ #
# 2. helpers to erase analytic geometry
# ------------------------------------------------------------------ #
def erase_line(p0, p1, width=2, only_short_runs=None):
    """erase ink lying on the segment p0-p1 (width px)."""
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    n = int(L * 2) + 2
    for i in range(n + 1):
        t = i / float(n)
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        for dy in range(-width, width + 1):
            for dx in range(-width, width + 1):
                yy, xx = int(round(y)) + dy, int(round(x)) + dx
                if 0 <= yy < H and 0 <= xx < W:
                    CURVE[yy, xx] = False


def erase_ray(angle_deg, r0, r1, width=1):
    a = math.radians(angle_deg)
    p0 = (CX + r0 * math.cos(a), CY - r0 * math.sin(a))
    p1 = (CX + r1 * math.cos(a), CY - r1 * math.sin(a))
    erase_line(p0, p1, width)


def polar(r, deg):
    a = math.radians(deg)
    return (CX + r * math.cos(a), CY - r * math.sin(a))


# outer hexagon (side 3.69 in -> circumradius 395.5 px)
R_OUT = 395.5
for k in range(6):
    erase_line(polar(R_OUT, 60 * k), polar(R_OUT, 60 * (k + 1)), 2)

# inner hexagon (side 2.24 in -> circumradius 240.2 px)
R_IN = 240.2
for k in range(6):
    erase_line(polar(R_IN, 60 * k), polar(R_IN, 60 * (k + 1)), 2)

# the eight radial construction rays
for ang in (0, 60, 90, 120, 180, 240, 270, 300):
    erase_ray(ang, 20, 410, 1)

# dimension lines
erase_line((335, 119), (577, 119), 1)          # 2.24 in
erase_line((455, 158), (455, 366), 1)          # 1.94 in
erase_line((258, 636), (653, 636), 1)          # 3.69 in
erase_ray(30, 200, 350, 1)                     # 1.25 in (upper right)
erase_ray(300, 200, 350, 1)                    # 1.25 in (lower left)

Image.fromarray((~CURVE * 255).astype(np.uint8)).save(OUT_PNG)
print("profile-only image:", OUT_PNG)

# ------------------------------------------------------------------ #
# 3. label the remaining components
# ------------------------------------------------------------------ #
lab2, n2 = ndimage.label(CURVE, structure=np.ones((3, 3)))
sizes = ndimage.sum(CURVE, lab2, range(1, n2 + 1))
print("components:", n2)
for i in np.argsort(sizes)[::-1][:20]:
    if sizes[i] < 30:
        break
    ys, xs = np.nonzero(lab2 == (i + 1))
    print("  comp %3d size %6d  bbox x %d..%d  y %d..%d" %
          (i + 1, sizes[i], xs.min(), xs.max(), ys.min(), ys.max()))

# ------------------------------------------------------------------ #
# 4. polar profile of the remaining outer boundary
# ------------------------------------------------------------------ #
print()
print("=== radial profile of the remaining ink, 0..360 deg ===")
for deg in range(0, 360, 2):
    a = math.radians(deg)
    hits, prev = [], False
    r = 30.0
    while r < 400:
        x = int(round(CX + r * math.cos(a)))
        y = int(round(CY - r * math.sin(a)))
        if 0 <= x < W and 0 <= y < H:
            v = CURVE[y, x]
            if v and not prev:
                hits.append(round(r, 1))
            prev = v
        r += 0.25
    print("%3d %s" % (deg, hits))
