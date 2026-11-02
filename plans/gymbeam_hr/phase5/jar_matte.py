"""Silhouette matte of an official Colla Pink packshot (white background) -> RGBA jar layer. Zero cost. Usage: jar_matte.py <packshot.png> <out.png>
The silver lid is nearly white, so a colour flood fill cannot separate it from the white backdrop. The jar is convex per row, so each row is the span between its
outermost jar pixels. Lid rows use 'differs from white', body rows use pink chroma (R-G > 12; this also excludes the neutral grey contact shadow), the base rows
add the dark base line. Edges between the lid and body rows are blended, body edges are median-smoothed, the span is anti-aliased (0.8 px). Nothing is repainted."""
import sys
from PIL import Image, ImageFilter
Y_LID, Y_BODY, Y_BASE0, BASE_Y = 290, 400, 990, 1058   # rows >= Y_BASE0 are bounded below by the dark base line (see yb)
im = Image.open(sys.argv[1]).convert("RGB"); W, H = im.size; px = im.load()


def span(y, mode):
    def ok(c):
        d = sum(255 - v for v in c)
        if mode == "lid":
            return d > 30
        return (c[0] - c[1] > 12 and d > 40) or (y >= Y_BASE0 and d > 300)
    xs = [x for x in range(W) if ok(px[x, y])]
    return (xs[0], xs[-1]) if len(xs) > 3 else None


L, R = {}, {}
for y in range(170, BASE_Y + 1):
    a, b = span(y, "lid"), span(y, "body")
    if y < Y_BODY and a:
        L[y], R[y] = a
    elif y >= Y_BODY and b:
        L[y], R[y] = b
for y in range(Y_LID + 1, Y_BODY):        # blend lid -> body edges
    t = (y - Y_LID) / (Y_BODY - Y_LID)
    if Y_LID in L and Y_BODY in L:
        L[y] = round(L[Y_LID] * (1 - t) + L[Y_BODY] * t); R[y] = round(R[Y_LID] * (1 - t) + R[Y_BODY] * t)
ys = sorted(L)
def smooth(E, y0, y1, k=4):
    for y in range(y0, y1):
        w = sorted(E[v] for v in range(y - k, y + k + 1) if v in E)
        E[y] = w[len(w) // 2]
sl, sr = dict(L), dict(R)
smooth(sl, Y_BODY, BASE_Y - 6); smooth(sr, Y_BODY, BASE_Y - 6)
# base: the bottom of the jar is a smooth curve whose edge is a dark line (the soft shadow below is lighter). yb(x) = lowest dark-line row per column.
yb = {}
for x in range(W):
    for y in range(1090, 1000, -1):
        if sum(255 - v for v in px[x, y]) > 200:
            yb[x] = y; break
m = Image.new("L", (W, H), 0); mp = m.load()
for y in ys:
    for x in range(sl[y], sr[y] + 1):
        if y >= Y_BASE0 and (x not in yb or y > yb[x]): continue
        mp[x, y] = 255
m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
out = im.convert("RGBA"); out.putalpha(m)
bbox = m.point(lambda v: 255 if v > 128 else 0).getbbox(); out = out.crop(bbox); out.save(sys.argv[2]); print("jar layer", out.size, "bbox in source", bbox)
