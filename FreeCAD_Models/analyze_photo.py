# -*- coding: utf-8 -*-
"""analyze_photo.py — quantitative extraction of the real part from the photo.
  * wood mask (saturation based)
  * outer tooth profile (tip / root circles, tooth count)
  * the 3 window openings: contours + polar description
  * bore + hub
"""
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = "/workspace/src/drawings/Screenshot (3).png"
OUT = "/workspace/FreeCAD_Models/out/"
rgb = np.array(Image.open(SRC).convert("RGB")).astype(int)
H, W, _ = rgb.shape
R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
mx = rgb.max(axis=2)
mn = rgb.min(axis=2)
sat = mx - mn

wood = (sat > 30) & (mx < 245) & (R > B + 12)
wood = ndimage.binary_closing(wood, np.ones((3, 3)))
print("raw wood px", wood.sum())

# largest component = the gear
lab, n = ndimage.label(wood, structure=np.ones((3, 3)))
sizes = ndimage.sum(wood, lab, range(1, n + 1))
order = np.argsort(sizes)[::-1][:6]
for i in order:
    sl = ndimage.find_objects(lab == i + 1)[0]
    print("  comp %d size=%d bbox x[%d..%d] y[%d..%d]" %
          (i + 1, sizes[i], sl[1].start, sl[1].stop, sl[0].start, sl[0].stop))
gear_id = order[0] + 1
wood = (lab == gear_id)
ys, xs = np.nonzero(wood)
print("gear bbox x[%d..%d] y[%d..%d]" % (xs.min(), xs.max(), ys.min(), ys.max()))

# ---- centre from the bore hole -------------------------------------------
bg = ~wood
lab2, n2 = ndimage.label(bg, structure=np.ones((3, 3)))
border = set(lab2[0, :]) | set(lab2[-1, :]) | set(lab2[:, 0]) | set(lab2[:, -1])
holes = []
for i in range(1, n2 + 1):
    if i in border:
        continue
    area = int((lab2 == i).sum())
    if area < 150:
        continue
    yy, xx = np.nonzero(lab2 == i)
    holes.append(dict(id=i, area=area, x0=xx.min(), x1=xx.max(),
                       y0=yy.min(), y1=yy.max(), cx=xx.mean(), cy=yy.mean()))
holes.sort(key=lambda h: -h["area"])
print("\nopenings:")
for h in holes:
    print("   id=%3d area=%7d bbox x[%d..%d] y[%d..%d] cen=(%.1f,%.1f)" %
          (h["id"], h["area"], h["x0"], h["x1"], h["y0"], h["y1"], h["cx"], h["cy"]))

bore = min(holes, key=lambda h: h["area"])
print("\nBORE: area=%d bbox=%s cen=(%.1f,%.1f)  r_mean=%.2f" %
      (bore["area"], (bore["x0"], bore["x1"], bore["y0"], bore["y1"]),
       bore["cx"], bore["cy"], math.sqrt(bore["area"] / math.pi)))
CX, CY = bore["cx"], bore["cy"]
print("  centre used:", CX, CY)

# ---- outer tooth profile --------------------------------------------------
filled = ndimage.binary_fill_holes(wood)
ys, xs = np.nonzero(filled)
print("\nouter bbox: x[%d..%d] y[%d..%d]  ->  w=%d h=%d" %
      (xs.min(), xs.max(), ys.min(), ys.max(), xs.max() - xs.min(), ys.max() - ys.min()))

n = 3600
th = np.linspace(0, 2 * math.pi, n, endpoint=False)
rmax = max(xs.max() - CX, ys.max() - CY) + 6
prof = np.zeros(n)
for i, a in enumerate(th):
    dx, dy = math.cos(a), -math.sin(a)
    rs = np.arange(0, rmax, 0.4)
    xx = np.rint(CX + rs * dx).astype(int)
    yy = np.rint(CY + rs * dy).astype(int)
    ok = (xx >= 0) & (xx < W) & (yy >= 0) & (yy < H)
    hit = np.zeros(len(rs), bool)
    hit[ok] = filled[yy[ok], xx[ok]]
    idx = np.nonzero(hit)[0]
    prof[i] = rs[idx[-1]] if len(idx) else 0.0

print("tip radius: max=%.1f  mean of top 5%%=%.1f" %
      (prof.max(), np.sort(prof)[-int(0.05 * n):].mean()))
print("root radius: min=%.1f" % prof.min())
# tooth count: count local maxima
sm = np.convolve(prof, np.ones(9) / 9, mode="same")
peaks = []
for i in range(2, n - 2):
    if sm[i] > sm[i - 1] and sm[i] >= sm[i + 1] and sm[i] > 250:
        peaks.append(i)
# merge close peaks
merged = []
for p in peaks:
    if not merged or p - merged[-1] > 12:
        merged.append(p)
print("tooth count (peaks):", len(merged))
if len(merged) > 1:
    d = np.diff(merged)
    print("  peak spacing (deg): min %.2f max %.2f mean %.2f" %
          (d.min() * 360 / n, d.max() * 360 / n, d.mean() * 360 / n))
np.save(OUT + "photo_outer_profile.npy", prof)

# print the profile every 1 deg for 0..90 to see the tooth shape
print("\nprofile 0..120 deg (1 deg):")
print(" ".join("%d:%.0f" % (math.degrees(th[i]), prof[i]) for i in range(0, 120)))
