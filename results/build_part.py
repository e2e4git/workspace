# -*- coding: utf-8 -*-
"""
Листовой кронштейн-уголок (L-bracket).

Параметры:
  - толщина листа .......... 2 мм
  - внутренний радиус гиба .. 2 мм (наружный 4 мм)
  - горизонтальная полка .... 60 мм
  - вертикальная полка ...... 40 мм
  - длина (ширина) .......... 80 мм
  - два отверстия Ø9 ........ по оси полки, в 20 мм от торцов

Скрипт строит деталь и сохраняет:
  results/bracket.FCStd
  results/bracket.step
При наличии GUI переключает вид на изометрию.
"""

import os
import math

import FreeCAD as App
import Part

# ----------------------------------------------------------------------------
# Параметры детали
# ----------------------------------------------------------------------------
THICKNESS       = 2.0                          # мм, толщина листа
BEND_RADIUS_IN  = 2.0                          # мм, внутренний радиус гиба
BEND_RADIUS_OUT = BEND_RADIUS_IN + THICKNESS   # 4 мм, наружный радиус гиба

FLANGE_H = 60.0                                # мм, горизонтальная полка (X)
FLANGE_V = 40.0                                # мм, вертикальная полка (Z)
LENGTH   = 80.0                                # мм, длина детали (Y)

HOLE_DIA  = 9.0                                # мм, диаметр отверстий
HOLE_EDGE = 20.0                               # мм, от торца до центра отверстия

# ----------------------------------------------------------------------------
# Каталог сохранения: папка, где лежит скрипт (results/)
# ----------------------------------------------------------------------------
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

FCSTD_PATH = os.path.join(BASE_DIR, "bracket.FCStd")
STEP_PATH  = os.path.join(BASE_DIR, "bracket.step")

# ----------------------------------------------------------------------------
# Профиль в плоскости XZ (y = 0)
# ----------------------------------------------------------------------------
c45 = math.cos(math.radians(45.0))

# Точки контура (x, y, z)
P1 = App.Vector(FLANGE_H, 0.0, 0.0)                 # низ, торец гориз. полки
P2 = App.Vector(BEND_RADIUS_OUT, 0.0, 0.0)          # начало наружной дуги
P3 = App.Vector(0.0, 0.0, BEND_RADIUS_OUT)          # конец наружной дуги
P4 = App.Vector(0.0, 0.0, FLANGE_V)                 # верх верт. полки
P5 = App.Vector(THICKNESS, 0.0, FLANGE_V)           # внутренняя кромка верха
P6 = App.Vector(THICKNESS, 0.0, BEND_RADIUS_OUT)    # начало внутренней дуги
P7 = App.Vector(BEND_RADIUS_OUT, 0.0, THICKNESS)    # конец внутренней дуги
P8 = App.Vector(FLANGE_H, 0.0, THICKNESS)           # верх, торец гориз. полки

# Середины дуг (Part.Arc строится по трём точкам)
outer_mid = App.Vector(
    BEND_RADIUS_OUT - BEND_RADIUS_OUT * c45, 0.0,
    BEND_RADIUS_OUT - BEND_RADIUS_OUT * c45,
)
inner_mid = App.Vector(
    BEND_RADIUS_OUT - BEND_RADIUS_IN * c45, 0.0,
    BEND_RADIUS_OUT - BEND_RADIUS_IN * c45,
)

edges = [
    Part.makeLine(P1, P2),
    Part.Arc(P2, outer_mid, P3),
    Part.makeLine(P3, P4),
    Part.makeLine(P4, P5),
    Part.makeLine(P5, P6),
    Part.Arc(P6, inner_mid, P7),
    Part.makeLine(P7, P8),
    Part.makeLine(P8, P1),
]

wire = Part.Wire(edges)
face = Part.Face(wire)

# Выдавливание вдоль Y на длину детали
solid = face.extrude(App.Vector(0.0, LENGTH, 0.0))

# ----------------------------------------------------------------------------
# Отверстия Ø9 в горизонтальной полке
# ----------------------------------------------------------------------------
hole_radius = HOLE_DIA / 2.0
hole_x = FLANGE_H / 2.0                      # по оси полки
for hole_y in (HOLE_EDGE, LENGTH - HOLE_EDGE):
    cutter = Part.makeCylinder(
        hole_radius,
        THICKNESS + 2.0,
        App.Vector(hole_x, hole_y, -1.0),
        App.Vector(0.0, 0.0, 1.0),
    )
    solid = solid.cut(cutter)

solid = solid.removeSplitter()

# ----------------------------------------------------------------------------
# Документ FreeCAD
# ----------------------------------------------------------------------------
doc = App.newDocument("bracket")
obj = doc.addObject("Part::Feature", "Bracket")
obj.Shape = solid
obj.Label = "Bracket_2mm"

try:
    obj.ViewObject.ShapeColor = (0.75, 0.78, 0.82)
except Exception:
    pass

doc.recompute()

# ----------------------------------------------------------------------------
# Сохранение .FCStd и .step
# ----------------------------------------------------------------------------
doc.saveAs(FCSTD_PATH)
Part.export([obj], STEP_PATH)

print("FCStd:", FCSTD_PATH)
print("STEP :", STEP_PATH)

# ----------------------------------------------------------------------------
# Изометрический вид (только при наличии GUI)
# ----------------------------------------------------------------------------
try:
    import FreeCADGui as Gui
    view = Gui.activeDocument().activeView()
    view.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
except Exception:
    pass
