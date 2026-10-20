# -*- coding: utf-8 -*-
"""analyze_photo2.py — rigorous photo measurement.
  1. segment the wooden gear (colour based)
  2. estimate the photo's elliptical foreshortening and correct it
  3. measure: tip / root circles, tooth count, window openings, spoke width,
     hub, bore
  4. export the corrected image for visual check
"""
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
wood = (lab == gid)
wood = ndimage.binary_fill_holes(wood)     # closes the 3 windows
ys, xs = np.nonzero(wood)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
print("gear outer bbox x[%d..%d] y[%d..%d]  w=%d h=%d  ratio=%.4f" %
      (x0, x1, y0, y1, x1 - x0, y1 - y0, (y1 - y0) / (x1 - x0)))

im = Image.open(SRC).convert("RGB")
arr = np.array(im)
out = arr.copy()
out[wood] = (0, 0, 0)
out[~wood] = (255, 255, 255)
Image.fromarray(out).save(OUT + "photo_mask2.png")

# foreshortening correction: scale y so the outline becomes a circle
k = (x1 - x0) / float(y1 - y0)
print("vertical stretch correction k=%.4f" % k)
CX, CY = (x0 + x1) / 2.0, (y0 + y1) / 2.0
corr = np.array(Image.fromarray(out).resize(
    (W, int(H * k)), Image.LANCZOS))          # stretch vertically
Image.fromarray(corr).save(OUT + "photo_corr.png")
print("corrected image size", corr.shape)
np.save(OUT + "photo_mask.npy", wood)
