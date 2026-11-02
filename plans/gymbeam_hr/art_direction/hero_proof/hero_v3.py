"""Hero v3: the glass rebuilt as an OBJECT (zero cost: no network, no API). Run from the repository root:  python plans/gymbeam_hr/art_direction/hero_proof/hero_v3.py

Diagnosis (see the report): v2 moved a rectangular block that began at the rim row. The rim is a thin arc (row ~676 at the left edge, ~665 at the right),
so its top pixels stayed at the old position (ghost arc / pale fragment above the moved rim), and the glass's left edge was a hard 1 px transition.
v3 builds a real glass mask: left edge (per row, refined) + top boundary (per column, the rim arc), a 4 px alpha ramp at the left edge, vacated old
pixels filled from the backdrop, and the same 30 px blend of the reflection rows. Everything else is v2 (matte pouch edge, source-derived seal repair).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
import importlib.util  # noqa: E402

from PIL import Image, ImageChops, ImageDraw, ImageFilter  # noqa: E402

spec = importlib.util.spec_from_file_location("hv", Path(__file__).with_name("hero_v2.py"))
hv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hv)
RUN, rf = hv.RUN, hv.rf
GW, GH = hv.GW, hv.GH
POUCH_BOTTOM = 1575   # below this row there is no pouch: glass base and reflection are handled as a block (as in v2)


def rim_top(gen, x0, x1=GW, y_lo=640, y_hi=700):
    """Per column: first row (from above) where the thin rim arc starts = a luminance step of > 18 within 6 rows; smoothed along x."""
    g = gen.convert("L").load()
    top = []
    for x in range(x0, x1):
        y_found = None
        for y in range(y_lo, y_hi):
            if abs(g[x, y + 3] - g[x, y - 3]) > 18:
                y_found = y
                break
        top.append(y_found if y_found is not None else y_hi)
    n = len(top)
    return [sorted(top[max(0, i - 20):i + 21])[len(top[max(0, i - 20):i + 21]) // 2] for i in range(n)]


def glass_object_mask(gen, edge, ramp=4):
    """Glass = right of its left edge and below the rim arc. Left edge gets a `ramp`-px alpha ramp (the glass wall is thin and transparent there)."""
    x0 = min(edge) - 2
    top = rim_top(gen, x0)
    # columns over the busy pouch seal / wordmark (x < 1255) are not reliable: the arc meets the glass wall at row ~676 (measured on the raw
    # image) and rises to the reliable part of the arc, so interpolate linearly between those two values
    g = gen.convert("L").load()
    for x in range(1255, 1336):                       # over the pouch seal: the rim highlight is the brightest row of the arc, whatever the dot pattern does
        peak = max(range(658, 690), key=lambda y: g[x, y])
        top[x - x0] = peak - 2
    top[1255 - x0:1336 - x0] = [sorted(top[max(1255 - x0, i - 7):i + 8])[len(top[max(1255 - x0, i - 7):i + 8]) // 2] for i in range(1255 - x0, 1336 - x0)]
    # beyond the pouch the arc is almost a straight line: replace the stair-stepped per-column values by a least-squares line (no stair artefacts)
    xs = [x for x in range(1340, GW)]
    for x in xs:                                      # same definition as over the pouch: the bright rim highlight row (the faint upper line is left in place)
        top[x - x0] = max(range(655, 690), key=lambda y: g[x, y]) - 2
    ys = [top[x - x0] for x in xs]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    k = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    for x in xs:
        top[x - x0] = round(my + k * (x - mx))
    xr = 1255 - x0
    for i in range(0, xr):
        top[i] = round(676 + (top[xr] - 676) * i / xr)
    m = Image.new("L", (GW, GH), 0)
    px = m.load()
    y_edge0 = rf.RIM
    for i, y in enumerate(range(y_edge0, 1640)):
        e = edge[i] + 1
        for k in range(ramp):
            xk = e + k
            a = int(255 * (k + 1) / (ramp + 1))
            for x in range(xk, xk + 1):
                px[x, y] = a
        for x in range(e + ramp, GW):
            px[x, y] = 255
    # cut everything above the rim arc (per column); the rim arc itself is part of the glass
    for ix, x in enumerate(range(x0, GW)):
        margin = 1
        for y in range(y_edge0 - 40, top[ix] - margin):
            if 0 <= y < GH:
                px[x, y] = 0
    # rows between the rim arc top and y_edge0 belong to the glass too (left of the block start the arc rises above row 668)
    for ix, x in enumerate(range(x0, GW)):
        margin = 1
        for y in range(max(0, top[ix] - margin), y_edge0):
            e = edge[0] + 1
            px[x, y] = 255 if x >= e + ramp else (int(255 * (x - e + 1) / (ramp + 1)) if x >= e else 0)
    return m, top


def glass_fn(gen, edge, dx):
    X0 = 1215
    old, top = glass_object_mask(gen, edge)
    new = Image.new("L", (GW, GH), 0)
    new.paste(old.crop((0, 0, GW - dx, GH)), (dx, 0))
    # --- rows above the pouch bottom: move only glass pixels; vacated pixels (old glass, no longer glass) come from the backdrop just above the rim
    shifted = ImageChops.offset(gen, dx, 0)
    plate = Image.composite(shifted, gen, new)
    vacated = ImageChops.subtract(old, new)
    above = ImageChops.offset(gen, 0, -18)                                   # backdrop / pouch pixels 18 rows higher (dark backdrop outside the pouch)
    plate = Image.composite(above, plate, vacated.point(lambda v: 255 if v > 8 else 0))
    # --- rows from the pouch bottom down (glass base + reflection): block move with a 30 px blend, as in v2
    Y0 = POUCH_BOTTOM
    mir = gen.copy()
    mir.paste(gen.crop((X0 - (dx + 30), Y0, X0, GH)).transpose(Image.FLIP_LEFT_RIGHT), (X0, Y0))
    sh = mir.copy()
    sh.paste(gen.crop((X0, Y0, GW - dx, GH)), (X0 + dx, Y0))
    ramp = Image.new("L", (GW, GH), 0)
    rd = ImageDraw.Draw(ramp)
    for i in range(30):
        rd.line((X0 + dx + i, Y0, X0 + dx + i, GH), fill=int(255 * (i + 1) / 30))
    rd.rectangle((X0 + dx + 30, Y0, GW, GH), fill=255)
    lower = Image.composite(sh, mir, ramp)
    plate.paste(lower.crop((0, Y0, GW, GH)), (0, Y0))
    return plate, new


def main():
    _, _, hv.layer_org = hv.source_layer()
    comp, info = hv.build(50, "", glass_fn=glass_fn)
    out = hv.headline(comp.copy())
    out.save(RUN / "hero_v3_corrected_1080x1350.png")
    comp.save(RUN / "hero_v3_nolettering_1080x1350.png")
    print("saved", out.size)


if __name__ == "__main__":
    main()
