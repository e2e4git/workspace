# -*- coding: utf-8 -*-
"""
extract_outline.py — produce the exact 2D outline of the part from the
drawing:

  * the toothed outer profile           (one closed polyline)
  * the outline of one window           (one closed polyline)

Both are written to JSON so the FreeCAD build script can turn them into
B-splines.
"""
import json
import math

import numpy as np
from PIL import Image
from scipy import ndimage

IMG = "/workspace/FreeCAD_Models/drawing_profile_only.png"
OUT = "/workspace/FreeCAD_Models/profile_points.json"
CX, CY = 455.5, 366.0

A = np.array(Image.open(IMG).convert("L"))
INK = A < 200
H, W = INK.shape

# ------------------------------------------------------------------ #
# 1. window outline: flood fill the enclosed opening
# ------------------------------------------------------------------ #
walls = ndimage.binary_dilation(INK, np.ones((3, 3)))
free = ~walls
lab, n = ndimage.label(free)

print("free regions:", n)
for i in range(1, n + 1):
    ys, xs = np.nonzero(lab == i)
    if len(xs) < 200:
        continue
    r = np.hypot(xs.mean() - CX, ys.mean() - CY)
    th = math.degrees(math.atan2(CY - ys.mean(), xs.mean() - CX)) % 360
    print("  region %2d  size %7d  bbox x %3d..%3d y %3d..%3d  "
          "centroid r=%.0f th=%.0f" %
          (i, len(xs), xs.min(), xs.max(), ys.min(), ys.max(), r, th))

# the window at 270 deg: search for a small region whose centroid is near
# theta = 270 and r ~ 130
best = None
for i in range(1, n + 1):
    ys, xs = np.nonzero(lab == i)
    if len(xs) < 200:
        continue
    r = math.hypot(xs.mean() - CX, ys.mean() - CY)
    th = math.degrees(math.atan2(CY - ys.mean(), xs.mean() - CX)) % 360
    if abs(th - 270) < 45 and 60 < r < 220:
        if best is None or len(xs) < best[1]:
            best = (i, len(xs))
print("window region candidate:", best)

reg = (lab == best[0])
# outline = ink pixels on the border of the region
er = ndimage.binary_erosion(reg, np.ones((3, 3)))
border = reg & ~er
ys, xs = np.nonzero(border)
pts = sorted(zip(xs.astype(float), ys.astype(float)),
             key=lambda p: math.atan2(CY - p[1], p[0] - CX))
window_pts = [[round(p[0], 1), round(p[1], 1)] for p in pts]
print("window outline points:", len(window_pts))

# ------------------------------------------------------------------ #
# 2. toothed outer profile: outermost ink per angle
# ------------------------------------------------------------------ #
tooth = []
for deg in range(0, 3600):
    a = math.radians(deg / 10.0)
    rmax = None
    r = 240.0
    while r < 345:
        x = int(round(CX + r * math.cos(a)))
        y = int(round(CY - r * math.sin(a)))
        if 0 <= x < W and 0 <= y < H and INK[y, x]:
            rmax = r
            break
        r += 0.25
    if rmax is not None:
        tooth.append([round(deg / 10.0, 1), round(rmax, 2)])
print("tooth profile samples:", len(tooth))
rr = [p[1] for p in tooth]
print("  radius range: %.1f .. %.1f px" % (min(rr), max(rr)))

# count teeth: number of local maxima
rads = np.array([p[1] for p in tooth])
rads_s = np.convolve(np.r_[rads[-60:], rads, rads[:60]], np.ones(61) / 61, "same")[60:-60]
n_teeth = 0
for i in range(len(rads_s)):
    if rads_s[i] > rads_s[i - 1] and rads_s[i] >= rads_s[(i + 1) % len(rads_s)]:
        n_teeth += 1
print("  detected teeth (smoothed maxima):", n_teeth)

# FFT to confirm
sp = np.abs(np.fft.rfft(rads - rads.mean()))
k = int(np.argmax(sp[3:80])) + 3
print("  FFT dominant harmonic: %d" % k)

json.dump({"window": window_pts, "tooth": tooth},
          open(OUT, "w"))
print("written", OUT)
