# -*- coding: utf-8 -*-
"""
analyze_v5.py  —  fresh, self-contained analysis of
    src/drawings/Screenshot (2).png   (dimensioned sketch)
    src/drawings/Screenshot (3).png   (photo of the real part)

No OpenCV: pure numpy / scipy / PIL.

Outputs:
    FreeCAD_Models/out/skill_*.png   (zoom crops for visual check)
    FreeCAD_Models/out/photo_*.png
    printout of all measurements
"""
import os
import math
import numpy as np
from PIL import Image
from scipy import ndimage

SKETCH = "/workspace/src/drawings/Screenshot (2).png"
PHOTO = "/workspace/src/drawings/Screenshot (3).png"
OUT = "/workspace/FreeCAD_Models/out"
os.makedirs(OUT, exist_ok=True)


# ----------------------------------------------------------------- helpers ---
def load_gray(path):
    im = Image.open(path).convert("L")
    return np.array(im)


def binarize(g, thr=160):
    return g < thr


def save_gray(arr, name, upscale=1.0, bbox=None):
    if bbox is not None:
        x0, y0, x1, y1 = bbox
        arr = arr[y0:y1, x0:x1]
    im = Image.fromarray(arr.astype(np.uint8))
    if upscale != 1.0:
        im = im.resize((int(im.width * upscale), int(im.height * upscale)), Image.LANCZOS)
    p = os.path.join(OUT, name)
    im.save(p)
    return p


def hough_lines(mask, n_angles=1440, min_len=40, n_peaks=40):
    """Simple Hough transform -> list of (theta_deg, rho, support, (x0,y0,x1,y1))."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return []
    pts = np.stack([xs.astype(np.float64), ys.astype(np.float64)], 1)
    th = np.linspace(0, math.pi, n_angles, endpoint=False)
    # normal direction n = (cos th, sin th)
    c = np.cos(th)
    s = np.sin(th)
    rho = pts[:, 0:1] * c[None, :] + pts[:, 1:2] * s[None, :]
    rho = rho.astype(np.int32)
    off = rho.min()
    rho = rho - off
    rmax = rho.max()
    acc = np.zeros((len(th), rmax + 1), dtype=np.int32)
    for i in range(len(th)):
        np.add.at(acc[i], rho[:, i], 1)
    results = []
    work = acc.copy()
    for _ in range(n_peaks):
        idx = np.unravel_index(np.argmax(work), work.shape)
        it, ir = int(idx[0]), int(idx[1])
        sup = int(work[it, ir])
        if sup < min_len:
            break
        theta = th[it]
        rho_val = ir + off
        d = np.abs(pts[:, 0] * math.cos(theta) + pts[:, 1] * math.sin(theta) - rho_val)
        sel = d <= 1.2
        if sel.sum() >= 2:
            p = pts[sel]
            # extreme points along the line direction
            t = -p[:, 0] * math.sin(theta) + p[:, 1] * math.cos(theta)
            i0, i1 = int(np.argmin(t)), int(np.argmax(t))
            p0, p1 = tuple(p[i0]), tuple(p[i1])
            length = float(t.max() - t.min())
        else:
            p0 = p1 = (0, 0)
            length = 0.0
        results.append(dict(theta=math.degrees(theta), rho=rho_val, support=sup,
                            length=length, p0=p0, p1=p1))
        # suppress this line
        work[max(0, it - 6):it + 7, max(0, ir - 12):ir + 13] = 0
    return results


def ray_profile(mask, cx, cy, thetas, rmax):
    """max radius of a dark pixel along each ray from (cx,cy)."""
    H, W = mask.shape
    out = np.full(len(thetas), np.nan)
    for i, a in enumerate(thetas):
        dx, dy = math.cos(a), math.sin(a)
        rs = np.arange(0, rmax, 0.5)
        xs = np.rint(cx + rs * dx).astype(int)
        ys = np.rint(cy + rs * dy).astype(int)
        ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
        hit = np.zeros(len(rs), bool)
        hit[ok] = mask[ys[ok], xs[ok]]
        idx = np.nonzero(hit)[0]
        if len(idx):
            out[i] = rs[idx[-1]]
    return out


def polar_r(mask, cx, cy, n=3600, rmax=None):
    if rmax is None:
        ys, xs = np.nonzero(mask)
        rmax = int(math.hypot(ys.max() - cy, xs.max() - cx)) + 5
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    r = ray_profile(mask, cx, cy, th, rmax)
    return th, r


def circ_centre_of_ring(mask, region):
    """fit a circle to dark pixels inside a bbox region -> (cx,cy,r)"""
    x0, y0, x1, y1 = region
    sub = mask[y0:y1, x0:x1]
    ys, xs = np.nonzero(sub)
    xs = xs + x0
    ys = ys + y0
    A = np.stack([xs, ys, np.ones(len(xs))], 1).astype(float)
    b = (xs ** 2 + ys ** 2).astype(float)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = math.sqrt(sol[2] + cx ** 2 + cy ** 2)
    res = np.hypot(xs - cx, ys - cy) - r
    return cx, cy, r, float(np.abs(res).max())


# ============================================================ SKETCH =========
def analyse_sketch():
    g = load_gray(SKETCH)
    H, W = g.shape
    print("=" * 78)
    print("SKETCH  %s  size=%dx%d" % (SKETCH, W, H))
    m = binarize(g, 160)
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1][:12]
    print("components:", n)
    for i in order:
        sl = ndimage.find_objects(lab == i + 1)[0]
        print("   size=%6d  bbox x[%d..%d] y[%d..%d]" %
              (sizes[i], sl[1].start, sl[1].stop, sl[0].start, sl[0].stop))

    # --- zoom crops (for visual inspection) -------------------------------
    save_gray(g, "sketch_full.png", 1.0)
    # centre bore circle region
    save_gray(g, "sketch_center.png", 3.0, (330, 270, 560, 430))
    # top window + 2.24 dimension
    save_gray(g, "sketch_top.png", 3.0, (280, 60, 600, 260))
    # upper-right 1.25 dimension
    save_gray(g, "sketch_dim_ur.png", 3.0, (560, 140, 780, 300))
    # lower-left 1.25 dimension
    save_gray(g, "sketch_dim_ll.png", 3.0, (250, 330, 450, 520))
    # bottom 3.69 dimension
    save_gray(g, "sketch_bottom.png", 2.0, (200, 560, 700, 700))
    # left vertex of hexagon
    save_gray(g, "sketch_left.png", 2.0, (30, 280, 300, 460))

    # --- straight lines ----------------------------------------------------
    print("\n--- hough lines (longest first) ---")
    lines = hough_lines(m, n_angles=1440, min_len=60, n_peaks=60)
    lines.sort(key=lambda L: -L["length"])
    for L in lines[:28]:
        print("   th=%6.1f deg  rho=%7.1f  len=%6.1f  sup=%5d  p0=%s p1=%s" %
              (L["theta"], L["rho"], L["length"], L["support"],
               tuple(int(v) for v in L["p0"]), tuple(int(v) for v in L["p1"])))
    return g, m


# ============================================================= PHOTO =========
def analyse_photo():
    g = load_gray(PHOTO)
    H, W = g.shape
    print("=" * 78)
    print("PHOTO  %s  size=%dx%d" % (PHOTO, W, H))
    g3 = np.array(Image.open(PHOTO).convert("RGB"))
    # wood = darker & saturated ; background = near white
    mx = g3.max(axis=2).astype(int)
    mn = g3.min(axis=2).astype(int)
    sat = mx - mn
    wood = (g < 215) & (sat > 28)
    wood = ndimage.binary_closing(wood, np.ones((5, 5)))
    wood = ndimage.binary_fill_holes(wood)
    ys, xs = np.nonzero(wood)
    print("wood pixels:", len(xs), " bbox x[%d..%d] y[%d..%d]" %
          (xs.min(), xs.max(), ys.min(), ys.max()))
    cx, cy = (xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0
    print("bbox centre: %.1f %.1f" % (cx, cy))

    save_gray((~wood).astype(np.uint8) * 255, "photo_mask.png", 1.0)
    save_gray(g, "photo_full.png", 1.0)

    # holes: white regions inside the wood -> background components not touching border
    bg = ~wood
    lab, n = ndimage.label(bg, structure=np.ones((3, 3)))
    border = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    holes = []
    for i in range(1, n + 1):
        if i in border:
            continue
        area = int((lab == i).sum())
        if area < 400:
            continue
        ys2, xs2 = np.nonzero(lab == i)
        holes.append((area, i, xs2.min(), xs2.max(), ys2.min(), ys2.max(),
                      xs2.mean(), ys2.mean()))
    holes.sort(reverse=True)
    print("\nwindows (holes): %d" % len(holes))
    for h in holes:
        print("   area=%7d  x[%4d..%4d] y[%4d..%4d]  centroid=(%.1f,%.1f)" %
              (h[0], h[2], h[3], h[4], h[5], h[6], h[7]))
    return g, wood, (cx, cy), holes, lab


if __name__ == "__main__":
    analyse_sketch()
    analyse_photo()
