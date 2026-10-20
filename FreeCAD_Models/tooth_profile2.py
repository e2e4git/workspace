# -*- coding: utf-8 -*-
"""tooth_profile2.py — robust tooth count / average tooth profile extraction."""
import math
import numpy as np

pw = np.load("/workspace/FreeCAD_Models/out/polar_wood.npy")
NA, NR = pw.shape
rr = np.linspace(0, 360.0, NR)
r_out = np.zeros(NA)
for i in range(NA):
    idx = np.nonzero(pw[i])[0]
    r_out[i] = rr[idx[-1]] if len(idx) else 0.0

print("profile stats: min %.1f max %.1f" % (r_out.min(), r_out.max()))

# local maxima (tooth tips)
peaks = []
for i in range(NA):
    a, b, c = r_out[(i - 1) % NA], r_out[i], r_out[(i + 1) % NA]
    if b >= a and b > c and b > 330:
        peaks.append(i)
# merge neighbours
merged = []
for p in peaks:
    if not merged or p - merged[-1] > 6:
        merged.append(p)
    else:
        merged[-1] = p
d = np.diff(merged)
print("tip peaks: %d   spacing: min %d max %d mean %.2f -> %.1f teeth" %
      (len(merged), d.min(), d.max(), d.mean(), NA / d.mean()))

N = int(round(NA / d.mean()))
M = NA // N
print("N=%d  M=%d samples/pitch" % (N, M))

# phase: align so that sample 0 of the profile is a tooth tip
tips = np.array(merged)
# fit: tips should be at phase + k*M
best = None
for ph in range(M):
    errs = []
    for t in tips:
        k = round((t - ph) / M)
        errs.append(abs(t - (ph + k * M)))
    e = np.mean(errs)
    if best is None or e < best[0]:
        best = (e, ph)
phase = best[1]
print("phase=%d (mean alignment error %.2f samples)" % (phase, best[0]))

prof = np.zeros(M)
for t in range(N):
    i0 = (phase + t * M) % NA
    prof += r_out[(i0 + np.arange(M)) % NA]
prof /= N
print("tooth profile: min=%.1f max=%.1f  (tip=%.1f root=%.1f)" %
      (prof.min(), prof.max(), prof.max(), prof.min()))
for j in range(0, M, 2):
    print("   %2d/%2d  %6.1f   (angle %5.2f deg)" %
          (j, M, prof[j], j * 360.0 / N))
np.save("/workspace/FreeCAD_Models/out/tooth_profile.npy", prof)
np.save("/workspace/FreeCAD_Models/out/tooth_params.npy",
        np.array([N, phase, M], dtype=float))
print("saved.")
