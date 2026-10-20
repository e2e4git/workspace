# -*- coding: utf-8 -*-
"""
build_gear_part_v4.py  —  strict Sketcher build (NO teeth, NO windows).

Solid hexagonal blank + blind trefoil (3-lobe) pocket + central through bore.

Run:  freecadcmd /workspace/FreeCAD_Models/build_gear_part_v4.py
Out:  /workspace/FreeCAD_Models/GearPart_v4.FCStd

Geometry (from 'src/drawings/Screenshot (2).png', 1 in = 25.4 mm):
  * Hexagon: the 3.69 in dimension spans ONE SIDE of the regular hexagon
    (between its two lower vertices). For a regular hexagon side = circumradius,
    so R_hex (circumradius) = 93.726 mm, across-flats = 162.27 mm.
    NOTE: the trefoil flat faces alone sit 49.276 mm from the centre, so a
    blank only 93.726 mm wide across flats is impossible — the drawing's own
    proportions confirm 3.69 in = side = circumradius.
  * Trefoil pocket: 3 arcs R = 31.75 mm (1.25 in), centres offset d from the
    origin at 120 deg, chosen so the lobe tips (the "flat faces" of the
    pocket, i.e. the outermost tangent points) are 49.276 mm (1.94 in) from
    the centre:  d = 49.276 - 31.75 = 17.526 mm.
    The three arcs are joined by three straight lines (flat notch faces).
  * Pocket depth: 10 mm blind (set POCKET_THROUGH = True for through).
  * Central bore: Ø10 mm, through.

Fallback (if you prefer the pure-boolean version the user suggested):
  set USE_CYLINDER_FALLBACK = True -> the pocket becomes the union of three
  R31.75 cylinders (a smooth clover), subtracted at 10 mm depth.
"""
import math
import FreeCAD as App
import Part
import Sketcher

# ----------------------------- parameters ----------------------------------
IN = 25.4
R_HEX_CIRCUM   = 3.69 * IN          # 93.726 mm  hexagon circumradius (= side)
THICKNESS      = 20.0               # mm
ARC_R          = 1.25 * IN          # 31.75 mm   trefoil arc radius
TIP_DIST       = 1.94 * IN          # 49.276 mm  centre -> lobe tip ("flat face")
D_OFFSET       = TIP_DIST - ARC_R   # 17.526 mm  arc-centre offset from origin
# "distance between the flat faces" = 56.896 mm between mid-points of two
# adjacent straight notch lines (120 deg apart): r*sqrt(3) = 56.896
NOTCH_FLAT_R   = (2.24 * IN) / math.sqrt(3.0)   # 32.85 mm  origin -> notch line
POCKET_DEPTH   = 10.0               # mm  blind pocket depth
POCKET_THROUGH = False              # True -> through cut
BORE_D         = 10.0               # mm  central through hole
LOBE_AXES_DEG  = (90.0, 210.0, 330.0)
USE_CYLINDER_FALLBACK = False       # True -> 3-cylinder boolean pocket
DOC_NAME       = "GearPart_v4"
OUT_PATH       = "/workspace/FreeCAD_Models/GearPart_v4.FCStd"

# ----------------------------- helpers -------------------------------------
def polar(r, deg):
    a = math.radians(deg)
    return App.Vector(r * math.cos(a), r * math.sin(a), 0)

def norm_ang(a):
    while a < 0.0:
        a += 2.0 * math.pi
    while a >= 2.0 * math.pi:
        a -= 2.0 * math.pi
    return a

def ang_diff(a, b):
    """signed smallest difference a-b in (-pi, pi]"""
    d = a - b
    while d > math.pi:
        d -= 2.0 * math.pi
    while d < -math.pi:
        d += 2.0 * math.pi
    return d

def line_circle_pts(m, c, cc, r):
    """Points where the line {p . m = c} (m unit vector, in XY plane)
    intersects the circle with centre cc and radius r."""
    proj = m.x * cc.x + m.y * cc.y       # projection of cc onto m
    h2 = r * r - (c - proj) * (c - proj)
    if h2 < 0.0:
        return []
    h = math.sqrt(h2)
    k = c - proj                          # signed distance cc -> line along m
    foot = App.Vector(cc.x + m.x * k, cc.y + m.y * k, 0.0)   # foot on cc's normal
    off = App.Vector(-m.y, m.x, 0.0)     # unit vector along the line
    return [App.Vector(foot.x + off.x * h, foot.y + off.y * h, 0.0),
            App.Vector(foot.x - off.x * h, foot.y - off.y * h, 0.0)]

# --------------------------- trefoil outline --------------------------------
def trefoil_geometry():
    """Closed wire: 3 outer arcs (R = ARC_R, centres at D_OFFSET on the lobe
    axes, tips at TIP_DIST = 49.276 mm) joined by 3 straight notch lines
    (each at distance NOTCH_FLAT_R = 32.85 mm from the origin, so the
    mid-points of adjacent flat faces are 2*NOTCH_FLAT_R*sin(60deg) = 56.896
    mm apart). Returns [arc0, line0, arc1, line1, arc2, line2] chained CCW."""
    axes = [polar(1.0, ax) for ax in LOBE_AXES_DEG]
    centers = [App.Vector(axes[i].x * D_OFFSET, axes[i].y * D_OFFSET, 0.0)
               for i in range(3)]
    # notch k sits between lobe k and lobe (k+1)%3:
    # lobe0=90 & lobe1=210 -> 150 ; lobe1 & lobe2=330 -> 270 ; lobe2 & lobe0 -> 30
    notch_dirs = [150.0, 270.0, 30.0]

    # For notch k (between lobe k and lobe k+1 in CCW order) the line
    # {p . m = NOTCH_FLAT_R} cuts each of the two circles in 2 points;
    # keep the one nearest the notch bisector direction m (the cut-off
    # cusp point), i.e. min |angle(p) - angle(m)|.
    # arc_end[k]    = CCW end of arc k   (on circle k,   at notch k)
    # next_start[k] = CCW start of arc k+1 (on circle k+1, at notch k)
    arc_end = []
    next_start = []
    for k, nd in enumerate(notch_dirs):
        m = polar(1.0, nd)
        for li in (k, (k + 1) % 3):
            cand = line_circle_pts(m, NOTCH_FLAT_R, centers[li], ARC_R)
            if not cand:
                raise RuntimeError("notch line misses circle - check NOTCH_FLAT_R")
            best = min(cand, key=lambda p: abs(ang_diff(
                math.atan2(p.y, p.x), math.atan2(m.y, m.x))))
            (arc_end if li == k else next_start).append(best)
    # arc i runs CCW from its right notch (notch i) to its left notch (notch i-1)
    geoms = []
    for i in range(3):
        c = centers[i]
        p_arcend = arc_end[i]                      # CCW end of arc i (at notch i)
        p_arcst = next_start[(i + 2) % 3]          # CCW start of arc i (at notch i-1)
        a1 = norm_ang(math.atan2(p_arcend.y - c.y, p_arcend.x - c.x))
        a2 = norm_ang(math.atan2(p_arcst.y - c.y, p_arcst.x - c.x))
        tip = polar(TIP_DIST, LOBE_AXES_DEG[i])
        at = norm_ang(math.atan2(tip.y - c.y, tip.x - c.x))
        # Part.ArcOfCircle(circle, a1, a2) sweeps CCW from a1 to a2.
        # Choose the sweep (a1->a2 or a2->a1) that contains the tip angle.
        if ang_diff(at, a1) % (2 * math.pi) <= ang_diff(a2, a1) % (2 * math.pi):
            arc = Part.ArcOfCircle(Part.Circle(c, App.Vector(0, 0, 1), ARC_R), a1, a2)
            p0, p1 = p_arcend, p_arcst
        else:
            arc = Part.ArcOfCircle(Part.Circle(c, App.Vector(0, 0, 1), ARC_R), a2, a1)
            p0, p1 = p_arcst, p_arcend
        geoms.append((arc, p0, p1))
    # reorder into a single CCW chain: arc -> line to next arc's start
    order = sorted(geoms, key=lambda g: math.degrees(
        math.atan2(g[1].y, g[1].x)) % 360.0)
    out = []
    for i in range(3):
        arc, p0, p1 = order[i]
        _, np0, _ = order[(i + 1) % 3]
        out.append(arc)
        out.append(Part.LineSegment(p1, np0))
    return out

# ----------------------------- document ------------------------------------
doc = App.newDocument(DOC_NAME)

# --- 1. hexagon sketch + Pad ---
sk_hex = doc.addObject("Sketcher::SketchObject", "Sketch_Hexagon")
sk_hex.MapMode = "Deactivated"
pts = [polar(R_HEX_CIRCUM, 60.0 * i) for i in range(6)]
for i in range(6):
    sk_hex.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 6]), False)
for i in range(6):
    sk_hex.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 6, 1))

pad = doc.addObject("Part::Extrusion", "Pad_Hexagon")
pad.Base = sk_hex
pad.DirMode = "Normal"
pad.Solid = True
pad.LengthFwd = THICKNESS
doc.recompute()
if pad.Shape.isNull() or not pad.Shape.isValid():
    raise RuntimeError("Hexagon pad failed")

# --- 2. trefoil pocket sketch on the top face (z = THICKNESS) ---
if not USE_CYLINDER_FALLBACK:
    sk_tri = doc.addObject("Sketcher::SketchObject", "Sketch_Trefoil")
    sk_tri.MapMode = "Deactivated"
    geoms = trefoil_geometry()
    for g in geoms:
        sk_tri.addGeometry(g, False)
    # coincidence constraints to close the wire
    n = len(geoms)
    for i in range(n):
        sk_tri.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % n, 1))
    sk_tri.Placement = App.Placement(App.Vector(0, 0, THICKNESS), App.Rotation())

    cut_tri = doc.addObject("Part::Extrusion", "Trefoil_Extrusion")
    cut_tri.Base = sk_tri
    cut_tri.DirMode = "Normal"
    cut_tri.Solid = True
    cut_tri.Reversed = True
    cut_tri.LengthFwd = THICKNESS if POCKET_THROUGH else POCKET_DEPTH
    doc.recompute()

    body1 = doc.addObject("Part::Cut", "Cut_Trefoil")
    body1.Base = pad
    body1.Tool = cut_tri
    doc.recompute()
    current = body1
    if current.Shape.isNull() or not current.Shape.isValid():
        raise RuntimeError("Trefoil pocket cut failed")
else:
    # --- fallback: three overlapping cylinders subtracted at 10 mm depth ---
    depth = THICKNESS if POCKET_THROUGH else POCKET_DEPTH
    z0 = 0.0 if POCKET_THROUGH else THICKNESS - POCKET_DEPTH
    cyls = []
    for ax in LOBE_AXES_DEG:
        c = polar(D_OFFSET, ax)
        cyls.append(Part.makeCylinder(ARC_R, depth, App.Vector(c.x, c.y, z0)))
    tool = cyls[0].multiFuse(cyls[1:])
    obj = doc.addObject("Part::Feature", "TrefoilTool")
    obj.Shape = tool
    current = doc.addObject("Part::Cut", "Cut_Trefoil")
    current.Base = pad
    current.Tool = obj
    doc.recompute()

# --- 3. central bore Ø10, through ---
sk_bore = doc.addObject("Sketcher::SketchObject", "Sketch_Bore")
sk_bore.MapMode = "Deactivated"
sk_bore.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), BORE_D / 2.0), False)
sk_bore.Placement = App.Placement(App.Vector(0, 0, THICKNESS), App.Rotation())

cut_bore = doc.addObject("Part::Extrusion", "Bore_Extrusion")
cut_bore.Base = sk_bore
cut_bore.DirMode = "Normal"
cut_bore.Solid = True
cut_bore.Reversed = True
cut_bore.LengthFwd = THICKNESS + 2.0
doc.recompute()

final = doc.addObject("Part::Cut", "TrefoilHexBlank")
final.Base = current
final.Tool = cut_bore
doc.recompute()

# hide intermediates
for o in doc.Objects:
    if o is not final and o.ViewObject:
        try:
            o.ViewObject.Visibility = False
        except Exception:
            pass
if final.ViewObject:
    try:
        final.ViewObject.ShapeColor = (0.72, 0.55, 0.35)
    except Exception:
        pass

doc.recompute()
shp = final.Shape
shp.exportStep(OUT_PATH.replace(".FCStd", ".step"))
doc.saveAs(OUT_PATH)
print("Saved:", OUT_PATH)
print("Valid:", shp.isValid(), "| Solids:", len(shp.Solids))
print("Volume mm^3:", round(shp.Volume, 1))
bb = shp.BoundBox
print("BBox: %.3f..%.3f x %.3f..%.3f x %.3f..%.3f" %
      (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
