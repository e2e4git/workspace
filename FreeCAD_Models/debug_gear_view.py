import os
import sys

import FreeCAD as App
import FreeCADGui as Gui

doc = App.openDocument("/workspace/results/gear.FCStd")
print("doc:", doc.Name, "objects:", [o.Name for o in doc.Objects])
for o in doc.Objects:
    vo = getattr(o, "ViewObject", None)
    print("  ", o.Name, "shape:", o.Shape.isValid() if hasattr(o, "Shape") else None,
          "VO:", vo, "vis:", getattr(vo, "Visibility", None))

Gui.showMainWindow()
Gui.activateWorkbench("PartWorkbench")
ad = Gui.activeDocument()
print("activeDocument:", ad)
view = ad.activeView()
print("view:", view, "size:", view.getSize())
for o in doc.Objects:
    if getattr(o, "ViewObject", None):
        o.ViewObject.Visibility = True
        o.ViewObject.show()

view.setCameraType("Orthographic")
view.setAxisCross(False)
view.viewIsometric()
view.fitAll()
Gui.updateGui()
print("camera:", view.getCameraOrientation())
print("fit:", view.getSize())
view.saveImage("/workspace/results/gear_iso.png", 1600, 1200, "White")
print("SAVED")
sys.stdout.flush()
os._exit(0)
