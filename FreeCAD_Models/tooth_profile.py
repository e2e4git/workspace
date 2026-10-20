# -*- coding: utf-8 -*-
"""tooth_profile.py — determine the tooth count and extract the average
tooth profile of the real part (normalised, for use in the CAD build)."""
import math
import numpy as np

pw = np.load("/workspace/FreeCAD_Models/out/polar_wood.npy")
NA, NR = pw.shape
rr = np.linspace(0, 360.0, NR)
r_out = np.zeros(NA)
for i in range(NA):
    idx = np.nonzero(pw[i])[0]
    r_out[i] = rr[idx[-1]] if len(idx) else 0.0

# smooth
k = np.ones(7) / 7.0
sm = np.convolve(np.r_[r_out[-3:], r_out, r_out[:3]], k, mode="same")[3:-3]
sm -= sm.mean()

# autocorrelation to get the tooth count
ac = np.correlate(sm, sm, "full")[NA - 1:]
ac /= ac[0]
print("autocorrelation peaks (lag, value):")
for lag in range(3, 120):
    if ac[lag] > ac[lag - 1] and ac[lag] >= ac[lag + 1] and ac[lag] > 0.25:
        print("   lag %3d  -> %5.1f teeth   ac=%.3f" % (lag, NA / lag, ac[lag]))

# best tooth count = maximises the ac peak
cands = [(NA / lag, ac[lag]) for lag in range(4, 120)
         if ac[lag] > ac[lag - 1] and ac[lag] >= ac[lag + 1] and ac[lag] > 0.2]
cands.sort(reverse=True)
print("\ntop candidates:", [(round(c[0], 1), round(c[1], 3)) for c in cands[:6]])
N = int(round(cands[0][0]))
print("chosen tooth count:", N)

# phase: find the angle of a tooth tip (max of sm)
phase = float(np.argmax(sm))
print("tooth tip at %.2f deg" % (phase * 360.0 / NA))

# average profile over one tooth pitch
M = NA // N
prof = np.zeros(M)
for t in range(N):
    i0 = int(round(phase + t * M))
    idx = [(i0 + j) % NA for j in range(M)]
    prof += r_out[idx]
prof /= N
print("one tooth profile (radius at %d samples over %.2f deg):" %
      (M, 360.0 / N))
print("  min=%.1f max=%.1f" % (prof.min(), prof.max()))
print("  " + " ".join("%.0f" % v for v in prof[::max(1, M // 24)]))
np.save("/workspace/FreeCAD_Models/out/tooth_profile.npy", prof)
np.save("/workspace/FreeCAD_Models/out/tooth_params.npy", np.array([N, phase, M]))
print("\nsaved tooth profile (%d samples)" % M)
