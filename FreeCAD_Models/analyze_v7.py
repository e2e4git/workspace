# -*- coding: utf-8 -*-
"""
analyze_v7.py — precise measurement of the 5 sketch dimensions + tooth profile.
Strategy: dimension lines are light grey (gray>170) while geometry is black.
We therefore use two thresholds and report runs for the dimension rows.
"""
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SKETCH = "/workspace/src/drawings/Screenshot (2).png"
g = np.array(Image.open(SKETCH).convert("L"))
H, W = g.shape
print("sketch %dx%d   gray hist:" % (W, H))
hist, edges = np.histogram(g, bins=[0, 60, 100, 140, 170, 200, 225, 240, 256])
print("  ", list(zip(edges[:-1].tolist(), hist.tolist())))

m_dark = g < 170      # black geometry
m_light = (g >= 170) & (g < 245)   # grey lines (dimensions)


def runs(idx):
    out = []
    if len(idx) == 0:
        return out
    s = p = idx[0]
    for v in idx[1:]:
        if v != p + 1:
            out.append((int(s), int(p)))
            s = v
        p = v
    out.append((int(s), int(p)))
    return out


def row_runs(mask, y, x0=0, x1=None):
    x1 = mask.shape[1] if x1 is None else x1
    return runs(np.nonzero(mask[y, x0:x1])[0] + x0)


def col_runs(mask, x, y0=0, y1=None):
    y1 = mask.shape[0] if y1 is None else y1
    return runs(np.nonzero(mask[y0:y1, x])[0] + y0)


print("\n### dimension rows (light grey) ###")
for y in range(108, 126):
    r = row_runs(m_light, y)
    if r:
        print("  y=%3d light: %s" % (y, r))
print()
for y in range(636, 654):
    r = row_runs(m_light, y)
    if r:
        print("  y=%3d light: %s" % (y, r))
print()
for x in range(448, 466):
    r = col_runs(m_light, x)
    if r:
        print("  x=%3d light col: %s" % (x, r))

print("\n### dark rows near the 2.24 dimension ###")
for y in range(108, 126):
    r = row_runs(m_dark, y)
    if r:
        print("  y=%3d dark: %s" % (y, r))
print("\n### dark rows near the 3.69 dimension ###")
for y in range(636, 654):
    r = row_runs(m_dark, y)
    if r:
        print("  y=%3d dark: %s" % (y, r))

# ------------------------------------------------------------------ hexagon --
CX, CY = 455.0, 365.0
R_HEX = 395.5
verts = [(CX + R_HEX * math.cos(math.radians(a)), CY - R_HEX * math.sin(math.radians(a)))
         for a in range(0, 360, 60)]
print("\nhexagon vertices:", [(round(x, 1), round(y, 1)) for x, y in verts])
# edge equations:  n . p = d  with n = unit normal at 30/90/150/210/270/330
d_hex = R_HEX * math.cos(math.radians(30))     # 342.45
normals = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(30, 360, 60)]
yy, xx = np.nonzero(m_dark | m_light)
px = xx - CX
py = CY - yy
mask_noh = np.zeros(len(px), bool)
for (nx, ny) in normals:
    dist = px * nx + py * ny - d_hex
    mask_noh |= (np.abs(dist) < 2.2)
    dist2 = -(px * nx + py * ny) - d_hex
    mask_noh |= (np.abs(dist2) < 2.2)
print("hexagon pixels removed:", mask_noh.sum(), "of", len(px))

keep = ~mask_noh
kpx, kpy = px[keep], py[keep]
# polar profile of the remaining (teeth) profile
ang = np.degrees(np.arctan2(kpy, kpx)) % 360
rad = np.hypot(kpx, kpy)
bins = np.arange(0, 361, 1.0)
ti = np.digitize(ang, bins) - 1
rmax = np.full(361, np.nan)
rmin = np.full(361, np.nan)
for i in range(361):
    sel = ti == i
    if sel.sum():
        rmax[i] = rad[sel].max()
        rmin[i] = rad[sel].min()
print("\n=== tooth-only outer profile (1 deg bins) ===")
for i in range(0, 360, 10):
    vals = ", ".join("%5.1f" % rmax[j] for j in range(i, i + 10))
    print("  %3d-%3d: %s" % (i, i + 9, vals))
print("  tooth profile max=%.1f  min=%.1f" % (np.nanmax(rmax), np.nanmin(rmax)))
np.save("/workspace/FreeCAD_Models/out/sketch_teeth_rmax.npy", rmax)
np.save("/workspace/FreeCAD_Models/out/sketch_teeth_rmin.npy", rmin)
