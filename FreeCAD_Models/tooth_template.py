# -*- coding: utf-8 -*-
"""tooth_template.py — build a clean CAD tooth template from the photo.
The template is the raw profile of one well-formed tooth of the real part,
resampled to the mean tooth pitch and scaled to the model's tip radius."""
import math
import numpy as np

pw = np.load("/workspace/FreeCAD_Models/out/polar_wood.npy")
NA, NR = pw.shape
rr = np.linspace(0, 360.0, NR)
r_out = np.zeros(NA)
for i in range(NA):
    idx = np.nonzero(pw[i])[0]
    r_out[i] = rr[idx[-1]] if len(idx) else 0.0

# fine resample
FINE = 14400
ang = np.linspace(0, 360.0, FINE, endpoint=False)
src = np.arange(NA) * 360.0 / NA
rf = np.interp(ang, src, r_out, period=360.0)

# mean tooth pitch from the autocorrelation
sm = rf - rf.mean()
ac = np.correlate(sm, sm, "full")[FINE - 1:]
ac /= ac[0]
# local maxima of the autocorrelation, strongest one wins
cands = [(ac[L], L) for L in range(20, 2000)
         if ac[L] > ac[L - 1] and ac[L] >= ac[L + 1]]
cands.sort(reverse=True)
print("autocorr candidates:", [(L, round(a, 3)) for a, L in cands[:5]])
lag = cands[0][1]
N = int(round(FINE / lag))
pitch = 360.0 / N
print("tooth pitch %.3f deg  ->  N = %d" % (pitch, N))

# pick the best-formed tooth: the one whose profile is closest to the
# average of all teeth, measured over +-0.5 pitch around its tip
def tooth_profile_at(tip_deg):
    i0 = int((tip_deg - 0.5 * pitch) / 360.0 * FINE) % FINE
    idx = (i0 + np.arange(int(pitch / 360.0 * FINE) + 1)) % FINE
    return rf[idx]


tips = []
for k in range(N):
    a0 = k * pitch
    i0 = int(a0 / 360.0 * FINE)
    i1 = int((a0 + pitch) / 360.0 * FINE)
    j = int(np.argmax(rf[i0:i1]))
    tips.append(a0 + j * 360.0 / FINE)

M = int(pitch / 360.0 * FINE) + 1
profs = []
for t in tips:
    i0 = int((t - 0.5 * pitch) / 360.0 * FINE) % FINE
    profs.append(rf[(i0 + np.arange(M)) % FINE])
profs = np.array(profs)
avg = profs.mean(axis=0)
err = np.abs(profs - avg).mean(axis=1)
# among the well formed teeth pick the one with the sharpest root
depth = profs.max(axis=1) - profs.min(axis=1)
rootw = ((profs < (profs.min(axis=1)[:, None] + 0.12 * depth[:, None])).sum(axis=1))
cand = [k for k in range(len(profs)) if err[k] < 1.6]
best = min(cand, key=lambda k: rootw[k])
print("tooth chosen at %.2f deg: deviation %.2f px, root width %.1f deg "
      "(candidates %d)" % (tips[best], err[best], rootw[best] * pitch / M, len(cand)))
print("root widths: min %d  median %d  max %d samples"
      % (rootw.min(), int(np.median(rootw)), rootw.max()))

# use the best tooth, aligned so that the tip is at the centre of the pitch
p = profs[best]
imax = int(np.argmax(p))
half = M // 2
# roll so that the tip is in the middle of the array (index half)
rolled = np.roll(p, half - imax)
print("template: max %.1f  min %.1f  (ratio %.4f)" %
      (rolled.max(), rolled.min(), rolled.min() / rolled.max()))
for j in range(0, M, 2):
    print("   %2d/%2d  %6.1f   %5.2f deg" %
          (j, M, rolled[j], (j - half) / float(M) * pitch))

np.save("/workspace/FreeCAD_Models/out/tooth_template.npy", rolled)
np.save("/workspace/FreeCAD_Models/out/tooth_params.npy",
        np.array([N, pitch, M, rolled.max(), rolled.min()]))
print("saved tooth template (%d samples, N=%d)" % (M, N))
