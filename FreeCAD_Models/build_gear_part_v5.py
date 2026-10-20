# -*- coding: utf-8 -*-
"""
build_gear_part_v5.py  --  3-spoke wooden gear, rebuilt from
    src/drawings/Screenshot (2).png   (dimensioned CAD sketch)
    src/drawings/Screenshot (3).png   (photo of the real part)

Run:  freecadcmd /workspace/FreeCAD_Models/build_gear_part_v5.py
Out:  /workspace/FreeCAD_Models/GearPart_v5.FCStd  +  GearPart_v5.step

------------------------------------------------------------------
HOW EVERY DIMENSION WAS RESOLVED  (all measured on the images)
------------------------------------------------------------------
SKETCH   the drawing scale is 107.2 px/in (3.69 in = 396 px, 1.94 in = 208 px
         from the centre, 1.25 in = 134 px)   ->  1 in = 25.4 mm
  * 3.69 in  = side of the CONSTRUCTION hexagon drawn around the gear.
               Its inradius is 3.69*cos30 = 3.195 in -> that circle is the
               tooth-tip circle  =>  R_TIP = 3.195 in = 81.16 mm
  * 1.94 in  = radius of the CONSTRUCTION circle C1 (the six axis tangents
               are drawn on it and the 1.94 in dimension points at its
               tangent line)
  * 1.25 in (radial, upper right) = distance C1 -> tooth-tip circle.
               1.94 + 1.25 = 3.19 in == 3.69*cos30, so the three values of
               the drawing are mutually consistent
  * 2.24 in  = side of the hexagon circumscribed about C1:
               2 * 1.94 * tan30 = 2.24 in  (exact)
  * 1.25 in (lower left) = the width of a spoke, measured between the two
               parallel flank lines of the drawing

PHOTO  (the real part - everything that the drawing does not dimension)
  * 51 teeth, rounded saw-like profile            (measured)
  * tooth depth / tip radius = 0.944              (measured)
  * rim (window outer circle) / tip radius = 0.807 (measured)
  * hub radius = 0.233 * R_tip = 18.9 mm          (measured)
  * central bore 10 mm                            (measured)
  * plate thickness 20 mm                         (given by the user)

------------------------------------------------------------------
THE MODEL
------------------------------------------------------------------
  toothed rim (51 teeth, profile of the real part)
  + 3 crescent shaped windows:  outer arc on the rim circle, rounded
    corners, concave inner arc that runs tangentially into the hub
  + hub + central bore, 20 mm thick.
  The window's outer arc is sized so that the spoke between two windows is
  1.25 in (31.75 mm) wide on the rim circle - the dimension of the drawing.
"""
import math
import os
import sys
import numpy as np
import FreeCAD as App
import Part

IN = 25.4
OUT_DIR = "/workspace/FreeCAD_Models"
Z = App.Vector(0, 0, 1)

# "sketch" -> variant that uses the 1.94 in construction circle of the drawing
# as the rim (window outer) circle, i.e. the drawing's deeper rim
VARIANT = "sketch" if "sketch" in sys.argv[1:] else "photo"
DOC_NAME = "GearPart_v5" if VARIANT == "photo" else "GearPart_v5_sketchrim"

# ----------------------------------------------------------------- INPUTS ---
# ---- the SKETCH gives the main dimensions ----------------------------------
R_TIP = 3.69 * IN * math.cos(math.radians(30.0))   # 81.16 mm  (3.69 in)
SPOKE_W = 1.25 * IN                                # 31.75 mm  (1.25 in)
R_C1 = 1.94 * IN                                   # 49.28 mm  (construction)
HEX_SIDE = 2.24 * IN                               # 56.90 mm  (construction)
# ---- the PHOTO gives the remaining dimensions ------------------------------
N_TEETH = 51
RATIO_RIM = 0.807          # rim (window outer circle) / tip radius
RATIO_ROOT = 0.9442        # tooth root / tip radius
R_HUB = 0.2330 * R_TIP     # 18.91 mm
BORE_D = 10.0
THICK = 20.0
R_CORNER = 8.0             # rounded window corners

TOOTH_TEMPLATE = np.load(os.path.join(OUT_DIR, "out", "tooth_template.npy"))
TOOTH_SAMPLES = 64

R_RIM = RATIO_RIM * R_TIP if VARIANT == "photo" else R_C1   # 65.50 / 49.28 mm
# window outer arc: the spoke (SPOKE_W) and the window fill the 120 deg sector
SPOKE_ANG = 2 * math.asin((SPOKE_W / 2.0) / R_RIM)
WIN_ANG = math.radians(120.0) - SPOKE_ANG
HALF_WIN = WIN_ANG / 2.0
W_WIN = 2 * R_RIM * math.sin(HALF_WIN)    # window chord on the rim circle


# ------------------------------------------------------------- helpers ------
def v(r, a_deg):
    a = math.radians(a_deg)
    return App.Vector(r * math.cos(a), r * math.sin(a), 0.0)


def arc_points(center, radius, a_start, a_end, n=None, ccw=True):
    sweep = (a_end - a_start) % 360.0
    if sweep == 0:
        sweep = 360.0
    if not ccw:
        sweep -= 360.0
    if n is None:
        n = max(3, int(math.ceil(abs(sweep) / 1.0)))
    out = []
    for k in range(n + 1):
        a = math.radians(a_start + sweep * k / float(n))
        out.append(App.Vector(center.x + radius * math.cos(a),
                              center.y + radius * math.sin(a), 0))
    return out


def circle_intersect(c1, r1, c2, r2):
    d = (c2 - c1).Length
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(r1 * r1 - a * a, 0.0))
    ex = App.Vector((c2.x - c1.x) / d, (c2.y - c1.y) / d, 0)
    base = App.Vector(c1.x + ex.x * a, c1.y + ex.y * a, 0)
    perp = App.Vector(-ex.y, ex.x, 0)
    return (App.Vector(base.x + perp.x * h, base.y + perp.y * h, 0),
            App.Vector(base.x - perp.x * h, base.y - perp.y * h, 0))


def window_points(R_rim, half_ang, R_hub, r_corner):
    """outline of one window, local frame: window axis = +Y.
       outer arc on R_rim, rounded corners, concave inner arc that is
       tangent to the hub circle."""
    p1 = App.Vector(-R_rim * math.sin(half_ang), R_rim * math.cos(half_ang), 0)
    p2 = App.Vector(+R_rim * math.sin(half_ang), R_rim * math.cos(half_ang), 0)
    yc = (R_rim ** 2 - R_hub ** 2) / (2.0 * (p1.y - R_hub))
    ci = App.Vector(0, yc, 0)
    r_in = abs(R_hub - yc)
    f1, f2 = circle_intersect(App.Vector(0, 0, 0), R_rim - r_corner,
                               ci, r_in + r_corner)
    if f1.x > f2.x:
        f1, f2 = f2, f1
    res = []
    for fc in (f1, f2):
        u = App.Vector(fc.x, fc.y, 0)
        u.normalize()
        to = App.Vector(u.x * R_rim, u.y * R_rim, 0)
        z = App.Vector(fc.x - ci.x, fc.y - ci.y, 0)
        z.normalize()
        ti = App.Vector(ci.x + z.x * r_in, ci.y + z.y * r_in, 0)
        res.append((fc, to, ti))
    (fcA, toA, tiA), (fcB, toB, tiB) = res
    O = App.Vector(0, 0, 0)

    def ang(c, p):
        return math.degrees(math.atan2(p.y - c.y, p.x - c.x))

    pts = []
    pts += arc_points(O, R_rim, ang(O, toB), ang(O, toA))
    pts += arc_points(fcA, r_corner, ang(fcA, toA), ang(fcA, tiA), n=18, ccw=False)
    pts += arc_points(ci, r_in, ang(ci, tiA), ang(ci, tiB))
    pts += arc_points(fcB, r_corner, ang(fcB, tiB), ang(fcB, toB), n=18, ccw=False)
    clean = [pts[0]]
    for p in pts[1:]:
        if (p - clean[-1]).Length > 1e-7:
            clean.append(p)
    return clean


def gear_points():
    t = TOOTH_TEMPLATE
    M = len(t)
    idx = np.linspace(0, M - 1, TOOTH_SAMPLES)
    prof = np.interp(idx, np.arange(M), t)
    scale = R_TIP / prof.max()
    pts = []
    for k in range(N_TEETH):
        a0 = k * 360.0 / N_TEETH
        for j in range(TOOTH_SAMPLES):
            frac = j / float(TOOTH_SAMPLES) - 0.5
            pts.append(v(prof[j] * scale, a0 + frac * 360.0 / N_TEETH))
    return pts


def poly_face(points):
    return Part.Face(Part.makePolygon(points + [points[0]]))


def main():
    print("variant   : %s" % VARIANT)
    print("R_tip %.2f  R_rim %.2f  window chord %.2f  spoke %.2f  hub %.2f"
          % (R_TIP, R_RIM, W_WIN, SPOKE_W, R_HUB))
    doc = App.newDocument(DOC_NAME)

    solid = poly_face(gear_points()).extrude(App.Vector(0, 0, THICK))

    wp = window_points(R_RIM, HALF_WIN, R_HUB, R_CORNER)
    for axis in (90.0, 210.0, 330.0):
        a = math.radians(axis - 90.0)
        rot = [App.Vector(p.x * math.cos(a) - p.y * math.sin(a),
                          p.x * math.sin(a) + p.y * math.cos(a), 0) for p in wp]
        solid = solid.cut(poly_face(rot).extrude(App.Vector(0, 0, THICK + 2)))

    solid = solid.cut(Part.makeCylinder(BORE_D / 2.0, THICK + 4,
                                        App.Vector(0, 0, -2), Z))
    solid = solid.removeSplitter()

    obj = doc.addObject("Part::Feature", "GearPart")
    obj.Shape = solid
    obj.Label = DOC_NAME

    # construction geometry of the drawing (kept in the document) ------------
    c1 = doc.addObject("Part::Feature", "ConstructionCircle_C1")
    c1.Shape = Part.Wire([Part.Circle(App.Vector(0, 0, 0), Z, R_C1).toShape()])
    c1.Label = "C1 construction circle (1.94 in)"
    hp = [v(R_C1 / math.cos(math.radians(30)), 30 + 60 * k) for k in range(6)]
    hx = doc.addObject("Part::Feature", "ConstructionHexagon")
    hx.Shape = Part.makePolygon(hp + [hp[0]])
    hx.Label = "construction hexagon (side 2.24 in / 3.69 in)"
    tc = doc.addObject("Part::Feature", "TipCircle")
    tc.Shape = Part.Wire([Part.Circle(App.Vector(0, 0, 0), Z, R_TIP).toShape()])
    tc.Label = "tooth tip circle (R 3.195 in)"

    doc.recompute()
    path = os.path.join(OUT_DIR, DOC_NAME + ".FCStd")
    doc.saveAs(path)
    Part.export([obj], os.path.join(OUT_DIR, DOC_NAME + ".step"))

    sh = obj.Shape
    print("solids : %d   valid: %s" % (len(sh.Solids), sh.isValid()))
    print("volume : %.1f cm3" % (sh.Volume / 1000.0))
    print("bbox   : %s" % sh.BoundBox)
    print("faces  : %d" % len(sh.Faces))
    print("saved  : %s" % path)


main()
