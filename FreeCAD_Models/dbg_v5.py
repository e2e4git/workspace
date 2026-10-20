# -*- coding: utf-8 -*-
"""dbg_v5.py — step-by-step check of the v5 geometry."""
import math, os
import numpy as np
import FreeCAD as App
import Part
import sys
sys.path.insert(0, "/workspace/FreeCAD_Models")

IN = 25.4
R_TIP = 3.69 * IN * math.cos(math.radians(30.0))
R_RIM = 1.94 * IN
W_WIN = 2.24 * IN
R_HUB = 0.2330 * R_TIP
R_CORNER = 8.0
N_TEETH = 57
prof = np.load("/workspace/FreeCAD_Models/out/tooth_profile.npy")


def v(r, a_deg):
    a = math.radians(a_deg)
    return App.Vector(r * math.cos(a), r * math.sin(a), 0.0)


def ang(center, p):
    return math.atan2(p.y - center.y, p.x - center.x)


def arc(center, radius, a_start, a_end):
    while a_end <= a_start:
        a_end += 2 * math.pi
    circ = Part.Circle(App.Vector(center.x, center.y, 0), App.Vector(0, 0, 1), radius)
    return Part.ArcOfCircle(circ, a_start, a_end).toShape()


def circle_intersect(c1, r1, c2, r2):
    d = (c2 - c1).Length
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(r1 * r1 - a * a, 0.0))
    ex = App.Vector((c2.x - c1.x) / d, (c2.y - c1.y) / d, 0)
    base = App.Vector(c1.x + ex.x * a, c1.y + ex.y * a, 0)
    perp = App.Vector(-ex.y, ex.x, 0)
    return (App.Vector(base.x + perp.x * h, base.y + perp.y * h, 0),
            App.Vector(base.x - perp.x * h, base.y - perp.y * h, 0))


phi = math.asin((W_WIN / 2.0) / R_RIM)
p1 = App.Vector(-R_RIM * math.sin(phi), R_RIM * math.cos(phi), 0)
p2 = App.Vector(+R_RIM * math.sin(phi), R_RIM * math.cos(phi), 0)
yc = (R_RIM ** 2 - R_HUB ** 2) / (2.0 * (p1.y - R_HUB))
ci = App.Vector(0, yc, 0)
r_in = abs(R_HUB - yc)
print("phi=%.2f deg  yc=%.2f  r_in=%.2f  R_hub=%.2f" %
      (math.degrees(phi), yc, r_in, R_HUB))
f1, f2 = circle_intersect(App.Vector(0, 0, 0), R_RIM - R_CORNER, ci, r_in + R_CORNER)
print("fillet centres:", f1, f2)
if f1.x > f2.x:
    f1, f2 = f2, f1
for fc in (f1, f2):
    w0 = App.Vector(fc.x, fc.y, 0); w0.normalize()
    to = App.Vector(w0.x * R_RIM, w0.y * R_RIM, 0)
    z = App.Vector(fc.x - ci.x, fc.y - ci.y, 0); z.normalize()
    ti = App.Vector(ci.x + z.x * r_in, ci.y + z.y * r_in, 0)
    print("  fc=(%.2f,%.2f)  to=(%.2f,%.2f) |.|=%.2f  ti=(%.2f,%.2f) |.|=%.2f" %
          (fc.x, fc.y, to.x, to.y, to.Length, ti.x, ti.y, ti.Length))
    print("     angle to=%.1f deg  angle ti=%.1f deg" %
          (math.degrees(ang(fc, to)), math.degrees(ang(fc, ti))))

# gear wire
scale = R_TIP / prof.max()
pts = []
M = len(prof)
for k in range(N_TEETH):
    a0 = k * 360.0 / N_TEETH
    for j in range(M):
        frac = j / float(M) - 0.5
        pts.append(v(prof[j] * scale, a0 + frac * 360.0 / N_TEETH))
for NS in (60, 30, 20, 12):
    sel = [pts[int(round(i * len(pts) / float(NS * N_TEETH)))] for i in range(NS * N_TEETH)]
    try:
        edges = [Part.Line(sel[i], sel[(i + 1) % len(sel)]).toShape() for i in range(len(sel))]
        w = Part.Wire(edges)
        f = Part.Face(w)
        print("samples/tooth=%2d  edges=%4d  closed=%s valid=%s  face area=%.1f"
              % (NS, len(edges), w.isClosed(), w.isValid(), f.Area))
    except Exception as e:
        print("samples/tooth=%2d  FAILED: %s" % (NS, e))
print("circle area %.1f" % (math.pi * R_TIP ** 2))
