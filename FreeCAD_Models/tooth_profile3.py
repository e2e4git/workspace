# -*- coding: utf-8 -*-
"""tooth_profile3.py — tooth count + averaged tooth profile via fine resampling
and per-tooth tip alignment (the photo's teeth are hand-cut and irregular)."""
import math
import numpy as np

pw = np.load("/workspace/FreeCAD_Models/out/polar_wood.npy")
NA, NR = pw.shape
rr = np.linspace(0, 360.0, NR)
r_out = np.zeros(NA)
for i in range(NA):
    idx = np.nonzero(pw[i])[0]
    r_out[i] = rr[idx[-1]] if len(idx) else 0.0

# fine resample: 0.05 deg
FINE = 7200
ang = np.linspace(0, 360.0, FINE, endpoint=False)
src = np.arange(NA) * 360.0 / NA
rf = np.interp(ang, src, r_out, period=360.0)

for N in (48, 50, 52, 54, 55, 56):
    pitch = 360.0 / N
    # per-tooth tip: max of rf in each sector
    tips = []
    for k in range(N):
        a0 = k * pitch
        i0 = int(a0 / 360.0 * FINE)
        i1 = int((a0 + pitch) / 360.0 * FINE)
        seg = rf[i0:i1]
        j = int(np.argmax(seg))
        tips.append(a0 + j * 360.0 / FINE)
    tips = np.array(tips)
    d = np.diff(tips)
    prof = []
    M = 60
    for k in range(N):
        t = tips[k]
        idx = (t + np.linspace(-0.45, 0.45, M) * pitch) % 360.0
        prof.append(np.interp(idx, ang, rf, period=360.0))
    prof = np.mean(prof, axis=0)
    print("N=%2d  pitch=%.2f  tip spread=%4.1f..%4.1f  profile min=%6.1f max=%6.1f  "
          "span(root->tip)=%5.1f" %
          (N, pitch, prof[0], prof[-1], prof.min(), prof.max(),
           prof.max() - prof.min()))
    if N == 50:
        np.save("/workspace/FreeCAD_Models/out/tooth_profile.npy", prof)
        np.save("/workspace/FreeCAD_Models/out/tooth_params.npy",
                np.array([N, float(tips[0]), M], dtype=float))
        print("   profile samples (60):")
        print("   " + " ".join("%.0f" % v for v in prof[::2]))
