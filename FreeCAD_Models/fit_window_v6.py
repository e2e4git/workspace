# -*- coding: utf-8 -*-
"""fit_window_v6.py -- fit the window outline of the real part (photo).

The window is modelled as:
    outer arc  : circle R_rim  (centre = part centre)
    inner arc  : circle R_hub  (centre = part centre)
    two flanks : straight lines parallel to the spoke axis, offset +-w/2
    corners    : rounded, radius r_c
This script measures R_rim, R_hub, w and r_c from the photo.
"""
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = "/workspace/src/drawings/Screenshot (3).png"
rgb = np.array(Image.open(SRC).convert("RGB")).astype(float)
R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
mx, mn = rgb.max(axis=2), rgb.min(axis=2)
sat = mx - mn
wood = (sat > 22) & (R > B + 8) & (mx < 252)
wood = ndimage.binary_closing(wood, np.ones((3, 3)))
lab, n = ndimage.label(wood, np.ones((3, 3)))
sizes = ndimage.sum(wood, lab, range(1, n + 1))
gid = int(np.argmax(sizes)) + 1
wood = (lab == gid)

cx, cy, a, b = 377.71, 312.53, 334.63, 285.84
H, W = wood.shape

bg = ~wood
lab2, n2 = ndimage.label(bg, np.ones((3, 3)))
border = set(lab2[0, :]) | set(lab2[-1, :]) | set(lab2[:, 0]) | set(lab2[:, -1])
wins = []
for i in range(1, n2 + 1):
    if i in border:
        continue
    ar = int((lab2 == i).sum())
    if ar < 5000:
        continue
    yy, xx = np.nonzero(lab2 == i)
    wins.append((ar, xx, yy))
wins.sort(key=lambda t: -t[0])
print("windows: %d" % len(wins))

# normalised coordinates (R_tip = 1)
allpts = []
for ar, xx, yy in wins:
    u = (xx - cx) / a
    v = -(yy - cy) / b
    r = np.hypot(u, v)
    th = np.degrees(np.arctan2(v, u)) % 360
    allpts.append((r, th))
    print("  area=%6d  r range %.3f..%.3f  theta %.1f..%.1f"
          % (ar, r.min(), r.max(), th.min(), th.max()))

r = np.concatenate([p[0] for p in allpts])
th = np.concatenate([p[1] for p in allpts])

# outer arc: r > 0.72
m = r > 0.72
print("\nouter arc: r mean %.4f  median %.4f  (n=%d)"
      % (r[m].mean(), np.median(r[m]), m.sum()))
# inner arc: r < 0.30
m2 = r < 0.30
print("inner arc: r mean %.4f  median %.4f  (n=%d)"
      % (r[m2].mean(), np.median(r[m2]), m2.sum()))

# flanks: 0.40 < r < 0.68 -> distance from the spoke axis
# spoke axes at 90/210/330 deg; window axes at 30/150/270
m3 = (r > 0.40) & (r < 0.68)
# for each point, the angular distance to the nearest spoke axis
spoke = np.array([90.0, 210.0, 330.0])
d = np.abs(((th[:, None] - spoke[None, :] + 180) % 360) - 180)
dmin = d.min(axis=1)
# perpendicular distance to the spoke axis = r*sin(dmin)
perp = r * np.sin(np.radians(dmin))
print("\nflank distance from spoke axis (r 0.40..0.68):")
print("  mean %.4f  median %.4f  p10 %.4f  p90 %.4f"
      % (perp[m3].mean(), np.median(perp[m3]),
         np.percentile(perp[m3], 10), np.percentile(perp[m3], 90)))
print("  -> spoke width w = %.4f Rtip" % (2 * np.median(perp[m3])))

# corner radius: look at the transition between the outer arc and the flank
# points with 0.68 < r < 0.78 and angular distance to the spoke axis
m4 = (r > 0.66) & (r < 0.80)
print("\ncorner region (r 0.66..0.80): %d points" % m4.sum())
# fit a circle to the corner points near one corner
# take the top-left window's corner near the 90 deg spoke
sel = m4 & (th > 60) & (th < 90)
if sel.sum() > 10:
    uu = r[sel] * np.cos(np.radians(th[sel]))
    vv = r[sel] * np.sin(np.radians(th[sel]))
    A = np.column_stack([2 * uu, 2 * vv, np.ones_like(uu)])
    rhs = uu ** 2 + vv ** 2
    sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    ccx, ccy, c = sol
    rc = math.sqrt(c + ccx ** 2 + ccy ** 2)
    print("  corner circle: centre (%.3f,%.3f)  r=%.4f Rtip" % (ccx, ccy, rc))
