# -*- coding: utf-8 -*-
"""
region_map.py — flood-fill the drawing with the drawn lines acting as walls
and print an ASCII map of the connected regions.  This reveals the topology of
the part (material / windows / bore) without having to guess.
"""
import math

import numpy as np
from PIL import Image
from scipy import ndimage

IMG = "/workspace/src/drawings/Screenshot (2).png"
CX, CY = 455.5, 366.0

A = np.array(Image.open(IMG).convert("L"))
INK = A < 200
H, W = INK.shape

# --- remove arrow heads (solid blocks) so they do not act as walls -------- #
dense = ndimage.uniform_filter(INK.astype(np.float32), size=3)
solid = (dense > 0.995) & INK
solid = ndimage.binary_dilation(solid, np.ones((3, 3)))
walls = INK & ~solid

# --- remove the OUTER hexagon (analytically known) ----------------------- #
R_HEX = 395.5
outer = np.zeros_like(walls)
for k in range(6):
    a0 = math.radians(60 * k)
    a1 = math.radians(60 * (k + 1))
    p0 = (CX + R_HEX * math.cos(a0), CY - R_HEX * math.sin(a0))
    p1 = (CX + R_HEX * math.cos(a1), CY - R_HEX * math.sin(a1))
    n = 400
    for i in range(n + 1):
            t = i / n
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t
            xi, yi = int(round(x)), int(round(y))
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    yy, xx = yi + dy, xi + dx
                    if 0 <= yy < H and 0 <= xx < W:
                        outer[yy, xx] = True
walls = walls & ~outer

# seal the walls (anti-aliased lines have pin-holes)
walls = ndimage.binary_dilation(walls, np.ones((3, 3)))
free = ~walls


def flood(seed, mask):
    lbl, n = ndimage.label(mask)          # 4-connectivity for the free space
    return lbl == lbl[seed], n


regions = {}
for name, seed in [("arm-top", (455, 200)), ("hub", (455, 355)),
                    ("upper-left", (250, 250)), ("upper-right", (640, 250)),
                    ("lower", (455, 500)), ("lower-left", (300, 500)),
                    ("lower-right", (620, 500)), ("outside", (5, 5)),
                    ("near-bore", (440, 366)), ("gap", (470, 366))]:
    m, n = flood(seed, free)
    regions[name] = m
    print("%-12s seed=%-10s  pixels=%6d  of %d regions" % (name, seed, m.sum(), n))

# ------------------------------------------------------------------ #
# ASCII map of the region of the top arm and the surrounding area
# ------------------------------------------------------------------ #
print()
print("=== material map, x 180..740, y 100..640 (step 7) ===")
marks = {}
letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
for i, (name, m) in enumerate(regions.items()):
    marks[name] = letters[i] if i < len(letters) else "?"
legend = {marks[n]: n for n in regions}
print("legend:", legend)
for y in range(100, 641, 7):
    row = ""
    for x in range(180, 741, 7):
        ch = " "
        for name, m in regions.items():
            if m[y, x]:
                ch = marks[name]
                break
        row += ch
    print("%4d %s" % (y, row))
