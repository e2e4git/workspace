# -*- coding: utf-8 -*-
"""clean_sketch.py — remove all annotation elements (text, dimension lines,
arrowheads) from the sketch and render the pure part geometry, with the
construction hexagon highlighted."""
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = "/workspace/src/drawings/Screenshot (2).png"
OUT = "/workspace/FreeCAD_Models/out/"
g = np.array(Image.open(SRC).convert("L"))
H, W = g.shape
m = g < 205

lab, n = ndimage.label(m, structure=np.ones((3, 3)))
objs = ndimage.find_objects(lab)
stats = ndimage.sum(m, lab, range(1, n + 1))

print("small components (possible text / arrowheads):")
for i in range(n):
    if stats[i] > 600:
        continue
    sl = objs[i]
    bb = (sl[1].start, sl[1].stop, sl[0].start, sl[0].stop)
    w = bb[1] - bb[0]
    h = bb[3] - bb[2]
    fill = stats[i] / max(1, w * h)
    print("   id=%3d area=%5d bbox x[%d..%d] y[%d..%d] w=%d h=%d fill=%.2f" %
          (i + 1, stats[i], bb[0], bb[1], bb[2], bb[3], w, h, fill))

# ---------------- erase annotations -----------------------------------------
clean = m.copy()
def erase(x0, y0, x1, y1):
    clean[max(0, y0):y1, max(0, x0):x1] = False

# text
erase(400, 85, 510, 113)     # 2.24 in
erase(398, 238, 502, 282)    # 1.94 in
erase(650, 205, 750, 250)    # 1.25 in (upper right)
erase(305, 392, 425, 448)    # 1.25 in (lower left)
erase(410, 605, 505, 648)    # 3.69 in
# 2.24 dimension line + extension lines
erase(330, 112, 582, 124)
erase(333, 100, 341, 160)
erase(573, 100, 581, 160)
# 1.94 dimension line
erase(449, 140, 463, 352)
# 3.69 dimension line + extension lines
erase(250, 641, 662, 651)
erase(253, 600, 262, 710)
erase(650, 600, 659, 710)
# 1.25 arrowheads (UR) + their shaft
erase(715, 186, 750, 214)
erase(628, 245, 660, 272)
erase(640, 240, 745, 250)
# 1.25 arrowheads (LL) + shaft
erase(310, 368, 335, 398)
erase(358, 452, 384, 482)
erase(313, 368, 380, 380)
erase(355, 450, 372, 480)

# keep the hexagon for reference (rendered blue)
CX, CY = 455.0, 365.0
R = 395.5
d = R * math.cos(math.radians(30))
yy, xx = np.nonzero(clean)
px = xx - CX
py = CY - yy
hexm = np.zeros(len(px), bool)
for a in range(30, 360, 60):
    nx, ny = math.cos(math.radians(a)), math.sin(math.radians(a))
    v1 = px * nx + py * ny - d
    v2 = -(px * nx + py * ny) - d
    hexm |= (np.abs(v1) < 2.5) | (np.abs(v2) < 2.5)

rgb = np.full((H, W, 3), 255, np.uint8)
ys, xs = np.nonzero(clean)
rgb[ys[~hexm], xs[~hexm]] = (0, 0, 0)
rgb[ys[hexm], xs[hexm]] = (200, 60, 60)
Image.fromarray(rgb).save(OUT + "sketch_clean.png")

# also a 2x zoom of the inner region
im = Image.open(OUT + "sketch_clean.png").crop((150, 20, 760, 710)).resize((1220, 1380), Image.LANCZOS)
im.save(OUT + "sketch_clean_inner.png")
print("\nsaved clean renders")
