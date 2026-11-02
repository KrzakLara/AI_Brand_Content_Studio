"""Slide 6 final: approved design (Lara, 1092x1440) with the AI jar replaced by the REAL Strawberry Lemonade packshot. Zero cost: no network, no API.
Everything outside the jar region and the subtitle line is the approved image's pixels (scaled 0.989 and cropped to 1080x1350). Run from the repository root."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import importlib.util  # noqa: E402

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont  # noqa: E402

RUN = ROOT / "runs/colla-pink"
spec = importlib.util.spec_from_file_location("rt", Path(__file__).with_name("retouch_cover2.py"))
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)
rt.JAR = RUN / "jars/jar_strawberry.png"
SRC = RUN / "SLIDE6_APPROVED_PINK_FRUIT_DESIGN_1092x1440.png"
BURG = (112, 20, 50)
JAR_BOX = (350, 455, 781, 972)           # AI jar in the 1092x1440 design (measured by eye on the image)
CROP_TOP = 30                              # 1092x1440 -> 1080x1424 (uniform 0.989) -> crop 30 px top + 44 px bottom = 1350


def mont(size, weight):
    f = ImageFont.truetype(str(RUN / "font/Montserrat.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def erase_subtitle(im):
    """The old subtitle sits on a smooth pink gradient: each row is re-filled by interpolating between clean pixels left and right of it."""
    px = im.load()
    x0, x1, y0, y1 = 60, 750, 334, 388
    for x in range(x0, x1):                                   # per column: interpolate between clean rows above and below the text (the light streaks are diagonal)
        a, b = [tuple(sum(px[x + dx, yy][c] for dx in range(-3, 4)) // 7 for c in range(3)) for yy in (y0 - 8, y1 + 8)]
        for y in range(y0, y1):
            t = (y - y0) / (y1 - y0)
            px[x, y] = tuple(int(a[c] * (1 - t) + b[c] * t) for c in range(3))
    return im


def main():
    im = Image.open(SRC).convert("RGB")
    orig = im.copy()
    erase_subtitle(im)
    # ---- real jar: clean matte, scaled so that it covers the AI jar's height; centred on it
    j = rt.clean_jar()
    bx0, by0, bx1, by1 = JAR_BOX
    h = by1 - by0
    w = round(j.width * h / j.height)
    j = j.resize((w, h), Image.LANCZOS)
    x = (bx0 + bx1) // 2 - w // 2
    y = by0
    # luminance-only relight from the AI jar's own shading (measured where nothing is in front of it)
    reg = orig.crop((x, y, x + w, y + h)).convert("L")
    inner = j.getchannel("A").point(lambda v: 255 if v > 250 else 0).filter(ImageFilter.MinFilter(9))
    gl, gd = rt.nblur(reg, inner, 24); rl, rd = rt.nblur(j.convert("L"), inner, 24)
    jp = j.load()
    for yy in range(h):
        for xx in range(w):
            if jp[xx, yy][3] == 0 or gd[xx, yy] < 8 or rd[xx, yy] < 8:
                continue
            g = min(1.10, max(0.85, (gl[xx, yy] / gd[xx, yy]) / max(1e-3, rl[xx, yy] / rd[xx, yy])))
            r, gg, b, a = jp[xx, yy]
            jp[xx, yy] = (min(255, int(r * g)), min(255, int(gg * g)), min(255, int(b * g)), a)
    # base line trim (as for the cover) and soft contact shadow on the wet surface
    al = j.getchannel("A"); ap = al.load(); cols = {}
    for xx in range(w):
        for yy in range(h - 1, -1, -1):
            if ap[xx, yy] > 128:
                cols[xx] = yy; break
    for xx, yb in cols.items():
        for k in range(7):
            if yb - k >= 0:
                ap[xx, yb - k] = int(ap[xx, yb - k] * (0.0 if k < 4 else (k - 3) / 4))
    j.putalpha(al)
    foot = Image.new("L", im.size, 0); foot.paste(al, (x, y))
    # cover the AI jar completely first: fill its box with the surrounding backdrop colour sampled outside the jar is not possible (fruit around) -> the real jar (3% larger) covers it
    scale = 1.0
    base = im.convert("RGBA")
    shadow = foot.filter(ImageFilter.GaussianBlur(10)); shadow = ImageChops.offset(shadow, 0, 6)
    shade = ImageChops.invert(shadow.point(lambda v: int(v * 0.16)))
    base = ImageChops.multiply(base.convert("RGB"), Image.merge("RGB", (shade, shade, shade))).convert("RGBA")
    # the AI jar's pixels outside the real jar's silhouette (a few px at the sides) come from the original design
    base.alpha_composite(j, (x, y))
    # ---- objects that were IN FRONT of the AI jar are restored from the original: red strawberry flesh/skin, the two ice cubes, a drop; only inside the jar footprint
    o = orig.load(); fm = Image.new("L", im.size, 0); fp = fm.load()
    for yy in range(by0, by1 + 10):
        for xx in range(bx0 - 10, bx1 + 10):
            r, g, b = o[xx, yy]
            if r > 150 and g < 95 and b < 105 and xx < 412 and yy > 790:     # strawberry red (left-front, bottom)
                fp[xx, yy] = 255
    ice = Image.new("L", im.size, 0); idr = ImageDraw.Draw(ice)
    idr.polygon([(404, 925), (440, 920), (535, 930), (532, 985), (480, 1003), (412, 995), (404, 960)], fill=255)    # ice cube, front-left
    idr.polygon([(703, 902), (760, 880), (857, 905), (854, 975), (790, 995), (722, 990), (703, 940)], fill=255)      # ice cube, front-right
    cm = Image.new("L", im.size, 0); cm.paste(fm.crop((300, 780, 440, 1000)).filter(ImageFilter.MaxFilter(25)).filter(ImageFilter.MinFilter(25)), (300, 780))   # closing: fills the grey holes where the AI label showed through the berry
    cm = ImageChops.multiply(cm, Image.new("L", im.size, 0).point(lambda v: 0) if False else cm)
    stb = Image.new("L", im.size, 0); ImageDraw.Draw(stb).polygon([(190, 860), (215, 830), (300, 805), (370, 808), (410, 850), (412, 900), (385, 945), (320, 975), (250, 970), (205, 930)], fill=255)   # the cut strawberry half
    fm = ImageChops.lighter(ImageChops.multiply(cm, stb), ice).filter(ImageFilter.GaussianBlur(1.2))
    fm = ImageChops.multiply(fm, foot.filter(ImageFilter.MaxFilter(15)))
    out = Image.composite(orig.convert("RGBA"), base, fm)
    out = out.convert("RGB")
    # ---- new subtitle (the verified-equivalence rule): Montserrat, spaced capitals like the design
    d = ImageDraw.Draw(out)
    xx = 76
    for ch in "PET OKUSA. JEDAN RITUAL.":
        d.text((xx, 336), ch, font=mont(40, "Medium"), fill=BURG)
        xx += d.textlength(ch, font=mont(40, "Medium")) + 5
    out.save(RUN / "slide6_work_1092x1440.png")
    # ---- 1092x1440 -> 1080x1424 -> crop 30 top / 44 bottom -> 1080x1350
    full = out.resize((1080, 1424), Image.LANCZOS)
    final = full.crop((0, CROP_TOP, 1080, CROP_TOP + 1350))
    final.save(RUN / "carousel_final/slide6_odaberi_svoj_okus_FINAL.png")
    print("saved", final.size, "jar at", (x, y), (w, h))


if __name__ == "__main__":
    main()
