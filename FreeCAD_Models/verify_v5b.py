# -*- coding: utf-8 -*-
"""verify_v5b.py -- geometric verification of the finished model."""
import math
import numpy as np
import FreeCAD as App

doc = App.openDocument("/workspace/FreeCAD_Models/GearPart_v5.FCStd")
sh = doc.getObject("GearPart").Shape
sec = sh.slice(App.Vector(0, 0, 1), 10.0)
print("solids %d  valid %s  volume %.1f cm3" %
      (len(sh.Solids), sh.isValid(), sh.Volume / 1000.0))
print("section wires: %d" % len(sec))
for i, w in enumerate(sec):
    pts = np.array([[p.x, p.y] for e in w.Edges
                    for p in e.discretize(Number=60)])
    r = np.hypot(pts[:, 0], pts[:, 1])
    print("  wire %d: edges %3d  r %.2f .. %.2f mm" %
          (i, len(w.Edges), r.min(), r.max()))

# ---- outer profile: tip / root radius and the tooth count -----------------
outer = max(sec, key=lambda w: w.BoundBox.XLength)
pts = np.array([[p.x, p.y] for e in outer.Edges
                for p in e.discretize(Number=20)])
r = np.hypot(pts[:, 0], pts[:, 1])
ang = np.degrees(np.arctan2(pts[:, 1], pts[:, 0])) % 360
tip = pts[r > r.max() - 0.8]
ta = np.sort(np.degrees(np.arctan2(tip[:, 1], tip[:, 0])) % 360)
cnt = 1
for i in range(1, len(ta)):
    if ta[i] - ta[i - 1] > 1.0:
        cnt += 1
print("\nTOOTH  tip R = %.2f mm (D = %.2f mm = %.3f in)" %
      (r.max(), 2 * r.max(), 2 * r.max() / 25.4))
print("       root R = %.2f mm   (%.3f x tip)" %
      (np.percentile(r, 1), np.percentile(r, 1) / r.max()))
print("       teeth  = %d" % cnt)

# ---- windows --------------------------------------------------------------
wins = [w for w in sec if w is not outer and len(w.Edges) > 1]
print("\nWINDOWS: %d" % len(wins))
for w in wins:
    p = np.array([[q.x, q.y] for e in w.Edges for q in e.discretize(Number=60)])
    rr = np.hypot(p[:, 0], p[:, 1])
    a = np.degrees(np.arctan2(p[:, 1], p[:, 0])) % 360
    print("   outer R = %.2f mm   inner R(min) = %.2f mm   axis = %.1f deg" %
          (rr.max(), rr.min(), a.mean()))

# ---- spoke width on the rim circle ----------------------------------------
R_RIM = 65.5
best = None
for w in wins:
    p = np.array([[q.x, q.y] for e in w.Edges for q in e.discretize(Number=80)])
    # points close to the rim circle
    m = np.abs(np.hypot(p[:, 0], p[:, 1]) - R_RIM) < 0.4
    if m.sum() < 5:
        continue
    pts2 = p[m]
    a = np.degrees(np.arctan2(pts2[:, 1], pts2[:, 0])) % 360
    c = np.arccos(np.clip(pts2 @ np.array([np.cos(np.radians(a[0])),
                                           np.sin(np.radians(a[0]))]), -1, 1))
    print("   window arc on the rim circle: %.1f deg (chord %.1f mm = %.2f in)" %
          (a.max() - a.min(), 2 * R_RIM * math.sin(math.radians((a.max() - a.min()) / 2)),
           2 * R_RIM * math.sin(math.radians((a.max() - a.min()) / 2)) / 25.4))

# ---- bore and thickness ---------------------------------------------------
for w in sec:
    if len(w.Edges) == 1 and w.BoundBox.XLength < 40:
        print("\nBORE  D = %.2f mm" % w.BoundBox.XLength)
print("THICKNESS = %.1f mm" % sh.BoundBox.ZLength)
