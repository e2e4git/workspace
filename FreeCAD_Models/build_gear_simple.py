"""Простая прямозубая шестерня: Ø60 наружный, 12 зубьев, толщина 10, отверстие Ø10.

Запуск: freecadcmd FreeCAD_Models/build_gear_simple.py
Результат: /workspace/results/gear.FCStd
"""
import math
import os

import FreeCAD as App
import Part
from FreeCAD import Vector

OUT_DIR = "/workspace/results"
OUT_FILE = os.path.join(OUT_DIR, "gear.FCStd")

# --- параметры -------------------------------------------------------------
Z = 12                 # число зубьев
R_TIP = 30.0           # наружный радиус (Ø60)
R_ROOT = 24.0          # радиус впадин (высота зуба 6 мм)
THICKNESS = 10.0       # толщина
R_HOLE = 5.0           # отверстие Ø10

PITCH = 2.0 * math.pi / Z          # угловой шаг зуба = 30°
HALF_TIP = math.radians(5.5)       # половина угловой ширины вершины
HALF_ROOT = math.radians(9.0)      # половина угловой ширины у основания

# --- профиль ---------------------------------------------------------------
c_root = Part.Circle(Vector(0, 0, 0), Vector(0, 0, 1), R_ROOT)
c_tip = Part.Circle(Vector(0, 0, 0), Vector(0, 0, 1), R_TIP)


def pt(radius, angle):
    return Vector(radius * math.cos(angle), radius * math.sin(angle), 0.0)


edges = []
for i in range(Z):
    a = i * PITCH
    p1 = pt(R_ROOT, a - HALF_ROOT)   # начало зуба у основания
    p2 = pt(R_TIP, a - HALF_TIP)     # начало вершины
    p3 = pt(R_TIP, a + HALF_TIP)     # конец вершины
    p4 = pt(R_ROOT, a + HALF_ROOT)   # конец зуба у основания

    edges.append(Part.LineSegment(p1, p2).toShape())          # восходящий бок
    edges.append(Part.ArcOfCircle(c_tip, a - HALF_TIP, a + HALF_TIP).toShape())
    edges.append(Part.LineSegment(p3, p4).toShape())          # нисходящий бок
    edges.append(Part.ArcOfCircle(c_root, a + HALF_ROOT,
                                  (i + 1) * PITCH - HALF_ROOT).toShape())

wire = Part.Wire(edges)
if not wire.isClosed():
    raise RuntimeError("профиль не замкнут")

face = Part.Face(wire)
body = face.extrude(Vector(0, 0, THICKNESS))
hole = Part.makeCylinder(R_HOLE, THICKNESS, Vector(0, 0, 0), Vector(0, 0, 1))
gear = body.cut(hole).removeSplitter()

# --- документ --------------------------------------------------------------
doc = App.newDocument("gear")
obj = doc.addObject("Part::Feature", "Gear")
obj.Shape = gear
obj.Label = "Gear_Z12_D60_t10"
try:
    obj.ViewObject.ShapeColor = (0.75, 0.75, 0.78)
except Exception:
    pass
doc.recompute()

os.makedirs(OUT_DIR, exist_ok=True)
doc.saveAs(OUT_FILE)

bb = gear.BoundBox
print("valid      :", gear.isValid())
print("volume     :", round(gear.Volume, 1), "mm^3")
print("bbox X/Y/Z :", round(bb.XLength, 3), round(bb.YLength, 3), round(bb.ZLength, 3))
print("faces      :", len(gear.Faces), " solids:", len(gear.Solids))
print("saved      :", doc.FileName)
