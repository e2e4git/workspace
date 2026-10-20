# -*- coding: utf-8 -*-
"""photo_geom.py — measure the photo's window / spoke geometry in polar
coordinates (after foreshortening correction)."""
import math
import numpy as np

pw = np.load("/workspace/FreeCAD_Models/out/polar_wood.npy")
NA, NR = pw.shape
rr = np.linspace(0, 360.0, NR)
print("polar map %dx%d" % pw.shape)

# tip / root
r_out = np.zeros(NA)
for i in range(NA):
    idx = np.nonzero(pw[i])[0]
    r_out[i] = rr[idx[-1]] if len(idx) else 0.0
Rtip = r_out.max()
Rroot = np.percentile(r_out, 2)
print("Rtip=%.1f  Rroot=%.1f  depth=%.1f (%.3f of tip)" %
      (Rtip, Rroot, Rtip - Rroot, (Rtip - Rroot) / Rtip))

# angular runs of material at given radii
def runs_at(r, band=3):
    j = int(r / 360.0 * NR)
    col = pw[:, max(0, j - band):j + band + 1].mean(axis=1) > 0.5
    out = []
    s = None
    for i, v in enumerate(col):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s * 360.0 / NA, (i - 1) * 360.0 / NA))
            s = None
    if s is not None:
        out.append((s * 360.0 / NA, (NA - 1) * 360.0 / NA))
    return out


print("\nmaterial angular runs (deg) vs radius:")
for r in (20, 40, 60, 80, 100, 120, 150, 180, 200, 220, 240, 260, 270, 280, 290, 300):
    rr_ = runs_at(r)
    print("  r=%3d : %s" % (r, "  ".join("%.1f..%.1f" % t for t in rr_)))

# window inner boundary: for each angle, the largest r < 250 that is still
# material (i.e. the end of the hub/spoke region)
print("\nspoke angular width (deg) vs radius:")
for r in (40, 60, 80, 100, 120, 150, 180, 200, 220, 240, 260):
    rr_ = runs_at(r)
    ws = [t for t in rr_ if (t[1] - t[0]) < 120]
    if ws:
        print("  r=%3d : %s" % (r, "  ".join("%.1f..%.1f (w=%.1f)" % (t[0], t[1], t[1] - t[0]) for t in ws)))

# window outer boundary and inner boundary along the window axes
print("\nwindow edges along the window axes:")
for a in (26, 86, 146, 206, 266, 326):
    i = int(a / 360.0 * NA)
    col = pw[(i - 3) % NA:(i + 4) % NA].mean(axis=0) > 0.5
    idx = np.nonzero(col)[0]
    segs = []
    s = None
    for j, v in enumerate(col):
        if v and s is None:
            s = j
        elif not v and s is not None:
            segs.append((rr[s], rr[j - 1]))
            s = None
    if s is not None:
        segs.append((rr[s], rr[-1]))
    print("  %3d deg : %s" % (a, "  ".join("%.0f..%.0f" % t for t in segs)))
