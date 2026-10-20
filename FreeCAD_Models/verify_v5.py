# -*- coding: utf-8 -*-
"""verify_v5.py — check the built model: measure the features and render a
top view for comparison with the photo."""
import math
import os
import numpy as np
import FreeCAD as App
import Part
from PIL import Image, ImageDraw

OUT = "/workspace/FreeCAD_Models/out/"
doc = App.openDocument("/workspace/FreeCAD_Models/GearPart_v5.FCStd")
obj = doc.getObject("GearPart")
sh = obj.Shape
print("solids %d  valid %s  volume %.1f cm3  faces %d"
      % (len(sh.Solids), sh.isValid(), sh.Volume / 1000.0, len(sh.Faces)))
bb = sh.BoundBox
print("bbox  X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f"
      % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))

# ---- measurements on a section at mid thickness ----------------------------
sec = sh.slice(App.Vector(0, 0, 1), 10.0)
print("section wires: %d" % len(sec))
edges = []
for w in sec:
    for e in w.Edges:
        n = max(8, int(e.Length / 0.4))
        try:
            pts = e.discretize(Number=n)
        except Exception:
            pts = [e.Vertexes[0].Point, e.Vertexes[-1].Point]
        edges.append([(p.x, p.y) for p in pts])

# polar analysis of the section
allpts = np.array([p for e in edges for p in e])
r = np.hypot(allpts[:, 0], allpts[:, 1])
print("outer radius  max %.3f mm   (target %.3f)" % (r.max(), 3.69 * 25.4 * math.cos(math.radians(30))))
# tooth count: count the angular peaks
ang = np.degrees(np.arctan2(allpts[:, 1], allpts[:, 0])) % 360
tip = allpts[r > r.max() - 0.6]
ta = np.degrees(np.arctan2(tip[:, 1], tip[:, 0])) % 360
ta = np.sort(ta)
groups = 1
for i in range(1, len(ta)):
    if ta[i] - ta[i - 1] > 1.0:
        groups += 1
print("tooth tips counted: %d" % groups)

# window geometry: the material radius along the window axis and the spoke
def radial_runs(angle_deg):
    a = math.radians(angle_deg)
    d = np.array([math.cos(a), math.sin(a)])
    ts = np.array([p[0] * d[0] + p[1] * d[1] for p in allpts])
    return ts

for a, what in ((90.0, "window at 90 deg"), (0.0, "spoke at 0 deg")):
    ts = radial_runs(a)
    ts = np.sort(ts)
    runs = []
    if len(ts):
        s = p = ts[0]
        for v in ts[1:]:
            if v > p + 0.8:
                runs.append((s, p))
                s = v
            p = v
        runs.append((s, p))
    print("%-22s radial crossings: %s" % (what, " ".join("%.1f-%.1f" % t for t in runs[:8])))

# ---- render a top view ----------------------------------------------------
S = 4.0
size = int(2 * 85 * S)
img = Image.new("RGB", (size, size), (255, 255, 255))
dr = ImageDraw.Draw(img)
c = size / 2.0
for e in edges:
    xy = [(c + p[0] * S, c - p[1] * S) for p in e]
    if len(xy) > 1:
        dr.line(xy, fill=(0, 0, 0), width=2)
img.save(OUT + "model_topview.png")
print("saved", OUT + "model_topview.png")

# ---- side by side with the photo ------------------------------------------
ph = Image.open("/workspace/src/drawings/Screenshot (3).png").convert("RGB")
ph = ph.resize((size, int(ph.height * size / ph.width)), Image.LANCZOS)
comb = Image.new("RGB", (size * 2 + 20, max(size, ph.height)), (240, 240, 240))
comb.paste(img, (0, 0))
comb.paste(ph, (size + 20, 0))
comb.save(OUT + "compare_photo_model.png")
print("saved", OUT + "compare_photo_model.png")
