# -*- coding: utf-8 -*-
"""Build a simple cylinder: diameter 100 mm, height 44 mm.

Run with:  freecadcmd FreeCAD_Models/build_cylinder_100x44.py
Output:    /workspace/FreeCAD_Models/cylinder_100x44.FCStd
"""
import os

import FreeCAD as App
import Part  # noqa: F401  (ensures Part module is loaded)

DOC_NAME = "cylinder_100x44"
OUT_DIR = "/workspace/FreeCAD_Models"
OUT_FILE = os.path.join(OUT_DIR, "cylinder_100x44.FCStd")

DIAMETER = 100.0
HEIGHT = 44.0

if DOC_NAME in App.listDocuments():
    App.closeDocument(DOC_NAME)

doc = App.newDocument(DOC_NAME)

cyl = doc.addObject("Part::Cylinder", "Cylinder")
cyl.Label = "Cylinder D100 x 44"
cyl.Radius = DIAMETER / 2.0
cyl.Height = HEIGHT
cyl.Angle = 360.0
# Base circle centred on the origin, axis along +Z
cyl.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

doc.recompute()

os.makedirs(OUT_DIR, exist_ok=True)
doc.saveAs(OUT_FILE)

bb = cyl.Shape.BoundBox
print("=== cylinder built ===")
print("file      :", OUT_FILE)
print("diameter  :", cyl.Radius * 2.0, "mm")
print("height    :", cyl.Height, "mm")
print("volume    :", round(cyl.Shape.Volume, 2), "mm^3")
print("bbox X    :", round(bb.XLength, 3), "mm")
print("bbox Y    :", round(bb.YLength, 3), "mm")
print("bbox Z    :", round(bb.ZLength, 3), "mm")
print("solids    :", len(cyl.Shape.Solids))
print("valid     :", cyl.Shape.isValid())
print("--- edges ---")
for i, e in enumerate(cyl.Shape.Edges, start=1):
    c = e.Curve
    print("Edge%d" % i, c.__class__.__name__,
          "len=%.3f" % e.Length,
          "center=", [round(v, 2) for v in e.CenterOfMass])
