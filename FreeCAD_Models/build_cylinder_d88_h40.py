"""Build a simple cylinder: diameter 88 mm, height 40 mm.

Saved to /home/igor/Downloads/cylinder.FCStd
Run with: /usr/lib/freecad/bin/freecadcmd-python3 FreeCAD_Models/build_cylinder_d88_h40.py
"""

import os

import FreeCAD
import Part  # noqa: F401  (ensures Part workbench is loaded)

DIAMETER = 88.0
HEIGHT = 40.0

OUT_DIR = "/home/igor/Downloads"
OUT_PATH = os.path.join(OUT_DIR, "cylinder.FCStd")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    doc_name = "cylinder_d88_h40"
    existing = [d.Name for d in FreeCAD.listDocuments().values()]
    if doc_name in existing:
        FreeCAD.closeDocument(doc_name)

    doc = FreeCAD.newDocument(doc_name)

    cyl = doc.addObject("Part::Cylinder", "Cylinder")
    cyl.Radius = DIAMETER / 2.0
    cyl.Height = HEIGHT
    cyl.Angle = 360.0
    doc.recompute()

    doc.saveAs(OUT_PATH)

    print("SAVED           :", OUT_PATH)
    print("FILE EXISTS     :", os.path.exists(OUT_PATH))
    print("FILE SIZE (B)   :", os.path.getsize(OUT_PATH) if os.path.exists(OUT_PATH) else "n/a")
    print("RADIUS (mm)     :", cyl.Radius)
    print("DIAMETER (mm)   :", cyl.Radius * 2.0)
    print("HEIGHT (mm)     :", cyl.Height)
    print("VOLUME (mm^3)   :", round(cyl.Shape.Volume, 3))
    print("BOUND BOX       :", cyl.Shape.BoundBox)

    FreeCAD.closeDocument(doc.Name)


# freecadcmd does not always set __name__ to "__main__", so call main() directly.
main()
