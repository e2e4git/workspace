# -*- coding: utf-8 -*-
import FreeCAD as App
import Part
import FreeCADGui as Gui

doc = App.newDocument("T")
box = doc.addObject("Part::Box", "Box")
box.Length = 20; box.Width = 10; box.Height = 5
doc.recompute()

Gui.showMainWindow()
Gui.activateWorkbench("PartWorkbench")
Gui.activeDocument().activeView().viewAxonometric()
Gui.activeDocument().activeView().fitAll()
Gui.updateGui()
Gui.activeDocument().activeView().saveImage("/workspace/FreeCAD_Models/_test_iso.png", 800, 600, "White")
print("SAVED")
