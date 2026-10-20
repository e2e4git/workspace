# -*- coding: utf-8 -*-
"""
analyze_drawing.py — vectorise the 2D drawing in ``src/drawings/Screenshot (2).png``
and fit lines / circles to every traced curve, so the part geometry can be
reconstructed exactly instead of guessed.

Pipeline
  1. binarise
  2. drop filled arrow-heads and text glyphs
  3. Zhang–Suen thinning
  4. build skeleton graph, split at junctions / endpoints
  5. trace each edge, fit a line (RANSAC-ish) or a circle (algebraic least squares)

Output: a table of primitives (type, parameters, endpoints) + an SVG overlay
so the result can be checked visually.
"""
import math
import os
import sys

import numpy as np
from scipy import ndimage

IMG = "/workspace/src/drawings/Screenshot (2).png"
OUT_SVG = "/workspace/FreeCAD_Models/drawing_vectors.svg"
OUT_PNG = "/workspace/FreeCAD_Models/drawing_overlay.png"
CX, CY = 455.5, 366.0        # centre of the part (bore centre)


# --------------------------------------------------------------------------- #
# 1. binarise
# --------------------------------------------------------------------------- #
def binarise(path):
    from PIL import Image
    a = np.array(Image.open(path).convert("L"))
    return a < 200, a.shape


# --------------------------------------------------------------------------- #
# 2. remove arrow-heads (solid blobs) and text glyphs
# --------------------------------------------------------------------------- #
def strip_blobs(ink):
    """Remove pixels belonging to solid arrow-heads / text glyphs."""
    out = ink.copy()
    # --- arrow heads: 3x3 window completely ink --------------------------- #
    dense = ndimage.uniform_filter(ink.astype(np.float32), size=3)
    solid = (dense > 0.995) & ink
    solid = ndimage.binary_dilation(solid, np.ones((3, 3)))
    out[solid] = False

    # --- text glyphs: small isolated blocks -------------------------------- #
    lab, n = ndimage.label(out, structure=np.ones((3, 3)))
    objs = ndimage.find_objects(lab)
    keep = np.ones(n + 1, bool)
    for i, sl in enumerate(objs, start=1):
        ys, xs = sl
        h, w = ys.stop - ys.start, xs.stop - xs.start
        area = (lab[sl] == i).sum()
        if h <= 24 and w <= 24 and area >= 12:
            fill = area / float(h * w)
            if fill > 0.25:
                keep[i] = False
    out[~keep[lab]] = False
    return out


# --------------------------------------------------------------------------- #
# 3. Zhang–Suen thinning
# --------------------------------------------------------------------------- #
def thin(img):
    img = img.astype(np.uint8).copy()
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            P = np.pad(img, 1)
            p2 = P[:-2, 1:-1]
            p3 = P[:-2, 2:]
            p4 = P[1:-1, 2:]
            p5 = P[2:, 2:]
            p6 = P[2:, 1:-1]
            p7 = P[2:, :-2]
            p8 = P[1:-1, :-2]
            p9 = P[:-2, :-2]
            B = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8)
                    for i in range(8))
            if step == 0:
                cond = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                cond = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            rm = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & cond
            if rm.any():
                img[rm] = 0
                changed = True
    return img.astype(bool)


# --------------------------------------------------------------------------- #
# 4./5. skeleton graph + tracing
# --------------------------------------------------------------------------- #
def skeleton_graph(sk):
    H, W = sk.shape
    nb = ndimage.convolve(sk.astype(np.int16), np.ones((3, 3), np.int16),
                           mode="constant", cval=0) - sk.astype(np.int16)
    return nb


def trace_edges(sk):
    """Split the skeleton into edges between nodes (endpoints / junctions)."""
    H, W = sk.shape
    nb = skeleton_graph(sk)
    nbrs = {}
    ys, xs = np.nonzero(sk)
    for y, x in zip(ys, xs):
        lst = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and sk[yy, xx]:
                    lst.append((yy, xx))
        nbrs[(y, x)] = lst

    nodes = set(p for p in nbrs if len(nbrs[p]) != 2)
    used = set()
    edges = []

    for node in nodes:
        for nxt in nbrs[node]:
            if (node, nxt) in used:
                continue
            path = [node, nxt]
            used.add((node, nxt))
            used.add((nxt, node))
            prev, cur = node, nxt
            while cur not in nodes:
                step = None
                for cand in nbrs[cur]:
                    if cand == prev or (cur, cand) in used:
                        continue
                    step = cand
                    break
                if step is None:
                    break
                used.add((cur, step))
                used.add((step, cur))
                path.append(step)
                prev, cur = cur, step
            edges.append(path)

    # isolated loops (no node at all)
    rest = [p for p in nbrs if p not in nodes and
            not any((p, q) in used for q in nbrs[p])]
    while rest:
        start = rest.pop()
        path = [start]
        prev, cur = None, start
        while True:
            step = None
            for cand in nbrs[cur]:
                if cand == prev:
                    continue
                step = cand
                break
            if step is None or step == start:
                break
            if (cur, step) in used:
                break
            used.add((cur, step))
            used.add((step, cur))
            path.append(step)
            prev, cur = cur, step
        if len(path) > 4:
            edges.append(path)
    return edges


# --------------------------------------------------------------------------- #
# fitting
# --------------------------------------------------------------------------- #
def fit_line(pts):
    x = pts[:, 0]
    y = pts[:, 1]
    mx, my = x.mean(), y.mean()
    sxx = ((x - mx) ** 2).sum()
    syy = ((y - my) ** 2).sum()
    sxy = ((x - mx) * (y - my)).sum()
    theta = 0.5 * math.atan2(2 * sxy, sxx - syy)
    nx, ny = -math.sin(theta), math.cos(theta)
    d = (x - mx) * nx + (y - my) * ny
    err = float(np.abs(d).max())
    return dict(type="line", err=err,
                p0=(mx - nx * d.mean(), my - ny * d.mean()),
                n=(nx, ny), angle=math.degrees(theta) % 180.0,
                length=float(np.hypot(x[-1] - x[0], y[-1] - y[0])))


def fit_circle(pts):
    x = pts[:, 0]
    y = pts[:, 1]
    A = np.column_stack([x, y, np.ones(len(x))])
    b = x ** 2 + y ** 2
    try:
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    except Exception:
        return None
    cx = sol[0] / 2.0
    cy = sol[1] / 2.0
    r = math.sqrt(max(sol[2] + cx * cx + cy * cy, 0.0))
    if not math.isfinite(r) or r <= 0 or r > 5000:
        return None
    rad = np.hypot(x - cx, y - cy)
    err = float(np.abs(rad - r).max())
    return dict(type="circle", err=err, centre=(cx, cy), radius=r)


def fit_arc(pts):
    """A curve is a line if the circle fit is poor, otherwise an arc."""
    c = fit_circle(pts)
    l = fit_line(pts)
    if c and c["err"] < 1.6:
        # keep only the points within tolerance and refit
        for _ in range(3):
            x = pts[:, 0]
            y = pts[:, 1]
            rad = np.hypot(x - c["centre"][0], y - c["centre"][1])
            keep = np.abs(rad - c["radius"]) < 1.4
            if keep.sum() < 8:
                break
            c2 = fit_circle(pts[keep])
            if not c2:
                break
            c = c2
        x = pts[:, 0]
        y = pts[:, 1]
        a0 = math.degrees(math.atan2(y[0] - c["centre"][1], x[0] - c["centre"][0]))
        a1 = math.degrees(math.atan2(y[-1] - c["centre"][1], x[-1] - c["centre"][0]))
        c["a0"], c["a1"] = a0, a1
        c["sweep"] = (a1 - a0) % 360.0
        c["arc_len"] = math.radians(c["sweep"]) * c["radius"]
        return c
    if l and l["err"] < 1.6:
        l["arc_len"] = l["length"]
        return l
    return dict(type="free", err=min(c["err"] if c else 99, l["err"]),
                arc_len=float(np.hypot(pts[-1, 0] - pts[0, 0],
                                       pts[-1, 1] - pts[0, 1])))


# --------------------------------------------------------------------------- #
def neighbour_map(sk):
    nbrs = {}
    H, W = sk.shape
    ys, xs = np.nonzero(sk)
    for y, x in zip(ys, xs):
        lst = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and sk[yy, xx]:
                    lst.append((yy, xx))
        nbrs[(y, x)] = lst
    return nbrs


def prune_spurs(sk, max_len=14):
    """Iteratively delete short terminal branches of the skeleton."""
    sk = sk.copy()
    for _ in range(80):
        nbrs = neighbour_map(sk)
        deg = {p: len(l) for p, l in nbrs.items()}
        removed = False
        for e in [p for p in nbrs if deg[p] == 1]:
            path = [e]
            cur, prev = e, None
            while True:
                nxt = [q for q in nbrs[cur] if q != prev]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                path.append(cur)
                if cur != e and deg[cur] != 2:
                    break
            if len(path) <= max_len and len(path) > 1 and cur != e:
                for p in path:
                    sk[p] = False
                removed = True
        if not removed:
            break
    return sk


def merge_chains(edges, tol=1.6):
    """Join chains that meet end-to-end into single curves."""
    edges = [list(e) for e in edges]
    changed = True
    while changed:
        changed = False
        ends = {}
        for i, e in enumerate(edges):
            ends.setdefault(e[0], set()).add(i)
            ends.setdefault(e[-1], set()).add(i)
        for pt, lst in ends.items():
            if len(lst) != 2:
                continue
            i, j = tuple(lst)
            if i == j:
                continue
            a, b = edges[i], edges[j]

            def far_end(ch):
                return ch[-1] if ch[0] == pt else ch[0]
            fa, fb = far_end(a), far_end(b)
            if abs(fa[0] - fb[0]) > tol or abs(fa[1] - fb[1]) > tol:
                continue
            merged = a + b[::-1] if a[-1] == pt else b + a[::-1]
            edges.pop(max(i, j))
            edges.pop(min(i, j))
            edges.append(merged)
            changed = True
            break
    return edges


def main():
    ink, shape = binarise(IMG)
    clean = strip_blobs(ink)
    sk = thin(clean)
    sk = prune_spurs(sk, 14)
    edges = trace_edges(sk)
    edges = merge_chains(edges)
    edges = [e for e in edges if len(e) >= 30]
    print("edges traced:", len(edges))

    prims = []
    for path in edges:
        pts = np.array([(p[1], p[0]) for p in path], float)   # (x, y)
        if len(pts) < 12:
            continue
        f = fit_arc(pts)
        f["npts"] = len(pts)
        f["p_start"] = tuple(pts[0])
        f["p_end"] = tuple(pts[-1])
        prims.append(f)

    prims.sort(key=lambda f: -f["npts"])
    print("\n%-6s %-7s %-8s %-42s %-24s" %
          ("type", "npts", "err", "geometry", "endpoints"))
    for f in prims:
        if f["type"] == "circle":
            g = "R=%.1f c=(%.1f,%.1f) sweep=%.0f" % (
                f["radius"], f["centre"][0], f["centre"][1], f["sweep"])
        elif f["type"] == "line":
            g = "n=(%.3f,%.3f) ang=%.1f len=%.1f" % (
                f["n"][0], f["n"][1], f["angle"], f["length"])
        else:
            g = "free-form"
        print("%-6s %-7d %-8.2f %-42s (%.0f,%.0f)-(%.0f,%.0f)" % (
            f["type"], f["npts"], f["err"], g,
            f["p_start"][0], f["p_start"][1], f["p_end"][0], f["p_end"][1]))

    # ------------------------------------------------------------------ #
    # SVG overlay of the fitted primitives
    # ------------------------------------------------------------------ #
    W, H = shape[1], shape[0]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d">' % (W, H, W, H),
             '<rect width="100%%" height="100%%" fill="white"/>']
    for f in prims:
        if f["type"] == "circle":
            cx, cy = f["centre"]
            r = f["radius"]
            a0 = math.radians(f["a0"])
            a1 = math.radians(f["a0"] + f["sweep"])
            x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
            x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
            large = 1 if f["sweep"] > 180 else 0
            parts.append('<path d="M %.1f %.1f A %.1f %.1f 0 %d 1 %.1f %.1f" '
                         'fill="none" stroke="red" stroke-width="1.2"/>'
                         % (x0, y0, r, r, large, x1, y1))
        elif f["type"] == "line":
            (px, py) = f["p0"]
            (nx, ny) = f["n"]
            L = max(f["length"], 1.0)
            parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                         'stroke="blue" stroke-width="1.2"/>'
                         % (px - nx * L / 2, py - ny * L / 2,
                            px + nx * L / 2, py + ny * L / 2))
    parts.append("</svg>")
    with open(OUT_SVG, "w") as fh:
        fh.write("\n".join(parts))
    print("\nSVG written:", OUT_SVG)

    # ------------------------------------------------------------------ #
    # PNG overlay: original drawing + fitted primitives in red
    # ------------------------------------------------------------------ #
    from PIL import Image, ImageDraw
    base = Image.open(IMG).convert("RGB")
    dr = ImageDraw.Draw(base)
    for f in prims:
        if f["type"] == "circle":
            cx, cy = f["centre"]
            r = f["radius"]
            a0 = math.radians(f["a0"])
            a1 = math.radians(f["a0"] + f["sweep"])
            n = max(int(abs(f["sweep"])) + 2, 8)
            pts = [(cx + r * math.cos(a0 + (a1 - a0) * i / n),
                    cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
            dr.line(pts, fill=(255, 0, 0), width=2)
        elif f["type"] == "line":
            (px, py) = f["p0"]
            (nx, ny) = f["n"]
            L = max(f["length"], 1.0)
            dr.line([(px - nx * L / 2, py - ny * L / 2),
                     (px + nx * L / 2, py + ny * L / 2)], fill=(0, 0, 255), width=2)
    base.save(OUT_PNG)
    print("PNG overlay written:", OUT_PNG)


if __name__ == "__main__":
    main()
