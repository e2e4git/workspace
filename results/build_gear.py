# -*- coding: utf-8 -*-
"""Простая прямозубая шестерня: Ø60, толщина 10, z=12, отверстие Ø10.

Профиль: дуги по вершинам и впадинам + прямые (радиальные) боковые стороны.
Запуск: freecadcmd results/build_gear.py
Результат: /workspace/results/gear.FCStd
"""
import math
import os

import FreeCAD as App
import Part

OUT = "/workspace/results/gear.FCStd"

# --- параметры -------------------------------------------------------------
Z = 12                 # число зубьев
TIP_D = 60.0           # внешний диаметр, мм
THICKNESS = 10.0       # толщина, мм
BORE_D = 10.0          # отверстие в центре, мм

R_TIP = TIP_D / 2.0                       # 30.0
MODULE = TIP_D / (Z + 2.0)                # m = da / (z + 2) = 4.2857
R_PITCH = MODULE * Z / 2.0                # делительный радиус
R_ROOT = R_PITCH - 1.0 * MODULE           # радиус впадин
PITCH_ANGLE = 2.0 * math.pi / Z           # угловой шаг

# полутолщина зуба (по дуге) на делительном радиусе
HALF_THICK_PITCH = math.pi * MODULE / 4.0
HALF_ANGLE_ROOT_LIMIT = 0.62 * PITCH_ANGLE / 2.0


def half_angle(r):
    """Половина углового размера зуба на радиусе r (прямой профиль)."""
    half_arc = HALF_THICK_PITCH - (r - R_PITCH) * math.tan(math.radians(20.0))
    return min(abs(half_arc) / r, HALF_ANGLE_ROOT_LIMIT)


def pt(r, a):
    return App.Vector(r * math.cos(a), r * math.sin(a), 0.0)


def arc(r, a1, a2):
    circle = Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), r)
    return Part.ArcOfCircle(circle, a1, a2).toShape()


# --- профиль: дуга вершины -> бок -> дуга впадины -> бок -> ... -------------
TIP_HALF = half_angle(R_TIP)
ROOT_HALF = HALF_ANGLE_ROOT_LIMIT

edges = []
for i in range(Z):
    a = i * PITCH_ANGLE
    # дуга вершины зуба
    edges.append(arc(R_TIP, a - TIP_HALF, a + TIP_HALF))
    # боковая сторона: вершина -> впадина
    edges.append(Part.LineSegment(pt(R_TIP, a + TIP_HALF),
                                  pt(R_ROOT, a + ROOT_HALF)).toShape())
    # дуга впадины до начала следующего зуба
    edges.append(arc(R_ROOT, a + ROOT_HALF, a + PITCH_ANGLE - ROOT_HALF))
    # боковая сторона: впадина -> вершина следующего зуба
    edges.append(Part.LineSegment(pt(R_ROOT, a + PITCH_ANGLE - ROOT_HALF),
                                  pt(R_TIP, a + PITCH_ANGLE - TIP_HALF)).toShape())

wire = Part.Wire(edges)
face = Part.Face(wire)
rim = face.extrude(App.Vector(0, 0, THICKNESS))

bore = Part.makeCylinder(BORE_D / 2.0, THICKNESS, App.Vector(0, 0, 0),
                         App.Vector(0, 0, 1))
gear_shape = rim.cut(bore).removeSplitter()

# --- документ --------------------------------------------------------------
for d in list(App.listDocuments()):
    App.closeDocument(d)

doc = App.newDocument("gear")

profile = doc.addObject("Part::Feature", "GearRim")
profile.Shape = rim
profile.Label = "Зубчатый венец"

tool = doc.addObject("Part::Feature", "Bore")
tool.Shape = bore
tool.Label = "Отверстие"

gear = doc.addObject("Part::Cut", "Gear")
gear.Base = profile
gear.Tool = tool
gear.Label = "Шестерня z12 Ø60x10"

# ViewObject существует только в GUI-режиме (не в freecadcmd)
if getattr(tool, "ViewObject", None) is not None:
    tool.ViewObject.Visibility = False
if getattr(gear, "ViewObject", None) is not None:
    gear.ViewObject.ShapeColor = (0.78, 0.72, 0.35)

doc.recompute()
doc.saveAs(OUT)

bb = gear_shape.BoundBox
print("MODULE      = %.4f mm" % MODULE)
print("R_TIP       = %.3f mm" % R_TIP)
print("R_PITCH     = %.3f mm" % R_PITCH)
print("R_ROOT      = %.3f mm" % R_ROOT)
print("TIP_HALF    = %.2f deg" % math.degrees(TIP_HALF))
print("ROOT_HALF   = %.2f deg" % math.degrees(ROOT_HALF))
print("VOLUME      = %.1f mm^3" % gear_shape.Volume)
print("BBOX        = %.2f x %.2f x %.2f" % (bb.XLength, bb.YLength, bb.ZLength))
print("VALID       = %s" % gear_shape.isValid())
print("SAVED       = %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
