# -*- coding: utf-8 -*-
"""line_families.py: project the sketch geometry onto the normals of the
30/120 deg line families and list the resulting line offsets.  The spacing
between two parallel lines is exactly what a width dimension measures."""
import math
import numpy as np
from PIL import Image

rgb = np.array(Image.open("/workspace/FreeCAD_Models/out/sketch_clean.png").convert("RGB"))
m = (rgb[:, :, 0] < 128) & (rgb[:, :, 1] < 128)
ys, xs = np.nonzero(m)
pts = np.stack([xs, ys], 1).astype(float)
CX, CY = 455.0, 365.0
SCALE = 107.2

for normal_deg in (30, 60, 90, 120, 150, 0):
    a = math.radians(normal_deg)
    rho = pts[:, 0] * math.cos(a) + pts[:, 1] * math.sin(a)
    hist, edges = np.histogram(rho, bins=np.arange(rho.min(), rho.max() + 2, 1.0))
    # find local maxima with support
    peaks = []
    for i in range(2, len(hist) - 2):
        if hist[i] >= hist[i - 1] and hist[i] > hist[i + 1] and hist[i] >= 12:
            peaks.append((hist[i], edges[i] + 0.5))
    peaks.sort(reverse=True)
    print("normal %3d deg  (lines at %3d deg):" % (normal_deg, normal_deg + 90))
    seen = []
    for h, r in peaks:
        if any(abs(r - s) < 6 for s in seen):
            continue
        seen.append(r)
        # signed distance from the centre along this normal
        d = r - (CX * math.cos(a) + CY * math.sin(a))
        print("    rho=%8.1f  h=%3d   offset from centre = %8.1f px = %7.3f in" %
              (r, h, d, d / SCALE))
    print()
