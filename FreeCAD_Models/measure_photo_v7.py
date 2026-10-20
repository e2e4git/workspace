# -*- coding: utf-8 -*-
"""measure_photo_v7.py -- measure the real part on the photo with a proper
ellipse fit of the outer (tooth-tip) boundary, so that the perspective
foreshortening is removed correctly.

All results are given as fractions of the tooth-tip radius.
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
wood = (sat > 22) & (R > B + 8) & (mx < 252)
wood = ndimage.binary_closing(wood, np.ones((3, 3)))
lab, n = ndimage.label(wood, np.ones((3, 3)))
sizes = ndimage.sum(wood, lab, range(1, n + 1))
gid = int(np.argmax(sizes)) + 1
wood = (lab == gid)

# ---- outer boundary points -------------------------------------------------
er = ndimage.binary_erosion(wood, np.ones((3, 3)))
bnd = wood & ~er
ys, xs = np.nonzero(bnd)
# keep only the outer boundary (drop the window/bore boundaries): the outer
# boundary is the set of boundary pixels whose distance to the background
# "outside" is small; simpler: take points that are on the convex hull side.
# Use the fact that the outer boundary is the largest connected boundary loop.
bl, bn = ndimage.label(bnd, np.ones((3, 3)))
bs = ndimage.sum(bnd, bl, range(1, bn + 1))
oid = int(np.argmax(bs)) + 1
ys, xs = np.nonzero(bl == oid)
print("outer boundary points: %d" % len(xs))

# ---- direct least squares ellipse fit (Fitzgibbon) -------------------------
x = xs.astype(float)
y = ys.astype(float)
D = np.column_stack([x * x, x * y, y * y, x, y, np.ones_like(x)])
S = D.T @ D
C = np.zeros((6, 6))
C[0, 2] = C[2, 0] = 2.0
C[1, 1] = -1.0
w, v = np.linalg.eig(np.linalg.solve(S, C))
idx = np.argmax(np.real(w))
A, Bc, Cc, Dc, Ec, Fc = np.real(v[:, idx])
# ellipse parameters
den = Bc * Bc - 4 * A * Cc
cx = (2 * Cc * Dc - Bc * Ec) / den
cy = (2 * A * Ec - Bc * Dc) / den
num = 2 * (A * Ec * Ec + Cc * Dc * Dc + Fc * Bc * Bc - Bc * Dc * Ec - 4 * A * Cc * Fc)
s = math.sqrt((A - Cc) ** 2 + Bc * Bc)
a = math.sqrt(abs(num / (den * ((A + Cc) + s))))
b = math.sqrt(abs(num / (den * ((A + Cc) - s))))
print("ellipse: centre=(%.2f,%.2f)  a=%.2f  b=%.2f  b/a=%.4f"
      % (cx, cy, a, b, b / a))

# ---- corrected polar map ---------------------------------------------------
NA, NR = 1440, 720
RMAX = 1.05
th = np.linspace(0, 2 * math.pi, NA, endpoint=False)
rr = np.linspace(0, RMAX, NR)
TH, RR = np.meshgrid(th, rr, indexing="ij")
X = np.rint(cx + RR * a * np.cos(TH)).astype(int)
Y = np.rint(cy - RR * b * np.sin(TH)).astype(int)
ok = (X >= 0) & (X < W) & (Y >= 0) & (Y < H)
pw = np.zeros((NA, NR), bool)
pw[ok] = wood[Y[ok], X[ok]]
pw = ndimage.median_filter(pw.astype(np.uint8), size=(5, 1)).astype(bool)
np.save(OUT + "polar_wood_v7.npy", pw)

r_out = np.array([rr[np.nonzero(pw[i])[0][-1]] if pw[i].any() else 0.0
                  for i in range(NA)])
Rtip = np.percentile(r_out, 99.0)
Rroot = np.percentile(r_out, 1.0)
print("\nRtip=%.4f  Rroot=%.4f  depth=%.4f (%.3f Rtip)"
      % (Rtip, Rroot, Rtip - Rroot, (Rtip - Rroot) / Rtip))

# teeth: count local maxima of the outer profile
rs = ndimage.median_filter(r_out, 3)
thr = 0.5 * (rs.max() + rs.min())
peaks = [i for i in range(NA)
         if rs[i] > thr and rs[i] >= rs[(i - 1) % NA] and rs[i] > rs[(i + 1) % NA]]
merged = []
for p in peaks:
    if merged and (p - merged[-1]) % NA < 10:
        continue
    merged.append(p)
print("teeth (peak count) = %d" % len(merged))
sig = r_out - r_out.mean()
F = np.abs(np.fft.rfft(sig))
top = np.argsort(F[20:90])[::-1][:6] + 20
print("FFT top harmonics: %s" % ", ".join("%d(%.0f)" % (k, F[k]) for k in top))

# ---- radial material fraction ---------------------------------------------
frac = pw.mean(axis=0)
print("\nradial material fraction (r/Rtip : frac):")
for f in np.arange(0.0, 1.01, 0.02):
    j = int(f / RMAX * NR)
    print("  %.2f : %.2f" % (f, frac[j]))


def runs_at(fr, band=4):
    j = int(fr / RMAX * NR)
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
    rs_ = [t for t in runs_at(f) if (t[1] - t[0]) > 1.0]
    print("  %.2f : %s" % (f, "  ".join("%.1f..%.1f" % t for t in rs_)))

print("\nspoke width (linear, /Rtip) vs radius:")
for f in (0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65,
          0.70, 0.75, 0.78):
    rs_ = [t for t in runs_at(f) if 3.0 < (t[1] - t[0]) < 60.0]
    if not rs_:
        continue
    ws = [2 * f * math.sin(math.radians((t[1] - t[0]) / 2.0)) for t in rs_]
    print("  r=%.2f Rtip: %s   -> w=%.3f Rtip"
          % (f, "  ".join("%.1f..%.1f" % t for t in rs_), np.mean(ws)))

print("\nwindow radial extent along window axes:")
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
    print("  %3d deg : %s" % (a, "  ".join("%.3f..%.3f" % t for t in segs)))

# ---- bore ------------------------------------------------------------------
bg = ~wood
lab2, n2 = ndimage.label(bg, np.ones((3, 3)))
border = set(lab2[0, :]) | set(lab2[-1, :]) | set(lab2[:, 0]) | set(lab2[:, -1])
print("\nholes (windows + bore):")
for i in range(1, n2 + 1):
    if i in border:
        continue
    ar = int((lab2 == i).sum())
    if ar < 50:
        continue
    yy, xx = np.nonzero(lab2 == i)
    print("  area=%6d  bbox x[%d..%d] y[%d..%d]  cen=(%.1f,%.1f)  w=%d h=%d"
          % (ar, xx.min(), xx.max(), yy.min(), yy.max(),
             xx.mean(), yy.mean(), xx.max() - xx.min() + 1, yy.max() - yy.min() + 1))
