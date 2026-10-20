# -*- coding: utf-8 -*-
"""ray_probe.py — cast rays from the sketch centre through the geometry and
report every crossing.  This identifies exactly which curves the dimensions
refer to."""
import math
import numpy as np
from PIL import Image

SRC = "/workspace/FreeCAD_Models/out/sketch_clean.png"
rgb = np.array(Image.open(SRC).convert("RGB"))
m = (rgb[:, :, 0] < 128) & (rgb[:, :, 1] < 128)
H, W = m.shape
CX, CY = 455.0, 365.0
SCALE = 107.2      # px per inch


def crossings(deg, rmax=420.0, step=0.25):
    a = math.radians(deg)
    dx, dy = math.cos(a), -math.sin(a)
    rs = np.arange(0, rmax, step)
    xs = np.rint(CX + rs * dx).astype(int)
    ys = np.rint(CY + rs * dy).astype(int)
    ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
    hit = np.zeros(len(rs), bool)
    hit[ok] = m[ys[ok], xs[ok]]
    idx = np.nonzero(hit)[0]
    groups = []
    if len(idx):
        s = idx[0]
        p = idx[0]
        for v in idx[1:]:
            if v > p + 1:
                groups.append((rs[s], rs[p]))
                s = v
            p = v
        groups.append((rs[s], rs[p]))
    return groups


for deg in (90, 30, 150, 210, 270, 330, 60, 0):
    g = crossings(deg)
    print("ray %3d deg: %s" % (deg, "  ".join("r=%.1f..%.1f" % t for t in g)))
    print("           (in): %s" % "  ".join("%.3f..%.3f" % (t[0] / SCALE, t[1] / SCALE) for t in g))
