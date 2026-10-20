# -*- coding: utf-8 -*-
"""measure_dims.py — find the arrowheads of the 5 dimensions in the sketch and
compute the exact pixel length each one measures."""
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = "/workspace/src/drawings/Screenshot (2).png"
g = np.array(Image.open(SRC).convert("L"))
m = g < 205
H, W = m.shape
lab, n = ndimage.label(m, np.ones((3, 3)))
sizes = ndimage.sum(m, lab, range(1, n + 1))
objs = ndimage.find_objects(lab)

print("candidate arrowheads (solid, elongated, 60..400 px):")
heads = []
for i in range(n):
    if not (60 <= sizes[i] <= 400):
        continue
    sl = objs[i]
    x0, x1 = sl[1].start, sl[1].stop
    y0, y1 = sl[0].start, sl[0].stop
    w, h = x1 - x0, y1 - y0
    fill = sizes[i] / float(w * h)
    if fill < 0.55:          # solid triangle
        continue
    ys, xs = np.nonzero(lab == i + 1)
    print("   id=%3d area=%4d bbox x[%3d..%3d] y[%3d..%3d] w=%2d h=%2d fill=%.2f" %
          (i + 1, sizes[i], x0, x1, y0, y1, w, h, fill))
    heads.append((i + 1, x0, x1, y0, y1, xs, ys))

# the arrowhead tip = the extreme vertex of the filled triangle
def tip_of(xs, ys, direction):
    """direction: unit vector pointing from the tail to the tip"""
    p = np.stack([xs, ys], 1).astype(float)
    t = p @ direction
    k = int(np.argmax(t))
    return p[k]

for (i, x0, x1, y0, y1, xs, ys) in heads:
    cx, cy = xs.mean(), ys.mean()
    # the tip is the vertex farthest from the centre of mass in one of 2
    # opposite directions; report the extreme point along the major axis
    p = np.stack([xs, ys], 1).astype(float)
    c = p.mean(axis=0)
    u, s, vt = np.linalg.svd(p - c, full_matrices=False)
    d = vt[0]
    tt = (p - c) @ d
    e1, e2 = p[int(np.argmax(tt))], p[int(np.argmin(tt))]
    print("   id=%3d  ends: %s  %s   (len %.1f)" %
          (i + 1, tuple(e1.astype(int)), tuple(e2.astype(int)),
           np.hypot(*(e1 - e2))))
