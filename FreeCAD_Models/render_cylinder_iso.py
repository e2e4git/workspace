# -*- coding: utf-8 -*-
"""Render an isometric screenshot of results/cylinder.FCStd.

Run with:  xvfb-run -a freecad FreeCAD_Models/render_cylinder_iso.py
Output:    /workspace/results/cylinder_iso.png
"""
import FreeCAD as App
import FreeCADGui as Gui

DOC_FILE = "/workspace/results/cylinder.FCStd"
PNG_FILE = "/workspace/results/cylinder_iso.png"

doc = App.openDocument(DOC_FILE)

Gui.showMainWindow()
Gui.activateWorkbench("PartWorkbench")

view = Gui.activeDocument().activeView()
view.setAxisCross(True)
view.viewIsometric()
view.fitAll()
Gui.updateGui()

view.saveImage(PNG_FILE, 1200, 900, "White")
print("SAVED:", PNG_FILE)
