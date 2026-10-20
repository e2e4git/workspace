# -*- coding: utf-8 -*-
"""analyze_v9.py — flood-fill the sketch to isolate the 3 window openings and
trace their boundaries (dimension lines removed first)."""
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = "/workspace/src/drawings/Screenshot (2).png"
g = np.array(Image.open(SRC).convert("L"))
H, W = g.shape
m = g < 205

# ---- remove dimension / annotation elements --------------------------------
keep = m.copy()
def erase_mask(x0, y0, x1, y1):
    keep[y0:y1, x0:x1] = False
# vertical 1.94 dimension line + arrow (x 452..462, y 140..350)
erase_mask(450, 140, 464, 350)
# horizontal 2.24 dimension line + arrows (y 112..124, x 330..580)
erase_mask(330, 112, 580, 124)
# extension lines of 2.24 (x 335..339 and 574..579, y 100..160)
erase_mask(334, 100, 340, 160)
erase_mask(574, 100, 580, 160)
# "2.24 in" text
erase_mask(400, 88, 510, 112)
# "1.94 in" text
erase_mask(400, 240, 500, 280)
# "1.25 in" text (upper right)
erase_mask(640, 205, 740, 245)
# "1.25 in" text (lower left)
erase_mask(300, 400, 390, 440)
# "3.69 in" text
erase_mask(415, 612, 500, 648)
# 3.69 dimension line (y 644..650) and its extension lines (x 255..261, 651..657)
erase_mask(250, 640, 262, 710)
erase_mask(649, 640, 661, 710)
erase_mask(255, 644, 660, 650)
# arrows of 1.25 (upper right, diagonal) : remove by hough later if needed

# label background
bg = ~keep
lab, n = ndimage.label(bg, structure=np.ones((3, 3)))
border = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
regions = []
for i in range(1, n + 1):
    if i in border:
        continue
    area = int((lab == i).sum())
    if area < 300:
        continue
    ys, xs = np.nonzero(lab == i)
    regions.append(dict(id=i, area=area, bbox=(xs.min(), xs.max(), ys.min(), ys.max()),
                         cen=(xs.mean(), ys.mean())))
regions.sort(key=lambda r: -r["area"])
print("enclosed regions:")
for r in regions:
    print("   id=%3d area=%7d bbox x[%d..%d] y[%d..%d] centroid=(%.1f,%.1f)" %
          (r["id"], r["area"], r["bbox"][0], r["bbox"][1], r["bbox"][2], r["bbox"][3],
           r["cen"][0], r["cen"][1]))

# ---- trace boundary of the biggest region (top window) ---------------------
def trace(region_id):
    """Moore-neighbour contour of one labelled region -> list of (x,y)"""
    idx = np.nonzero(lab == region_id)
    pts = set(zip(idx[1].tolist(), idx[0].tolist()))
    start = min(pts, key=lambda p: (p[1], p[0]))
    nbrs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    cont = [start]
    prev = (-2, 0)
    cur = start
    for _ in range(400000):
        i = nbrs.index(prev) if prev in nbrs else 0
        nxt = None
        for k in range(8):
            d = nbrs[(i + 1 + k) % 8]
            c = (cur[0] + d[0], cur[1] + d[1])
            if c in pts:
                nxt = c
                prev = cur
                cur = c
                break
        if nxt is None:
            break
        if cur == start and len(cont) > 3:
            break
        cont.append(cur)
    return cont

if regions:
    top = regions[0]
    cont = trace(top["id"])
    print("\ntop region contour points: %d" % len(cont))
    # print every 10th point
    step = max(1, len(cont) // 120)
    s = " ".join("(%d,%d)" % (c[0], c[1]) for c in cont[::step])
    print(s)
    np.save("/workspace/FreeCAD_Models/out/sketch_topregion.npy", np.array(cont))
