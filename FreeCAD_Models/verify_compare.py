# -*- coding: utf-8 -*-
"""verify_compare.py -- compare the built model with the photo in polar
coordinates (the same measurement on both) and write an overlay image."""
import math
import os
import numpy as np
import FreeCAD as App
import Part
from PIL import Image, ImageDraw

OUT = "/workspace/FreeCAD_Models/out/"
NA, NR = 1440, 700

# ---------------- the photo (already measured) -----------------------------
pw_photo = np.load(OUT + "polar_wood.npy")
rr = np.linspace(0, 360.0, NR)

# ---------------- the model -------------------------------------------------
doc = App.openDocument("/workspace/FreeCAD_Models/GearPart_v5.FCStd")
sh = doc.getObject("GearPart").Shape
sec = sh.slice(App.Vector(0, 0, 1), 10.0)
edges = []
for w in sec:
    for e in w.Edges:
        n = max(6, int(e.Length / 0.3))
        try:
            pts = e.discretize(Number=n)
        except Exception:
            pts = [e.Vertexes[0].Point, e.Vertexes[-1].Point]
        edges.append([(p.x, p.y) for p in pts])
allp = np.array([p for e in edges for p in e])

# build the model's polar material map
pw_model = np.zeros((NA, NR), bool)
for i in range(NA):
    a = 2 * math.pi * i / NA
    d = np.array([math.cos(a), math.sin(a)])
    perp = np.abs(allp[:, 0] * d[1] - allp[:, 1] * d[0])   # distance to the ray
    t = allp @ d                                            # along the ray
    on = (perp < 0.45) & (t > 0)
    if on.any():
        pw_model[i] = np.isin(np.round(rr, 1),
                              np.round(t[on], 1))


def prof(pw):
    out = np.zeros(NA)
    for i in range(NA):
        idx = np.nonzero(pw[i])[0]
        out[i] = rr[idx[-1]] if len(idx) else 0.0
    return out


def gaps(pw, ang):
    i = int((ang % 360) / 360 * NA)
    col = pw[i]
    idx = np.nonzero(col)[0]
    segs = []
    s = None
    for j, v in enumerate(col):
        if v and s is None:
            s = j
        elif not v and s is not None:
            segs.append((rr[s], rr[j - 1]))
            s = None
    if s is not None:
        segs.append((rr[s], rr[-1]))
    return segs


pm, pp = prof(pw_model), prof(pw_photo)
K = 81.16 / 347.1          # photo pixels -> model mm
print("                          MODEL      PHOTO (scaled)")
print("tip radius             %7.2f    %7.2f" % (pm.max(), pp.max() * K))
print("root radius (2%% low)   %7.2f    %7.2f" % (np.percentile(pm, 2),
                                                  np.percentile(pp, 2) * K))
for a in (30, 90, 150, 210, 270, 330):
    gm = gaps(pw_model, a)
    gp = [(s * K, e * K) for s, e in gaps(pw_photo, a)]
    print("axis %3d deg  model: %-28s photo: %s" %
          (a, " ".join("%.0f-%.0f" % t for t in gm),
           " ".join("%.0f-%.0f" % t for t in gp)))

# -------- overlay: photo in grey, model in red -----------------------------
S = 3.2
size = int(2 * 88 * S)
img = Image.new("RGB", (size, size), (255, 255, 255))
dr = ImageDraw.Draw(img)
c = size / 2.0
# photo outline (from the polar map: the outer profile and the window edges)
for i in range(NA):
    a = 2 * math.pi * i / NA
    for pw, col, sc in ((pw_photo, (185, 185, 185), K), (pw_model, (220, 0, 0), 1.0)):
        idx = np.nonzero(pw[i])[0]
        if not len(idx):
            continue
        r = rr[idx[-1]] * sc
        dr.line([(c + r * math.cos(a) * S, c - r * math.sin(a) * S),
                 (c + r * math.cos(a + 2 * math.pi / NA) * S,
                  c - r * math.sin(a + 2 * math.pi / NA) * S)], fill=col)
img.save(OUT + "overlay_photo_model.png")
print("saved", OUT + "overlay_photo_model.png")
