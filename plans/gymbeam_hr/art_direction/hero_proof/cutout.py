"""Pixel-accurate cut-out of the real pouch from the official GymBeam photograph (no painting, no generation).

Inside a 14 px ring around the pouch outline, background is found by flood fill over smoothly varying backdrop pixels; whatever the
fill cannot reach is pouch. The right edge is the pouch's straight vertical edge (the shaker touches it there, so colour cannot be
trusted); the foreground glass of the final scene covers that strip anyway. Run from the repository root.
"""
import hashlib
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "runs/hero-proof/source/creatine-monohydrate-unflavoured-lifestyle.png"
OUT = ROOT / "runs/hero-proof/pouch_layer_official_photo.png"
EXPECTED_SHA = "cc19b0cd800dc8bd2fba06eec193335192d1e3ac02b601dd24098628e92358e0"
L, T, R, B = 219, 121, 806, 1056   # measured outline (right edge = straight vertical seal edge)
RING = 14


def build():
    raw = SRC.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
        raise SystemExit("source photograph hash mismatch")
    im = Image.open(SRC).convert("RGB")
    px = im.load()
    W, H = im.size
    SHAKER_Y = 270                                          # below this row the shaker touches the right edge: no colour trust there
    outer = (L - RING, T - RING, R + RING, B)               # bottom: the pouch ends at B (below it is the reflection)
    bg = [[False] * W for _ in range(H)]
    q = deque()

    def inring(x, y):
        if not (outer[0] <= x < outer[2] and outer[1] <= y < outer[3]):
            return False
        if y >= SHAKER_Y and x >= R:
            return False
        return not (L + RING <= x < R - RING + 1 and T + RING <= y < B - RING)

    for y in range(outer[1], outer[3]):
        for x in range(outer[0], outer[2]):
            if inring(x, y) and (x in (outer[0], outer[2] - 1) or y == outer[1]) and not (y >= SHAKER_Y and x >= R - 1):
                bg[y][x] = True
                q.append((x, y))
    while q:
        x, y = q.popleft()
        a = px[x, y]
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if inring(nx, ny) and not bg[ny][nx]:
                b = px[nx, ny]
                if abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) <= 9:   # smooth backdrop only
                    bg[ny][nx] = True
                    q.append((nx, ny))
    m = Image.new("L", (W, H), 0)
    mp = m.load()
    for y in range(T - RING, B):
        for x in range(L - RING, R + RING):
            if not bg[y][x]:
                mp[x, y] = 255
    d = ImageDraw.Draw(m)
    d.rectangle((0, 0, W, T - RING - 1), fill=0)
    d.rectangle((0, 0, L - 6, H), fill=0)                    # left edge is straight to within 5 px: nothing beyond it is pouch
    d.rectangle((R, SHAKER_Y, W, H), fill=0)                 # straight right seal edge where the shaker touches it
    d.rectangle((R + RING, 0, W, H), fill=0)
    d.rectangle((0, B, W, H), fill=0)
    m = m.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(3))  # opening removes 1-2 px slivers; net 1 px erosion avoids a halo
    m = m.filter(ImageFilter.GaussianBlur(0.8))
    c = im.convert("RGBA")
    c.putalpha(m)
    box = m.point(lambda v: 255 if v > 128 else 0).getbbox()
    c = c.crop(box)
    c.save(OUT)
    return c, box


def inspect():
    c = Image.open(OUT)
    out = Image.new("RGB", (c.width * 2 + 30, c.height), (128, 128, 128))
    for i, bgc in enumerate(((235, 233, 230), (22, 20, 20))):
        t = Image.new("RGBA", c.size, bgc + (255,))
        t.alpha_composite(c)
        out.paste(t.convert("RGB"), (i * (c.width + 30), 0))
    p = OUT.with_name("cutout_inspection_light_dark.png")
    out.save(p)
    return p


if __name__ == "__main__":
    c, box = build()
    print("cutout", c.size, "box", box, "sha256", hashlib.sha256(OUT.read_bytes()).hexdigest())
    print(inspect())
