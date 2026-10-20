# -*- coding: utf-8 -*-
"""fit_sketch_curves.py — thin the cleaned sketch, split it into branches and
fit every branch with a line or a circle, so the part geometry can be
reconstructed exactly."""
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = "/workspace/FreeCAD_Models/out/sketch_clean.png"
OUT = "/workspace/FreeCAD_Models/out/"
rgb = np.array(Image.open(SRC).convert("RGB"))
H, W, _ = rgb.shape
black = (rgb[:, :, 0] < 128) & (rgb[:, :, 1] < 128)
mask = black.copy()
print("black px", mask.sum())


def thin(img):
    img = img.astype(np.uint8).copy()
    changed = True
    it = 0
    while changed and it < 200:
        changed = False
        it += 1
        for step in (0, 1):
            P = np.pad(img, 1)
            p2 = P[0:-2, 1:-1]
            p3 = P[0:-2, 2:]
            p4 = P[1:-1, 2:]
            p5 = P[2:, 2:]
            p6 = P[2:, 1:-1]
            p7 = P[2:, 0:-2]
            p8 = P[1:-1, 0:-2]
            p9 = P[0:-2, 0:-2]
            B = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            A = np.zeros_like(img)
            for i in range(8):
                A += ((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8)
            if step == 0:
                cond = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & \
                       ((p2 * p4 * p6) == 0) & ((p4 * p6 * p8) == 0)
            else:
                cond = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & \
                       ((p2 * p4 * p8) == 0) & ((p2 * p6 * p8) == 0)
            if cond.any():
                img[cond] = 0
                changed = True
    return img.astype(bool)


skel = thin(mask)
print("skeleton px", skel.sum())
ys, xs = np.nonzero(skel)
nbr = np.zeros((H, W), np.uint8)
for dy in (-1, 0, 1):
    for dx in (-1, 0, 1):
        if dy == 0 and dx == 0:
            continue
        nbr += np.roll(np.roll(skel, dy, 0), dx, 1).astype(np.uint8)
nbr = nbr * skel
ends = np.argwhere(skel & (nbr == 1))
juncs = np.argwhere(skel & (nbr >= 3))
print("endpoints %d  junctions %d" % (len(ends), len(juncs)))

visited = set()
branches = []


def walk(start, first):
    pts = [start, first]
    visited.add((start[1], start[0]))
    visited.add((first[1], first[0]))
    cur = first
    prev = start
    while True:
        y, x = cur
        best = None
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and skel[ny, nx] and (nx, ny) not in visited:
                    best = (ny, nx)
                    break
            if best:
                break
        if best is None:
            break
        if nbr[best] >= 3 and len(pts) > 2:
            break
        visited.add((best[1], best[0]))
        pts.append(best)
        prev, cur = cur, best
    return pts


for (y, x) in ends:
    if (x, y) in visited:
        continue
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and skel[ny, nx] and (nx, ny) not in visited:
                branches.append(walk((y, x), (ny, nx)))
                break
        else:
            continue
        break
print("branches from endpoints:", len(branches))


def fit_line(P):
    x = P[:, 0].astype(float)
    y = P[:, 1].astype(float)
    A = np.stack([x, y, np.ones(len(x))], 1)
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ sol
    return sol, float(np.sqrt((res ** 2).mean()))


def fit_circle(P):
    x = P[:, 0].astype(float)
    y = P[:, 1].astype(float)
    A = np.stack([x, y, np.ones(len(x))], 1)
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = math.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 1e-9))
    res = np.hypot(x - cx, y - cy) - r
    return (cx, cy, r), float(np.sqrt((res ** 2).mean()))


out = []
for i, b in enumerate(branches):
    if len(b) < 12:
        continue
    P = np.array([[p[1], p[0]] for p in b], float)   # (x, y)
    (a, bb, c), lerr = fit_line(P)
    (cx, cy, r), cerr = fit_circle(P)
    L = float(np.hypot(P[-1, 0] - P[0, 0], P[-1, 1] - P[0, 1]))
    kind = "LINE" if lerr < cerr else "CIRCLE"
    out.append(dict(i=i, n=len(b), kind=kind, lerr=lerr, cerr=cerr,
                    line=(a, bb, c), circle=(cx, cy, r),
                    p0=(P[0, 0], P[0, 1]), p1=(P[-1, 0], P[-1, 1]), length=L))
    if kind == "LINE":
        print("branch %2d n=%3d LINE  slope=%7.3f  x=%3d..%3d y=%3d..%3d  err=%.2f  len=%.0f"
              % (i, len(b), a, P[0, 0], P[-1, 0], P[0, 1], P[-1, 1], lerr, L))
    else:
        print("branch %2d n=%3d CIRCLE c=(%7.2f,%7.2f) r=%7.2f err=%.2f  ends (%d,%d)->(%d,%d) len=%.0f"
              % (i, len(b), cx, cy, r, cerr, P[0, 0], P[0, 1], P[-1, 0], P[-1, 1], L))
