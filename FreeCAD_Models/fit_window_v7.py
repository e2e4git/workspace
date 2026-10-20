# -*- coding: utf-8 -*-
"""fit_window_v7.py -- measure the window outline of the real part (photo).

For each of the three windows:
  R_rim  = max radius of the window boundary (outer arc)
  R_hub  = min radius of the window boundary (inner arc)
  w      = 2 * min perpendicular distance of the flank points to the spoke axis
  r_c    = corner radius (circle fitted to the corner points)
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

spoke = np.array([90.0, 210.0, 330.0])
res = []
for ar, xx, yy in wins:
    u = (xx - cx) / a
    v = -(yy - cy) / b
    r = np.hypot(u, v)
    th = np.degrees(np.arctan2(v, u)) % 360
    # window axis = the mean angle (circular)
    ang = np.radians(th)
    wax = math.degrees(math.atan2(np.sin(ang).mean(), np.cos(ang).mean())) % 360
    # outer arc
    m_out = r > 0.75
    R_rim = np.percentile(r[m_out], 90)
    # inner arc
    m_in = r < 0.30
    R_hub = np.percentile(r[m_in], 10)
    # flanks: points between 0.40 and 0.70, distance to the nearest spoke axis
    m_f = (r > 0.40) & (r < 0.70)
    d = np.abs(((th[:, None] - spoke[None, :] + 180) % 360) - 180)
    dmin = d.min(axis=1)
    perp = r * np.sin(np.radians(dmin))
    w = 2 * np.percentile(perp[m_f], 2)
    # corner: points near the outer corner (r 0.70..0.80, close to the spoke)
    m_c = (r > 0.70) & (r < 0.80) & (dmin < 20)
    rc = float('nan')
    if m_c.sum() > 20:
        uu = r[m_c] * np.cos(np.radians(th[m_c]))
        vv = r[m_c] * np.sin(np.radians(th[m_c]))
        A = np.column_stack([2 * uu, 2 * vv, np.ones_like(uu)])
        rhs = uu ** 2 + vv ** 2
        sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
        ccx, ccy, c = sol
        rc = math.sqrt(max(c + ccx ** 2 + ccy ** 2, 0))
    res.append((R_rim, R_hub, w, rc, wax))
    print("window axis %5.1f deg : R_rim %.4f  R_hub %.4f  w %.4f  r_corner %.4f"
          % (wax, R_rim, R_hub, w, rc))

arr = np.array([t[:4] for t in res])
print("\nMEAN: R_rim %.4f  R_hub %.4f  w %.4f  r_corner %.4f"
      % tuple(arr.mean(axis=0)))
print("R_rim/R_tip = %.4f   R_hub/R_tip = %.4f   w/R_tip = %.4f"
      % (arr[:, 0].mean(), arr[:, 1].mean(), arr[:, 2].mean()))
