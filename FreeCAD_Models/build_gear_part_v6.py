# -*- coding: utf-8 -*-
"""
build_gear_part_v6.py -- parametric, self-contained rebuild of the 3-spoke gear
                          (51 rounded saw teeth, 3 windows, hub, 10 mm bore).

--------------------------------------------------------------------------
RUN IT ON THE HOST, WHERE FreeCAD IS INSTALLED
--------------------------------------------------------------------------
    freecadcmd /workspace/FreeCAD_Models/build_gear_part_v6.py
    # GUI alternative:
    freecad     /workspace/FreeCAD_Models/build_gear_part_v6.py

FreeCAD is intentionally NOT installed inside the dev container, so this file
is only syntax-checked there; the geometry kernel runs on the host.

--------------------------------------------------------------------------
OUTPUT  (see .roo/rules/freecad-save-path.md)
--------------------------------------------------------------------------
    /workspace/FreeCAD_Models/GearPart_v6.FCStd     <- FreeCAD document
    /workspace/FreeCAD_Models/GearPart_v6.step      <- STEP AP214
    /workspace/FreeCAD_Models/GearPart_v6.stl       <- mesh preview (best effort)

The output folder can be overridden with the FC_OUT_DIR environment variable,
and the file name with FC_DOC_NAME, but the default is the project folder.

--------------------------------------------------------------------------
WHAT IS NEW COMPARED TO v5
--------------------------------------------------------------------------
v5 needed numpy and the photo-derived array
`FreeCAD_Models/out/tooth_template.npy`.
v6 drops both dependencies:
  * the tooth is an ANALYTIC rounded saw profile  r(v) = R_root +
    (R_tip - R_root) * (1 - |v|^TOOTH_FLANK),  v in [-1, 1] over one pitch;
  * everything is plain Python + FreeCAD's own Part module.
So the script runs on any clean FreeCAD installation, from a single file.

--------------------------------------------------------------------------
DIMENSIONS  (same source data as v5 -- see MODEL_REPORT.md)
--------------------------------------------------------------------------
SKETCH (src/drawings/Screenshot (2).png), scale 107.2 px/in:
    3.69 in  side of the construction hexagon -> tip circle
             R_tip = 3.69 * cos(30 deg) in = 81.16 mm
    1.94 in  radius of construction circle C1  = 49.28 mm (kept as reference)
    2.24 in  side of the hexagon about C1      = 56.90 mm (kept as reference)
    1.25 in  spoke width on the rim circle     = 31.75 mm
PHOTO (src/drawings/Screenshot (3).png):
    51 teeth, tooth root / tip = 0.9442
    rim (window outer circle) / tip = 0.807  ->  R_rim = 65.50 mm
    hub radius / tip = 0.233                 ->  R_hub = 18.91 mm
    central bore 10 mm, corner radius 8 mm, thickness 20 mm (user)
"""

import math
import os
import sys
import traceback

import FreeCAD as App
import Part

# ============================================================== parameters ==
IN = 25.4                       # mm per inch

# --- from the dimensioned sketch -------------------------------------------
R_TIP = 3.69 * IN * math.cos(math.radians(30.0))    # 81.16 mm
SPOKE_W = 1.25 * IN                                 # 31.75 mm
R_C1 = 1.94 * IN                                    # 49.28 mm  (reference)
HEX_SIDE = 2.24 * IN                                # 56.90 mm  (reference)

# --- from the photo --------------------------------------------------------
N_TEETH = 51
RATIO_ROOT = 0.9442
RATIO_RIM = 0.8070
RATIO_HUB = 0.2330

R_ROOT = RATIO_ROOT * R_TIP                         # 76.63 mm
R_RIM = RATIO_RIM * R_TIP                           # 65.50 mm
R_HUB = RATIO_HUB * R_TIP                           # 18.91 mm

# --- user / manufacturing --------------------------------------------------
BORE_D = 10.0
THICK = 20.0
R_CORNER = 8.0

# --- discretisation of the analytic tooth ----------------------------------
TOOTH_SAMPLES = 24              # points per tooth (root included)
TOOTH_FLANK = 2.6               # >1 : flat-ish tip, narrow root

WIN_AXES = (90.0, 210.0, 330.0)

# --- output location (project rule) ----------------------------------------
OUT_DIR = os.environ.get("FC_OUT_DIR", "/workspace/FreeCAD_Models")
DOC_NAME = os.environ.get("FC_DOC_NAME", "GearPart_v6")

Z = App.Vector(0.0, 0.0, 1.0)
ORIGIN = App.Vector(0.0, 0.0, 0.0)


# ================================================================= helpers ==
def v(r, a_deg):
    """Polar -> Cartesian in the XY plane."""
    a = math.radians(a_deg)
    return App.Vector(r * math.cos(a), r * math.sin(a), 0.0)


def arc_points(center, radius, a_start, a_end, n=None, ccw=True):
    """Polyline approximation of a circular arc, angles in degrees."""
    sweep = (a_end - a_start) % 360.0
    if sweep == 0.0:
        sweep = 360.0
    if not ccw:
        sweep -= 360.0
    if n is None:
        n = max(3, int(math.ceil(abs(sweep) / 1.0)))
    pts = []
    for k in range(n + 1):
        a = math.radians(a_start + sweep * k / float(n))
        pts.append(App.Vector(center.x + radius * math.cos(a),
                              center.y + radius * math.sin(a), 0.0))
    return pts


def circle_intersect(c1, r1, c2, r2):
    """Both intersection points of two circles in the XY plane."""
    d = (c2 - c1).Length
    if d < 1e-12:
        raise ValueError("concentric circles cannot be intersected")
    a = (r1 * r1 - r2 * r2 + d * d) / (2.0 * d)
    h2 = r1 * r1 - a * a
    h = math.sqrt(h2) if h2 > 0.0 else 0.0
    ex = App.Vector((c2.x - c1.x) / d, (c2.y - c1.y) / d, 0.0)
    base = App.Vector(c1.x + ex.x * a, c1.y + ex.y * a, 0.0)
    perp = App.Vector(-ex.y, ex.x, 0.0)
    return (App.Vector(base.x + perp.x * h, base.y + perp.y * h, 0.0),
            App.Vector(base.x - perp.x * h, base.y - perp.y * h, 0.0))


def poly_face(points):
    """Planar face from a closed polygon given as a point list."""
    return Part.Face(Part.makePolygon(points + [points[0]]))


def tooth_ratio(v_norm):
    """Normalised radius of the analytic tooth, v_norm in [-1, 1]."""
    a = abs(v_norm)
    if a >= 1.0:
        return 0.0
    return 1.0 - a ** TOOTH_FLANK


def tooth_ring_points():
    """Closed polyline of the whole toothed rim."""
    pitch = 360.0 / N_TEETH
    half = pitch / 2.0
    pts = []
    for k in range(N_TEETH):
        a0 = k * pitch
        for j in range(TOOTH_SAMPLES):
            u = -1.0 + 2.0 * j / float(TOOTH_SAMPLES)
            r = R_ROOT + (R_TIP - R_ROOT) * tooth_ratio(u)
            pts.append(v(r, a0 + u * half))
    return pts


def window_outline(r_rim, half_ang, r_hub, r_fillet):
    """Outline of one window in its local frame (window axis = +Y).

    * outer boundary: arc on the rim circle r_rim
    * rounded corners of radius r_fillet
    * concave inner arc through the two corners, tangent to the hub circle
    """
    # outer corner points, before filleting
    px = r_rim * math.sin(half_ang)
    py = r_rim * math.cos(half_ang)

    # centre/radius of the inner arc: through (+-px, py), tangent to hub
    yc = (r_rim ** 2 - r_hub ** 2) / (2.0 * (py - r_hub))
    inner_c = App.Vector(0.0, yc, 0.0)
    r_in = abs(yc - r_hub)

    # fillet centres: tangent to the outer circle (inside) and inner arc
    f1, f2 = circle_intersect(ORIGIN, r_rim - r_fillet,
                              inner_c, r_in + r_fillet)
    if f1.x > f2.x:
        f1, f2 = f2, f1

    def tangents(fc):
        u = App.Vector(fc.x, fc.y, 0.0)
        u.normalize()
        outer_t = App.Vector(u.x * r_rim, u.y * r_rim, 0.0)
        d = App.Vector(fc.x - inner_c.x, fc.y - inner_c.y, 0.0)
        d.normalize()
        inner_t = App.Vector(inner_c.x + d.x * r_in,
                             inner_c.y + d.y * r_in, 0.0)
        return outer_t, inner_t

    def ang(center, p):
        return math.degrees(math.atan2(p.y - center.y, p.x - center.x))

    to_a, ti_a = tangents(f1)          # left fillet
    to_b, ti_b = tangents(f2)          # right fillet

    pts = []
    pts += arc_points(ORIGIN, r_rim, ang(ORIGIN, to_b), ang(ORIGIN, to_a))
    pts += arc_points(f1, r_fillet, ang(f1, to_a), ang(f1, ti_a),
                      n=18, ccw=False)
    pts += arc_points(inner_c, r_in, ang(inner_c, ti_a), ang(inner_c, ti_b))
    pts += arc_points(f2, r_fillet, ang(f2, ti_b), ang(f2, to_b),
                      n=18, ccw=False)

    clean = [pts[0]]
    for p in pts[1:]:
        if (p - clean[-1]).Length > 1e-7:
            clean.append(p)
    return clean


def rotate(pts, axis_deg):
    """Rotate a local-frame outline so that its +Y axis points at axis_deg."""
    a = math.radians(axis_deg - 90.0)
    ca, sa = math.cos(a), math.sin(a)
    return [App.Vector(p.x * ca - p.y * sa, p.x * sa + p.y * ca, 0.0)
            for p in pts]


# ==================================================================== main ==
def build():
    # window geometry: spoke width is fixed, the window fills the rest of the
    # 120 deg sector, so the dimensional chain comes straight from 1.25 in.
    spoke_ang = 2.0 * math.asin((SPOKE_W / 2.0) / R_RIM)
    win_ang = math.radians(120.0) - spoke_ang
    half_win = win_ang / 2.0
    window_chord = 2.0 * R_RIM * math.sin(half_win)

    print("=" * 68)
    print("build_gear_part_v6  ->  %s" % os.path.join(OUT_DIR, DOC_NAME))
    print("=" * 68)
    print("R_tip      %8.2f mm   (= %.3f in)" % (R_TIP, R_TIP / IN))
    print("R_root     %8.2f mm   (ratio %.4f)" % (R_ROOT, RATIO_ROOT))
    print("R_rim      %8.2f mm   (ratio %.4f)" % (R_RIM, RATIO_RIM))
    print("R_hub      %8.2f mm   (ratio %.4f)" % (R_HUB, RATIO_HUB))
    print("spoke      %8.2f mm   (= %.3f in, from the sketch)"
          % (SPOKE_W, SPOKE_W / IN))
    print("window     %8.2f mm chord, %.2f deg"
          % (window_chord, math.degrees(win_ang)))
    print("teeth      %8d       thickness %.1f mm, bore %.1f mm"
          % (N_TEETH, THICK, BORE_D))

    doc = App.newDocument(DOC_NAME)

    # 1. toothed rim ---------------------------------------------------------
    solid = poly_face(tooth_ring_points()).extrude(App.Vector(0.0, 0.0, THICK))

    # 2. three windows -------------------------------------------------------
    outline = window_outline(R_RIM, half_win, R_HUB, R_CORNER)
    for axis in WIN_AXES:
        cutter = poly_face(rotate(outline, axis)).extrude(
            App.Vector(0.0, 0.0, THICK + 2.0))
        cutter.translate(App.Vector(0.0, 0.0, -1.0))
        solid = solid.cut(cutter)

    # 3. central bore --------------------------------------------------------
    solid = solid.cut(Part.makeCylinder(BORE_D / 2.0, THICK + 4.0,
                                        App.Vector(0.0, 0.0, -2.0), Z))

    solid = solid.removeSplitter()
    if not solid.isValid():
        solid.fix(1e-7, 1e-7, 1e-7)

    part = doc.addObject("Part::Feature", "GearPart")
    part.Shape = solid
    part.Label = DOC_NAME

    # 4. construction geometry of the drawing, kept for traceability ---------
    hex_r = R_C1 / math.cos(math.radians(30.0))
    hex_pts = [v(hex_r, 30.0 + 60.0 * k) for k in range(6)]

    refs = (
        ("ConstructionCircle_C1", "C1 construction circle (1.94 in)",
         Part.Wire([Part.Circle(ORIGIN, Z, R_C1).toShape()])),
        ("ConstructionHexagon", "construction hexagon (2.24 in / 3.69 in)",
         Part.makePolygon(hex_pts + [hex_pts[0]])),
        ("TipCircle", "tooth tip circle (R 3.195 in)",
         Part.Wire([Part.Circle(ORIGIN, Z, R_TIP).toShape()])),
    )
    for name, label, shape in refs:
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        obj.Label = label

    doc.recompute()

    # 5. save (project rule: /workspace/FreeCAD_Models by default) -----------
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    fcstd = os.path.join(OUT_DIR, DOC_NAME + ".FCStd")
    doc.saveAs(fcstd)
    print("saved      %s" % fcstd)

    step = os.path.join(OUT_DIR, DOC_NAME + ".step")
    try:
        Part.export([part], step)
        print("saved      %s" % step)
    except Exception as exc:                                   # noqa: BLE001
        print("STEP export failed: %s" % exc)

    stl = os.path.join(OUT_DIR, DOC_NAME + ".stl")
    try:
        part.Shape.exportStl(stl)
        print("saved      %s" % stl)
    except Exception as exc:                                   # noqa: BLE001
        print("STL export failed: %s" % exc)

    # 6. report --------------------------------------------------------------
    sh = part.Shape
    bb = sh.BoundBox
    print("-" * 68)
    print("solids %d   valid %s   faces %d"
          % (len(sh.Solids), sh.isValid(), len(sh.Faces)))
    print("volume %.1f cm3" % (sh.Volume / 1000.0))
    print("bbox   X %.2f..%.2f   Y %.2f..%.2f   Z %.2f..%.2f"
          % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    print("diameter %.2f mm   thickness %.2f mm"
          % (max(bb.XLength, bb.YLength), bb.ZLength))
    return doc, part


def main():
    try:
        build()
    except Exception:                                          # noqa: BLE001
        traceback.print_exc()
        sys.stdout.flush()
        # non-zero exit status so that a headless run is reported as failed
        raise SystemExit(1)


main()
