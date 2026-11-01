# -*- coding: utf-8 -*-
"""
build_part_v7.py -- hexagonal plate with a three-lobed (trefoil) pocket and a
                    central through bore.

Clean, self-contained rebuild of the part that used to be produced by
build_gear_part_v4.py (the v6 / render_preview files were lost in a git
rollback).  It uses only FreeCAD's own Part module -- no numpy, no Sketcher,
no external data files.

--------------------------------------------------------------------------
RUN IT ON THE HOST, WHERE FreeCAD IS INSTALLED
--------------------------------------------------------------------------
    freecadcmd /workspace/FreeCAD_Models/build_part_v7.py
    # GUI alternative:
    freecad     /workspace/FreeCAD_Models/build_part_v7.py

FreeCAD is intentionally NOT installed inside the dev container, so this file
is only written there; the geometry kernel runs on the host.

--------------------------------------------------------------------------
OUTPUT  (see .roo/rules/freecad-save-path.md)
--------------------------------------------------------------------------
    /workspace/FreeCAD_Models/GearPart_v7.FCStd   <- FreeCAD document
    /workspace/FreeCAD_Models/GearPart_v7.step    <- STEP AP214
    /workspace/FreeCAD_Models/GearPart_v7.stl     <- mesh preview (best effort)

The output folder can be overridden with FC_OUT_DIR and the document name
with FC_DOC_NAME; the defaults follow the project rule.

--------------------------------------------------------------------------
GEOMETRY  (1 in = 25.4 mm, from src/drawings/Screenshot (2).png)
--------------------------------------------------------------------------
  * Regular hexagon blank: the 3.69 in dimension is one SIDE of the hexagon.
    For a regular hexagon side == circumradius, so
        R_HEX = 3.69 in = 93.726 mm   (across flats 162.27 mm).
  * Trefoil pocket: three arcs of R = 1.25 in = 31.75 mm.  Their centres are
    offset d = 1.94 in - 1.25 in = 17.526 mm from the origin at 90/210/330 deg,
    so the lobe tips reach 1.94 in = 49.276 mm.  The arcs are joined by three
    straight notch faces, each at 2.24 in / sqrt(3) = 32.85 mm from the centre
    (the 2.24 in dimension is the side of the hexagon circumscribed about the
    1.94 in construction circle).
  * Pocket depth 10 mm, blind from the top face.  Set POCKET_THROUGH = True
    for a through cut.
  * Central bore Ø10 mm, through.
  * Plate thickness 20 mm.
"""

import math
import os
import sys
import traceback

import FreeCAD as App
import Part

# ============================================================== parameters ==
IN = 25.4

# --- hexagon blank ---------------------------------------------------------
R_HEX_CIRCUM = 3.69 * IN                       # 93.726 mm  circumradius (= side)
THICKNESS = 20.0                               # mm

# --- trefoil pocket --------------------------------------------------------
ARC_R = 1.25 * IN                              # 31.75 mm   lobe radius
TIP_DIST = 1.94 * IN                           # 49.276 mm  centre -> lobe tip
D_OFFSET = TIP_DIST - ARC_R                    # 17.526 mm  lobe-centre offset
NOTCH_FLAT_R = (2.24 * IN) / math.sqrt(3.0)    # 32.85 mm   origin -> notch face
LOBE_AXES_DEG = (90.0, 210.0, 330.0)

POCKET_DEPTH = 10.0                            # mm  blind pocket depth
POCKET_THROUGH = False                         # True -> through cut

# --- central bore ----------------------------------------------------------
BORE_D = 10.0                                  # mm

# --- output location (project rule) ----------------------------------------
OUT_DIR = os.environ.get("FC_OUT_DIR", "/workspace/FreeCAD_Models")
DOC_NAME = os.environ.get("FC_DOC_NAME", "GearPart_v7")

Z = App.Vector(0.0, 0.0, 1.0)
ORIGIN = App.Vector(0.0, 0.0, 0.0)


# ================================================================= helpers ==
def polar(r, a_deg):
    """Polar -> Cartesian in the XY plane."""
    a = math.radians(a_deg)
    return App.Vector(r * math.cos(a), r * math.sin(a), 0.0)


def ang_diff(a, b):
    """Signed smallest difference a - b, in (-pi, pi]."""
    d = a - b
    while d > math.pi:
        d -= 2.0 * math.pi
    while d < -math.pi:
        d += 2.0 * math.pi
    return d


def line_circle_pts(m, c, center, radius):
    """Intersection points of the line {p . m = c} with a circle.

    m is a unit vector in the XY plane, c the signed offset of the line,
    center/radius describe the circle.  Returns 0, 1 or 2 points.
    """
    proj = m.x * center.x + m.y * center.y
    h2 = radius * radius - (c - proj) * (c - proj)
    if h2 < 0.0:
        return []
    h = math.sqrt(h2)
    k = c - proj
    foot = App.Vector(center.x + m.x * k, center.y + m.y * k, 0.0)
    off = App.Vector(-m.y, m.x, 0.0)
    return [App.Vector(foot.x + off.x * h, foot.y + off.y * h, 0.0),
            App.Vector(foot.x - off.x * h, foot.y - off.y * h, 0.0)]


def _angle(center, p):
    return math.atan2(p.y - center.y, p.x - center.x)


def _arc_edge(center, radius, p_start, p_end, p_tip):
    """Edge of the circle (center, radius) that runs from p_start to p_end
    through the side nearest p_tip.

    Both complementary arcs are built and the one whose midpoint is closest
    to p_tip is kept, so the result does not depend on FreeCAD's arc
    orientation convention.  The edge is then oriented to start at p_start.
    """
    circle = Part.Circle(center, Z, radius)
    a_s = _angle(center, p_start)
    a_e = _angle(center, p_end)
    candidates = [
        Part.ArcOfCircle(circle, a_s, a_e).toShape(),
        Part.ArcOfCircle(circle, a_e, a_s).toShape(),
    ]

    def midpoint(edge):
        return edge.valueAt(0.5 * (edge.FirstParameter + edge.LastParameter))

    edge = min(candidates, key=lambda e: (midpoint(e) - p_tip).Length)
    if (edge.Vertexes[0].Point - p_start).Length > 1e-6:
        edge = edge.reverse()
    return edge


# ========================================================= trefoil outline ==
def trefoil_edges():
    """Closed chain of 3 outer arcs + 3 straight notch faces.

    Lobe i (axis LOBE_AXES_DEG[i]) is an arc of radius ARC_R centred at
    D_OFFSET along that axis.  Notch k lies between lobe k and lobe k+1, on
    the bisector direction, and is the line {p . m = NOTCH_FLAT_R}.  The arc
    of lobe i runs from its intersection with notch (i-1) to its intersection
    with notch i, passing through the lobe tip.
    """
    centers = [polar(D_OFFSET, a) for a in LOBE_AXES_DEG]
    notch_dirs = [(LOBE_AXES_DEG[k] + 60.0) % 360.0 for k in range(3)]

    # E[k] = notch k on circle k        (end of arc k)
    # S[k] = notch k-1 on circle k      (start of arc k)
    E = [None, None, None]
    S = [None, None, None]
    for k in range(3):
        m = polar(1.0, notch_dirs[k])
        m_ang = math.atan2(m.y, m.x)
        for li in (k, (k + 1) % 3):
            cand = line_circle_pts(m, NOTCH_FLAT_R, centers[li], ARC_R)
            if not cand:
                raise RuntimeError(
                    "notch line %d misses circle %d -- check NOTCH_FLAT_R"
                    % (k, li))
            best = min(cand, key=lambda p: abs(
                ang_diff(math.atan2(p.y, p.x), m_ang)))
            if li == k:
                E[k] = best
            else:
                S[(k + 1) % 3] = best

    edges = []
    for i in range(3):
        tip = polar(TIP_DIST, LOBE_AXES_DEG[i])
        edges.append(_arc_edge(centers[i], ARC_R, S[i], E[i], tip))
        edges.append(Part.LineSegment(E[i], S[(i + 1) % 3]).toShape())
    return edges


def trefoil_face():
    """Planar face of the trefoil pocket, with a polygon fallback."""
    edges = trefoil_edges()
    try:
        return Part.Face(Part.Wire(edges))
    except Exception:                                          # noqa: BLE001
        # Robust fallback: discretise the same edges into a closed polygon.
        pts = []
        for edge in edges:
            pts.extend(edge.discretize(32)[:-1])
        return Part.Face(Part.makePolygon(pts + [pts[0]]))


# ==================================================================== main ==
def build():
    print("=" * 68)
    print("build_part_v7  ->  %s" % os.path.join(OUT_DIR, DOC_NAME))
    print("=" * 68)
    print("hexagon    R %8.2f mm  (= %.3f in, across flats %.2f mm)"
          % (R_HEX_CIRCUM, R_HEX_CIRCUM / IN,
             2.0 * R_HEX_CIRCUM * math.cos(math.radians(30.0))))
    print("trefoil    lobe R %.2f mm, tip %.2f mm, notch %.2f mm"
          % (ARC_R, TIP_DIST, NOTCH_FLAT_R))
    print("pocket     %s, depth %.1f mm"
          % ("through" if POCKET_THROUGH else "blind", POCKET_DEPTH))
    print("bore       D %.1f mm, thickness %.1f mm" % (BORE_D, THICKNESS))

    doc = App.newDocument(DOC_NAME)

    # 1. hexagonal blank -----------------------------------------------------
    hex_pts = [polar(R_HEX_CIRCUM, 60.0 * i) for i in range(6)]
    hex_face = Part.Face(Part.makePolygon(hex_pts + [hex_pts[0]]))
    solid = hex_face.extrude(App.Vector(0.0, 0.0, THICKNESS))

    # 2. trefoil pocket ------------------------------------------------------
    depth = THICKNESS if POCKET_THROUGH else POCKET_DEPTH
    z0 = 0.0 if POCKET_THROUGH else THICKNESS - POCKET_DEPTH
    cutter = trefoil_face().extrude(App.Vector(0.0, 0.0, depth + 1.0))
    cutter.translate(App.Vector(0.0, 0.0, z0 - 0.5))
    solid = solid.cut(cutter)

    # 3. central bore --------------------------------------------------------
    solid = solid.cut(Part.makeCylinder(
        BORE_D / 2.0, THICKNESS + 4.0, App.Vector(0.0, 0.0, -2.0), Z))

    solid = solid.removeSplitter()
    if not solid.isValid():
        solid.fix(1e-7, 1e-7, 1e-7)

    part = doc.addObject("Part::Feature", "Part")
    part.Shape = solid
    part.Label = DOC_NAME

    doc.recompute()

    # 4. save (project rule: /workspace/FreeCAD_Models by default) -----------
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

    # 5. report --------------------------------------------------------------
    sh = part.Shape
    bb = sh.BoundBox
    print("-" * 68)
    print("solids %d   valid %s   faces %d"
          % (len(sh.Solids), sh.isValid(), len(sh.Faces)))
    print("volume %.1f cm3" % (sh.Volume / 1000.0))
    print("bbox   X %.2f..%.2f   Y %.2f..%.2f   Z %.2f..%.2f"
          % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    print("across flats %.2f mm   thickness %.2f mm"
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


if __name__ == "__main__":
    main()
