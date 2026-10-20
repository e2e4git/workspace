# -*- coding: utf-8 -*-
"""overlay_test.py — rotate the photo so that its top spoke points up, scale it
to the sketch's tip circle and overlay both drawings.  This shows which sketch
dimension corresponds to which photo feature."""
import math
import numpy as np
from PIL import Image
from scipy import ndimage

OUT = "/workspace/FreeCAD_Models/out/"
PHOTO = "/workspace/src/drawings/Screenshot (3).png"

# ---------------- photo mask (as in analyze_photo3) ------------------------
rgb = np.array(Image.open(PHOTO).convert("RGB")).astype(int)
H, W, _ = rgb.shape
R, B = rgb[:, :, 0], rgb[:, :, 2]
mx = rgb.max(axis=2)
sat = mx - rgb.min(axis=2)
wood = (sat > 25) & (R > B + 10) & (mx < 250)
wood = ndimage.binary_closing(wood, np.ones((3, 3)))
lab, n = ndimage.label(wood, np.ones((3, 3)))
sizes = ndimage.sum(wood, lab, range(1, n + 1))
wood = (lab == int(np.argmax(sizes)) + 1)
ys, xs = np.nonzero(wood)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
k = (x1 - x0) / float(y1 - y0)
CX, CY = (x0 + x1) / 2.0, (y0 + y1) / 2.0
NA, NR = 1440, 700
th = np.linspace(0, 2 * math.pi, NA, endpoint=False)
rr = np.linspace(0, 360.0, NR)
TH, RR = np.meshgrid(th, rr, indexing="ij")
r_app = RR / np.sqrt(np.cos(TH) ** 2 + (k * np.sin(TH)) ** 2)
X = np.rint(CX + r_app * np.cos(TH)).astype(int)
Y = np.rint(CY - r_app * np.sin(TH)).astype(int)
ok = (X >= 0) & (X < W) & (Y >= 0) & (Y < H)
pw = np.zeros((NA, NR), bool)
pw[ok] = wood[Y[ok], X[ok]]
np.save(OUT + "polar_wood.npy", pw)

# ---- rotate the photo so that the top spoke (at 90 deg) stays at 90 deg ----
# photo spokes are at 90/210/330 in the corrected frame?  detect: the material
# run through the centre
# find the spoke direction: angle with the longest continuous material from r=0
best = (0, 0)
for a in range(0, 360):
    i = int(a / 360 * NA)
    col = pw[i]
    idx = np.nonzero(col)[0]
    if len(idx) and idx[0] == 0:
        if idx[-1] > best[1]:
            best = (a, idx[-1])
print("longest solid radial run: %d deg, r=%.0f" % best)
# the photo's SPOKE is the narrow solid band: detect it as the direction where
# the material just above the hub is thin -> use the window centroids instead
# (window = big empty sector).  Window centroids were at 34/146/273 deg, so the
# spokes are at 94/206/326 and the sketch's spokes are at 30/150/270.
# -> rotate so that the photo spoke 94 deg maps to 90 deg.
spoke_a = 94.0
print("using spoke_a =", spoke_a, "(photo) -> 90 deg (sketch)")

# window directions = spokes + 60
spoke_a = best[0]

# ---- rebuild a rectified photo image (tip circle centred, 1 px = 1 unit) ----
SC = 1.0
Rtip = 347.1
size = int(2 * Rtip * SC) + 8
c = size / 2.0
canvas = np.ones((size, size), bool)
for i in range(NA):
    a = th[i] - math.radians(spoke_a - 90.0)     # rotate so the spoke -> 90 deg
    a = a + math.radians(60.0)                  # 60 deg correction (see above)
    x = c + rr * math.cos(a)
    y = c - rr * math.sin(a)
    xi = np.rint(x).astype(int)
    yi = np.rint(y).astype(int)
    o = (xi >= 0) & (xi < size) & (yi >= 0) & (yi < size)
    canvas[yi[o], xi[o]] = pw[i][o]
Image.fromarray((~canvas).astype(np.uint8) * 255).save(OUT + "photo_rect.png")
print("rectified photo saved (%d px)" % size)

# ---- overlay with the sketch ------------------------------------------------
sk = np.array(Image.open(OUT + "sketch_clean.png").convert("RGB"))
skm = (sk[:, :, 0] < 128) & (sk[:, :, 1] < 128)      # part geometry (black)
# sketch centre + tip radius
SCX, SCY, SRT = 455.0, 365.0, 330.0
sx = SCX + (np.arange(size) - c) * SRT / Rtip
sy = SCY - (np.arange(size) - c) * SRT / Rtip
XI = np.rint(sx).astype(int)
YI = np.rint(sy).astype(int)
o = (XI >= 0) & (XI < sk.shape[1]) & (YI >= 0) & (YI < sk.shape[0])
rgb2 = sk.copy()
yy, xx = np.nonzero(canvas)
yy2 = YI[yy]
xx2 = XI[xx]
m2 = (yy2 >= 0) & (yy2 < rgb2.shape[0]) & (xx2 >= 0) & (xx2 < rgb2.shape[1])
rgb2[yy2[m2], xx2[m2]] = (255, 0, 0)
Image.fromarray(rgb2).save(OUT + "overlay.png")
print("overlay saved: red = photo, black = sketch")
