# -*- coding: utf-8 -*-
"""
fit_profile.py — vectorise the cleaned profile (construction geometry already
removed by extract_profile.py) and fit a line / circle to every curve.
"""
import math
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, "/workspace/FreeCAD_Models")
from analyze_drawing import (binarise, strip_blobs, thin, trace_edges,  # noqa
                             prune_spurs, merge_chains, fit_arc, fit_circle)

CX, CY = 455.5, 366.0
PX2IN = 1.0 / 107.18

ink, shape = binarise("/workspace/FreeCAD_Models/drawing_profile_only.png")
clean = ink
sk = thin(clean)
sk = prune_spurs(sk, 16)
edges = trace_edges(sk)
edges = merge_chains(edges)
edges = [e for e in edges if len(e) >= 25]
print("edges:", len(edges))

prims = []
for path in edges:
    pts = np.array([(p[1], p[0]) for p in path], float)
    f = fit_arc(pts)
    f["npts"] = len(pts)
    f["p_start"] = tuple(pts[0])
    f["p_end"] = tuple(pts[-1])
    prims.append(f)

prims.sort(key=lambda f: -f["npts"])
print()
print("%-6s %-6s %-6s %-38s %-10s %-20s" %
      ("type", "npts", "err", "geometry", "r[px/in]", "endpoints"))
for f in prims:
    if f["type"] == "circle":
        cx, cy = f["centre"]
        g = "R=%.1f c=(%.1f,%.1f) sweep=%.0f" % (f["radius"], cx, cy, f["sweep"])
        extra = "%.1f / %.3f" % (f["radius"], f["radius"] * PX2IN)
        d = math.hypot(cx - CX, cy - CY)
        ang = math.degrees(math.atan2(CY - cy, cx - CX)) % 360
        extra += "  d=%.0f@%.0f" % (d, ang)
    elif f["type"] == "line":
        g = "ang=%.2f n=(%.3f,%.3f) len=%.1f" % (
            f["angle"], f["n"][0], f["n"][1], f["length"])
        extra = "len=%.1f px" % f["length"]
    else:
        g = "free-form"
        extra = ""
    print("%-6s %-6d %-6.2f %-38s %-10s (%.0f,%.0f)-(%.0f,%.0f)" %
          (f["type"], f["npts"], f["err"], g, extra,
           f["p_start"][0], f["p_start"][1], f["p_end"][0], f["p_end"][1]))
