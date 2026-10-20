# -*- coding: utf-8 -*-
"""analyze_photo3.py — polar analysis of the photo with the elliptical
foreshortening removed. Gives the true (circular) geometry of the part."""
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = "/workspace/src/drawings/Screenshot (3).png"
OUT = "/workspace/FreeCAD_Models/out/"
rgb = np.array(Image.open(SRC).convert("RGB")).astype(int)
H, W, _ = rgb.shape
R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
mx, mn = rgb.max(axis=2), rgb.min(axis=2)
sat = mx - mn
wood = (sat > 25) & (R > B + 10) & (mx < 250)
wood = ndimage.binary_closing(wood, np.ones((3, 3)))
lab, n = ndimage.label(wood, np.ones((3, 3)))
sizes = ndimage.sum(wood, lab, range(1, n + 1))
gid = int(np.argmax(sizes)) + 1
wood = (lab == gid)                      # NOT filled -> windows are holes

ys, xs = np.nonzero(wood)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
k = (x1 - x0) / float(y1 - y0)            # vertical compression factor
CX, CY = (x0 + x1) / 2.0, (y0 + y1) / 2.0
print("bbox x[%d..%d] y[%d..%d] k=%.4f  centre=(%.1f,%.1f)" % (x0, x1, y0, y1, k, CX, CY))

# ---- polar resampling (corrected) -----------------------------------------
NA, NR = 1440, 700
RMAX = 360.0
th = np.linspace(0, 2 * math.pi, NA, endpoint=False)
rr = np.linspace(0, RMAX, NR)
TH, RR = np.meshgrid(th, rr, indexing="ij")
# apparent radius for a true radius r at angle t with vertical compression k
r_app = RR / np.sqrt(np.cos(TH) ** 2 + (k * np.sin(TH)) ** 2)
X = np.rint(CX + r_app * np.cos(TH)).astype(int)
Y = np.rint(CY - r_app * np.sin(TH)).astype(int)
ok = (X >= 0) & (X < W) & (Y >= 0) & (Y < H)
polar_wood = np.zeros((NA, NR), bool)
polar_wood[ok] = wood[Y[ok], X[ok]]
np.save(OUT + "polar_wood.npy", polar_wood)

r_out = np.zeros(NA)
for i in range(NA):
    idx = np.nonzero(polar_wood[i])[0]
    r_out[i] = rr[idx[-1]] if len(idx) else 0.0
print("\nouter profile: tip R=%.1f  root R=%.1f  (mean top 3%%=%.1f)" %
      (r_out.max(), r_out.min(), np.sort(r_out)[-int(0.03 * NA):].mean()))

# tooth count: FFT of the profile
sig = r_out - r_out.mean()
F = np.abs(np.fft.rfft(sig))
for kk in range(20, 90):
    if F[kk] > F[kk - 1] and F[kk] >= F[kk + 1] and F[kk] > 0.25 * F.max():
        print("   harmonic %d (amp %.1f) -> %d teeth" % (kk, F[kk], kk))

# ---- window openings ------------------------------------------------------
bg = ~wood
lab2, n2 = ndimage.label(bg, np.ones((3, 3)))
border = set(lab2[0, :]) | set(lab2[-1, :]) | set(lab2[:, 0]) | set(lab2[:, -1])
holes = []
for i in range(1, n2 + 1):
    if i in border:
        continue
    area = int((lab2 == i).sum())
    if area < 150:
        continue
    yy, xx = np.nonzero(lab2 == i)
    holes.append((area, i, xx, yy))
holes.sort(key=lambda t: -t[0])
print("\nopenings found: %d" % len(holes))
for area, i, xx, yy in holes:
    print("   id=%3d area=%7d bbox x[%d..%d] y[%d..%d] cen=(%.1f,%.1f)" %
          (i, area, xx.min(), xx.max(), yy.min(), yy.max(), xx.mean(), yy.mean()))

# ---- describe the 3 big windows in polar coordinates ----------------------
def polar_runs(theta_deg, half=2.0):
    """return the list of (r_start, r_end) of wood along that direction"""
    i = int((theta_deg % 360) / 360 * NA)
    band = polar_wood[(i - 2) % NA:(i + 3) % NA]
    col = band.mean(axis=0) > 0.5
    out = []
    s = None
    for j, v in enumerate(col):
        if v and s is None:
            s = j
        elif not v and s is not None:
            out.append((rr[s], rr[j - 1]))
            s = None
    if s is not None:
        out.append((rr[s], rr[-1]))
    return out

print("\nradial material runs (corrected polar):")
for a in range(0, 360, 15):
    print("  %3d deg : %s" % (a, " ".join("%.0f-%.0f" % t for t in polar_runs(a))))

# ---- spoke width measurement ---------------------------------------------
def window_span(theta_deg):
    """for a direction that crosses a window, return (r_in, r_out) of the hole"""
    i = int((theta_deg % 360) / 360 * NA)
    band = polar_wood[(i - 2) % NA:(i + 3) % NA]
    col = band.mean(axis=0) > 0.5
    gaps = []
    s = None
    for j, v in enumerate(col):
        if not v and s is None:
            s = j
        elif v and s is not None:
            gaps.append((rr[s], rr[j - 1]))
            s = None
    return gaps

for a in range(0, 360, 10):
    g = window_span(a)
    if g:
        print("  gap @%3d deg: %s" % (a, " ".join("%.0f-%.0f" % t for t in g)))
