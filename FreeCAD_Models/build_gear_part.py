# -*- coding: utf-8 -*-
"""
Headless FreeCAD build: 3-spoke wooden-style spur gear
per drawing 'src/drawings/Screenshot (2).png' + photo 'src/drawings/Screenshot (3).png'.

Run:  freecadcmd /workspace/FreeCAD_Models/build_gear_part.py
Out:  /workspace/FreeCAD_Models/GearPart.FCStd (+ .step)

All units mm. 1 in = 25.4 mm.
Real shape (from photo): toothed rim + 3 straight spokes (120 deg) + small hub,
THREE THROUGH windows, through bore. Hexagon on drawing = construction layout
for the 3 spokes (every other vertex direction), not a solid feature.
"""
import math
import FreeCAD as App
import Part

IN = 25.4

# ---------------- Parameters (drawing + photo + user data) ----------------
THICKNESS = 20.0                      # user
BORE_D    = 10.0                      # user
R_TIP     = 3.69 * IN                 # 93.726  tooth tip circle (= hexagon circumradius)
R_ROOT    = R_TIP - 1.25 * IN         # 61.976  tooth root circle (right 1.25 in)
R_RIM_I   = 1.94 * IN                 # 49.276  rim inner radius (1.94 in):
                                      #   window chord check: 2*49.276*sin(35deg)=56.5 ~ 2.24 in OK
N_TEETH   = 36                        # from drawing count
SPOKE_W   = 1.25 * IN                 # 31.75   spoke width (left 1.25 in)

# Reasonable defaults from photo proportions:
HUB_R     = 17.0                      # hub slightly wider than spokes
RIM_FILLET_R = 10.0                   # large fillets at spoke-rim junctions (photo)
TOOTH_TIP_HALF = 1.6                  # deg, sharper teeth (photo shows pointier teeth)
TOOTH_ROOT_HALF = 3.4                 # deg

# ---------------- Toothed disk profile ----------------
def polar(r, deg):
    a = math.radians(deg)
    return App.Vector(r * math.cos(a), r * math.sin(a), 0)

pts = []
pitch = 360.0 / N_TEETH
for i in range(N_TEETH):
    th = i * pitch
    pts.append(polar(R_ROOT, th - pitch / 2.0 + 0.2))
    pts.append(polar(R_TIP,  th - TOOTH_TIP_HALF))
    pts.append(polar(R_TIP,  th + TOOTH_TIP_HALF))
pts.append(pts[0])
toothed_face = Part.Face(Part.makePolygon(pts))
rim = toothed_face.extrude(App.Vector(0, 0, THICKNESS))
rim = rim.cut(Part.makeCylinder(R_RIM_I, THICKNESS))   # rim band with teeth

# ---------------- Spokes + hub ----------------
spokes = []
for k in range(3):
    b = Part.makeBox(SPOKE_W, R_RIM_I + 8.0 + 25.0, THICKNESS,
                     App.Vector(-SPOKE_W / 2.0, -25.0, 0))
    b.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 90 + 120 * k)
    spokes.append(b)
hub = Part.makeCylinder(HUB_R, THICKNESS)

solid = rim.multiFuse(spokes + [hub]).removeSplitter()

# ---------------- Fillet vertical edges at spoke-rim junctions ----------------
edges = []
for e in solid.Edges:
    try:
        if not isinstance(e.Curve, Part.Line):
            continue
    except Exception:
        continue
    vs = e.Vertexes
    if len(vs) != 2:
        continue
    if abs(vs[0].X - vs[1].X) < 1e-6 and abs(vs[0].Y - vs[1].Y) < 1e-6:  # vertical
        r = math.hypot(vs[0].X, vs[0].Y)
        if 30.0 < r < R_RIM_I + 1.0:
            edges.append(e)
if edges:
    try:
        solid = solid.makeFillet(RIM_FILLET_R, edges)
        print("Filleted %d rim-junction edges" % len(edges))
    except Exception as ex:
        print("Fillet skipped:", ex)

# ---------------- Bore ----------------
solid = solid.cut(Part.makeCylinder(BORE_D / 2.0, THICKNESS + 2, App.Vector(0, 0, -1)))

# ---------------- Hexagon construction wire ----------------
hex_pts = [polar(R_TIP, 60 * i) for i in range(6)]
hex_pts.append(hex_pts[0])
hex_wire = Part.makePolygon(hex_pts)

# ---------------- Document ----------------
doc = App.newDocument("GearPart")
obj = doc.addObject("Part::Feature", "GearPart")
obj.Shape = solid
if obj.ViewObject:
    try:
        obj.ViewObject.ShapeColor = (0.72, 0.55, 0.35)   # wood-ish
    except Exception:
        pass

hx = doc.addObject("Part::Feature", "Hexagon_Construction")
hx.Shape = hex_wire

notes = (
    "Interpretation corrected by photo Screenshot (3).png:\n"
    "- THROUGH windows between 3 straight spokes (not blind pockets, no stadium lobes)\n"
    "- R_tip=93.726 (3.69in), R_root=61.976 (tip - 1.25in), 36 teeth\n"
    "- Rim inner radius 49.276 (1.94in); window chord check ~2.24in OK\n"
    "- Spoke width 31.75 (left 1.25in)\n"
    "Defaults from photo: hub R=17, rim-junction fillet R=10, thickness 20, bore 10\n"
    "Hexagon = construction geometry for 120deg spoke layout (wire, not solid)\n"
)
an = doc.addObject("App::Annotation", "Notes_Assumptions")
an.LabelText = notes.split("\n")

doc.recompute()
out = "/workspace/FreeCAD_Models/GearPart.FCStd"
doc.saveAs(out)
solid.exportStep("/workspace/FreeCAD_Models/GearPart.step")
print("Saved:", out)
print("Volume mm^3:", round(solid.Volume, 1))
print("Valid:", solid.isValid(), "| Solids:", len(solid.Solids))
bb = solid.BoundBox
print("BBox: %.3f..%.3f x %.3f..%.3f x %.3f..%.3f" %
      (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
