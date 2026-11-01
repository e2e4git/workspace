import os
import FreeCAD as App
import Part

OUT_DIR = "/home/igor/Downloads"
OUT_PATH = os.path.join(OUT_DIR, "cylinder.FCStd")

os.makedirs(OUT_DIR, exist_ok=True)

doc = App.newDocument("cylinder")
cyl = doc.addObject("Part::Cylinder", "Cylinder")
cyl.Radius = 77.0 / 2.0   # diameter 77 mm
cyl.Height = 40.0         # height 40 mm
cyl.Angle = 360.0
doc.recompute()

doc.saveAs(OUT_PATH)

print("Saved:", OUT_PATH)
print("Exists:", os.path.exists(OUT_PATH))
print("Size bytes:", os.path.getsize(OUT_PATH))
print("Radius:", cyl.Radius, "Diameter:", cyl.Radius * 2, "Height:", cyl.Height)
print("Volume mm^3:", round(cyl.Shape.Volume, 3))
