# -*- coding: utf-8 -*-
"""gridcrop.py — save a zoom crop with a labelled pixel grid (for reading
exact coordinates off the drawings)."""
import sys
import numpy as np
from PIL import Image, ImageDraw

def gridcrop(src, out, x0, y0, x1, y1, zoom=4, step=10, major=50):
    im = Image.open(src).convert("RGB").crop((x0, y0, x1, y1))
    w, h = im.size
    im = im.resize((int(w * zoom), int(h * zoom)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for gx in range(x0 - x0 % step, x1 + 1, step):
        X = (gx - x0) * zoom
        col = (255, 0, 0) if gx % major == 0 else (120, 200, 255)
        d.line([(X, 0), (X, im.height)], fill=col, width=1)
        if gx % major == 0:
            d.text((X + 2, 2), str(gx), fill=(200, 0, 0))
    for gy in range(y0 - y0 % step, y1 + 1, step):
        Y = (gy - y0) * zoom
        col = (255, 0, 0) if gy % major == 0 else (120, 200, 255)
        d.line([(0, Y), (im.width, Y)], fill=col, width=1)
        if gy % major == 0:
            d.text((2, Y + 2), str(gy), fill=(200, 0, 0))
    im.save(out)
    print("saved", out, im.size)

if __name__ == "__main__":
    S = "/workspace/src/drawings/Screenshot (2).png"
    P = "/workspace/src/drawings/Screenshot (3).png"
    O = "/workspace/FreeCAD_Models/out/"
    gridcrop(S, O + "g_2p24_left.png", 320, 100, 400, 140, zoom=8, step=10, major=50)
    gridcrop(S, O + "g_2p24_right.png", 530, 100, 610, 140, zoom=8, step=10, major=50)
    gridcrop(S, O + "g_1p94_top.png", 430, 130, 490, 200, zoom=8, step=10, major=50)
    gridcrop(S, O + "g_1p25_ur.png", 600, 170, 770, 290, zoom=4, step=10, major=50)
    gridcrop(S, O + "g_1p25_ll.png", 280, 370, 430, 500, zoom=4, step=10, major=50)
    gridcrop(S, O + "g_3p69.png", 230, 620, 690, 680, zoom=2, step=20, major=100)
    gridcrop(S, O + "g_topwin.png", 300, 100, 620, 260, zoom=3, step=20, major=100)
