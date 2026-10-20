# -*- coding: utf-8 -*-
"""analyze_v8.py — read the top-centre structure of the sketch numerically."""
import numpy as np
from PIL import Image

g = np.array(Image.open("/workspace/src/drawings/Screenshot (2).png").convert("L"))
m = g < 200


def runs(idx):
    out = []
    if len(idx) == 0:
        return out
    s = p = idx[0]
    for v in idx[1:]:
        if v != p + 1:
            out.append((int(s), int(p)))
            s = v
        p = v
    out.append((int(s), int(p)))
    return out


X0, X1 = 300, 620
print("=== rows, x in [%d,%d] ===" % (X0, X1))
for y in range(105, 345, 5):
    r = [(a, b) for a, b in runs(np.nonzero(m[y, X0:X1])[0] + X0) if b - a >= 0]
    print("y=%3d: %s" % (y, " ".join("%d-%d" % t for t in r)))

print("\n=== columns, y in [100,345] ===")
for x in range(320, 600, 10):
    r = [(a, b) for a, b in runs(np.nonzero(m[100:345, x])[0] + 100)]
    print("x=%3d: %s" % (x, " ".join("%d-%d" % t for t in r)))
