"""Изометрический (и вид сверху) скриншот results/gear.FCStd.

Запуск: xvfb-run -a freecad FreeCAD_Models/render_gear_iso.py
"""
import os
import sys

import FreeCAD as App
import FreeCADGui as Gui

LOG = "/tmp/render_gear.log"


def log(msg):
    with open(LOG, "a") as fh:
        fh.write(str(msg) + "\n")


open(LOG, "w").close()

doc = App.openDocument("/workspace/results/gear.FCStd")
log("opened %s objects=%s" % (doc.Name, [o.Name for o in doc.Objects]))

Gui.activateWorkbench("PartWorkbench")

# Документ сохранён из freecadcmd, где ViewObject отсутствует, поэтому
# видимость объектов при загрузке сбрасывается в False — включаем нужные.
for obj in doc.Objects:
    try:
        obj.ViewObject.Visibility = obj.Name == "Gear"
        log("  %s visible=%s" % (obj.Name, obj.ViewObject.Visibility))
    except Exception as exc:
        log("  %s no ViewObject: %r" % (obj.Name, exc))

gear = doc.getObject("Gear")
if gear is not None and getattr(gear, "ViewObject", None) is not None:
    gear.ViewObject.ShapeColor = (0.78, 0.72, 0.35)

view = Gui.activeDocument().activeView()
view.setCameraType("Orthographic")
view.viewIsometric()
try:
    Gui.runCommand("Std_DrawStyleFlatLines")
except Exception as exc:
    log("drawstyle: %r" % (exc,))
view.fitAll()
Gui.updateGui()

view.saveImage("/workspace/results/gear_iso.png", 1600, 1200, "White")
log("saved gear_iso.png %d bytes" % os.path.getsize("/workspace/results/gear_iso.png"))

view.viewTop()
view.fitAll()
Gui.updateGui()
view.saveImage("/workspace/results/gear_top.png", 1200, 1200, "White")
log("saved gear_top.png %d bytes" % os.path.getsize("/workspace/results/gear_top.png"))

sys.stdout.flush()
os._exit(0)
