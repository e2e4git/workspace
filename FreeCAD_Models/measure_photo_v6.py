# -*- coding: utf-8 -*-
"""measure_photo_v6.py -- careful measurement of the real part on the photo.

Segments the wooden part, removes the elliptical foreshortening, and reports
every radius as a fraction of the tooth-tip radius:
    tip / root circles, rim inner circle, hub, bore, spoke width vs radius,
    window inner boundary.
"""
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = "/workspace/src/drawings/Screenshot (3).png"
OUT = "/workspace/FreeCAD_Models/out/"

rgb = np.array(Image.open(SRC).convert("RGB")).astype(float)
H, W, _ = rgb.shape
R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
mx, mn = rgb.max(axis=2), rgb.min(axis=2)
sat = mx - mn
# wood: brownish (R > B), reasonably saturated, not blown out
wood = (sat > 22) & (R > B + 8) & (mx < 252)
wood = ndimage.binary_closing(wood, np.ones((3, 3)))
wood = ndimage.binary_opening(wood, np.ones((3, 3)))
lab, n = ndimage.label(wood, np.ones((3, 3)))
sizes = ndimage.sum(wood, lab, range(1, n + 1))
gid = int(np.argmax(sizes)) + 1
wood = (lab == gid)
# fill small holes inside the wood (lighting), keep the real windows
filled = ndimage.binary_fill_holes(wood)
holes = filled & ~wood
hl, hn = ndimage.label(holes, np.ones((3, 3)))
for i in range(1, hn + 1):
    a = int((hl == i).sum())
    if a < 400:                      # small speck -> wood
        wood |= (hl == i)

ys, xs = np.nonzero(wood)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
k = (x1 - x0) / float(y1 - y0)
CX, CY = (x0 + x1) / 2.0, (y0 + y1) / 2.0
print("bbox x[%d..%d] y[%d..%d]  squash k=%.4f  centre=(%.1f,%.1f)"
      % (x0, x1, y0, y1, k, CX, CY))

# ---- corrected polar map ---------------------------------------------------
NA, NR = 1440, 720
RMAX = 360.0
th = np.linspace(0, 2 * math.pi, NA, endpoint=False)
rr = np.linspace(0, RMAX, NR)
TH, RR = np.meshgrid(th, rr, indexing="ij")
r_app = RR / np.sqrt(np.cos(TH) ** 2 + (k * np.sin(TH)) ** 2)
X = np.rint(CX + r_app * np.cos(TH)).astype(int)
Y = np.rint(CY - r_app * np.sin(TH)).astype(int)
ok = (X >= 0) & (X < W) & (Y >= 0) & (Y < H)
pw = np.zeros((NA, NR), bool)
pw[ok] = wood[Y[ok], X[ok]]
# median filter along angle to kill speckle
pw = ndimage.median_filter(pw.astype(np.uint8), size=(5, 1)).astype(bool)
np.save(OUT + "polar_wood_v6.npy", pw)

r_out = np.array([rr[np.nonzero(pw[i])[0][-1]] if pw[i].any() else 0.0
                  for i in range(NA)])
Rtip = np.percentile(r_out, 99.5)
Rroot = np.percentile(r_out, 1.0)
print("\nRtip=%.1f  Rroot=%.1f  depth=%.1f (%.3f Rtip)"
      % (Rtip, Rroot, Rtip - Rroot, (Rtip - Rroot) / Rtip))

sig = r_out - r_out.mean()
F = np.abs(np.fft.rfft(sig))
best = max(range(20, 90), key=lambda i: F[i])
print("teeth (FFT peak) = %d   (amp %.1f)" % (best, F[best]))

# ---- bore ------------------------------------------------------------------
# the bore is the small hole at the centre: look at the polar map near r=0
col0 = pw[:, :int(0.2 * Rtip / RMAX * NR)].mean(axis=1)
print("material fraction near centre (r<0.2Rtip): %.2f" % col0.mean())
# radial profile of material fraction averaged over all angles
frac = pw.mean(axis=0)
print("\nradial material fraction (r/Rtip : frac):")
for f in np.arange(0.0, 1.01, 0.02):
    j = int(f * Rtip / RMAX * NR)
    print("  %.2f : %.2f" % (f, frac[j]))

# ---- angular runs at radii -------------------------------------------------
def runs_at(fr, band=4):
    j = int(fr * Rtip / RMAX * NR)
    col = pw[:, max(0, j - band):j + band + 1].mean(axis=1) > 0.5
    out, s = [], None
    for i, v in enumerate(col):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s * 360.0 / NA, (i - 1) * 360.0 / NA))
            s = None
    if s is not None:
        out.append((s * 360.0 / NA, (NA - 1) * 360.0 / NA))
    return out


print("\nmaterial angular runs (deg) at r/Rtip:")
for f in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55,
          0.60, 0.65, 0.70, 0.75, 0.78, 0.80, 0.82, 0.85, 0.90):
    rs = runs_at(f)
    rs = [t for t in rs if (t[1] - t[0]) > 1.0]
    print("  %.2f : %s" % (f, "  ".join("%.1f..%.1f" % t for t in rs)))

# ---- spoke width (linear) vs radius ---------------------------------------
print("\nspoke width (px and /Rtip) vs radius:")
for f in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60,
          0.65, 0.70, 0.75, 0.78):
    rs = runs_at(f)
    rs = [t for t in rs if 3.0 < (t[1] - t[0]) < 60.0]
    if not rs:
        continue
    r = f * Rtip
    ws = [2 * r * math.sin(math.radians((t[1] - t[0]) / 2.0)) for t in rs]
    print("  r=%.0f (%.2f Rtip): %s   -> w=%.1f px = %.3f Rtip"
          % (r, f, "  ".join("%.1f..%.1f" % t for t in rs),
             np.mean(ws), np.mean(ws) / Rtip))

# ---- window inner boundary along the window axes --------------------------
print("\nwindow radial extent along window axes (deg):")
for a in (30, 150, 270):
    i = int(a / 360.0 * NA)
    col = pw[(i - 6) % NA:(i + 7) % NA].mean(axis=0) > 0.5
    segs, s = [], None
    for j, v in enumerate(col):
        if v and s is None:
            s = j
        elif not v and s is not None:
            segs.append((rr[s], rr[j - 1]))
            s = None
    if s is not None:
        segs.append((rr[s], rr[-1]))
    print("  %3d deg : %s" % (a, "  ".join("%.0f..%.0f (%.3f..%.3f Rtip)"
                                           % (t[0], t[1], t[0] / Rtip, t[1] / Rtip)
                                           for t in segs)))

# ---- bore radius -----------------------------------------------------------
# scan the centre: the bore is the only hole near the centre
i0 = int(0.0 / 360.0 * NA)
print("\ncentre column material runs (r/Rtip):")
col = pw.mean(axis=0) > 0.5
segs, s = [], None
for j, v in enumerate(col):
    if v and s is None:
        s = j
    elif not v and s is not None:
        segs.append((rr[s], rr[j - 1]))
        s = None
if s is not None:
    segs.append((rr[s], rr[-1]))
print("  " + "  ".join("%.0f..%.0f (%.3f..%.3f)" % (t[0], t[1], t[0] / Rtip, t[1] / Rtip)
                       for t in segs))
