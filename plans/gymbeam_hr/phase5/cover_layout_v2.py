"""Zero-cost corrected cover LAYOUT for Phase 5 Slide 1 (no network, no API, no key). Run from the repository root.
It composes only: the measured campaign palette, real fonts, the REAL Strawberry Lemonade jar layer (scaled / rolled in the plane only) and clearly labelled flat
placeholders for the model pose and the GymBeam G logo. The placeholders are layout guides, NOT images of the model: the photograph is not generated yet.
Outputs in runs/colla-pink/layout_v2/: layout_A_hold_and_present.png, layout_B_hero_jar.png, compare_references_vs_failed_vs_proposed.png."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "runs/colla-pink"
REF = RUN / "instagram_pink/campaign_references"
OUT = RUN / "layout_v2"
OUT.mkdir(exist_ok=True)
W, H = 1080, 1350
PINK, PINK_LIGHT, BURG = (247, 180, 189), (250, 205, 211), (127, 41, 68)   # measured from the reference screenshots: #f7b4bd and #7f2944
SKIN, HAIR, WHITE, INK = (232, 176, 160), (66, 40, 30), (252, 248, 247), (30, 20, 24)


def mont(size, weight):
    f = ImageFont.truetype(str(RUN / "font/Montserrat.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def sans(size, bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf", size)


def background():
    g = Image.linear_gradient("L").rotate(45, expand=False).resize((W, H))
    return Image.composite(Image.new("RGB", (W, H), PINK), Image.new("RGB", (W, H), PINK_LIGHT), g)


def fit(draw, text, weight, width):
    lo, hi = 20, 400
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if draw.textlength(text, font=mont(mid, weight)) > width:
            hi = mid
        else:
            lo = mid
    return lo


def headline(im, light_lines):
    d = ImageDraw.Draw(im)
    size = fit(d, "VAŠ RUŽIČASTI", "ExtraBold", 930)
    f = mont(size, "ExtraBold")
    d.text((60, 52), "VAŠ RUŽIČASTI", font=f, fill=BURG)
    d.text((60, 52 + int(size * 1.12)), "RITUAL.", font=f, fill=BURG)
    fl = mont(42, "Medium")
    d.text((66, 52 + int(size * 1.12) * 2 + 8), " ".join(light_lines), font=fl, fill=BURG)   # subtitle directly under the headline, about 42 px: readable at feed size
    return size


def jar(width, roll=0):
    j = Image.open(RUN / "jar_strawberry_layer.png").convert("RGBA")
    j = j.resize((width, round(j.height * width / j.width)), Image.LANCZOS)
    return j.rotate(roll, resample=Image.BICUBIC, expand=True) if roll else j


def paste_with_shadow(im, j, xy, blur=18, off=(10, 16), alpha=70):
    sh = Image.new("RGBA", j.size, (110, 30, 55, 0))
    sh.putalpha(j.getchannel("A").point(lambda v: min(v, alpha)))
    big = Image.new("RGBA", (j.width + 80, j.height + 80), (0, 0, 0, 0))
    big.alpha_composite(sh, (40, 40))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    base = im.convert("RGBA")
    base.alpha_composite(big, (xy[0] - 40 + off[0], xy[1] - 40 + off[1]))
    base.alpha_composite(j, xy)
    return base.convert("RGB")


def tag(im, text, xy, color=(30, 20, 24)):
    d = ImageDraw.Draw(im)
    f = sans(17, True)
    w = d.textlength(text, font=f) + 14
    d.rectangle((xy[0], xy[1], xy[0] + w, xy[1] + 26), fill=(255, 255, 255))
    d.rectangle((xy[0], xy[1], xy[0] + w, xy[1] + 26), outline=color, width=2)
    d.text((xy[0] + 7, xy[1] + 2), text, font=f, fill=color)


def logo_placeholder(im, xy):
    d = ImageDraw.Draw(im)
    x, y = xy
    d.rounded_rectangle((x, y, x + 150, y + 90), 14, outline=(255, 255, 255), width=3)
    d.text((x + 18, y + 12), "GymBeam G", font=sans(22, True), fill=(255, 255, 255))
    d.text((x + 18, y + 44), "official logo\nasset pending", font=sans(15), fill=(255, 255, 255))


def model_placeholder_A(im):
    """Flat pose guide: 3/4 turned athletic stance, raised right hand (viewer's left) presenting the jar, left hand on hip, long hair down."""
    d = ImageDraw.Draw(im, "RGBA")
    d.polygon([(600, 450), (720, 440), (790, 560), (830, 820), (760, 900), (640, 880), (580, 700)], fill=HAIR + (255,))        # long hair behind the shoulders
    d.ellipse((560, 410, 740, 650), fill=SKIN + (255,))                                                                        # head
    d.polygon([(560, 470), (600, 400), (700, 395), (745, 450), (720, 470), (640, 430), (590, 480)], fill=HAIR + (255,))         # hair top
    d.polygon([(630, 640), (690, 640), (700, 700), (640, 700)], fill=SKIN + (255,))                                            # neck
    d.polygon([(500, 720), (830, 720), (860, 860), (800, 920), (530, 920), (470, 850)], fill=WHITE + (255,))                  # white sports bra
    d.polygon([(535, 920), (800, 920), (790, 1050), (545, 1050)], fill=SKIN + (255,))                                         # midriff
    d.polygon([(520, 1050), (810, 1050), (880, 1350), (440, 1350)], fill=WHITE + (255,))                                       # white high-waist leggings
    d.polygon([(500, 760), (445, 880), (430, 700), (470, 640), (520, 700)], fill=SKIN + (255,))                                # raised right arm (presenting)
    d.polygon([(830, 780), (905, 900), (860, 1040), (815, 1030), (840, 900)], fill=SKIN + (255,))                              # left arm, hand on hip
    d.text((520, 590), "FICTIONAL MODEL\n(pose guide, not an image)", font=sans(15, True), fill=(120, 40, 70))


def layout_A():
    im = background()
    size = headline(im, ["SVE ŠTO TREBA ZNATI", "U ŠEST KADROVA."])
    model_placeholder_A(im)
    j = jar(230, roll=10)                                                  # 21% of the frame width, in-plane roll 10 degrees (rigid rotation, no perspective warp)
    im = paste_with_shadow(im, j, (300, 560))
    logo_placeholder(im, (880, 1210))
    tag(im, "REAL JAR: 21% of width, roll 10 deg (hand grips the sides, fingers behind)", (40, 1290))
    tag(im, f"headline: Montserrat ExtraBold {size} px, 86% of width, burgundy #7f2944", (40, 1255))
    im.save(OUT / "layout_A_hold_and_present.png")
    return im


def layout_B():
    im = background()
    size = headline(im, ["SVE ŠTO TREBA ZNATI", "U ŠEST KADROVA."])
    d = ImageDraw.Draw(im, "RGBA")
    d.polygon([(640, 470), (760, 460), (830, 580), (860, 830), (790, 900), (660, 880), (610, 700)], fill=HAIR + (255,))
    d.ellipse((590, 430, 770, 670), fill=SKIN + (255,))
    d.polygon([(590, 490), (630, 420), (730, 415), (775, 470), (750, 490), (670, 450), (620, 500)], fill=HAIR + (255,))
    d.polygon([(660, 660), (720, 660), (730, 720), (670, 720)], fill=SKIN + (255,))
    d.polygon([(530, 740), (860, 740), (890, 880), (830, 940), (560, 940), (500, 870)], fill=WHITE + (255,))
    d.polygon([(565, 940), (830, 940), (820, 1060), (575, 1060)], fill=SKIN + (255,))
    d.polygon([(550, 1060), (840, 1060), (910, 1350), (470, 1350)], fill=WHITE + (255,))
    d.polygon([(860, 800), (935, 920), (890, 1060), (845, 1050), (870, 920)], fill=SKIN + (255,))
    d.text((545, 600), "FICTIONAL MODEL\n(pose guide, not an image)", font=sans(15, True), fill=(120, 40, 70))
    d.ellipse((60, 1120, 520, 1240), fill=(255, 235, 238, 255))               # blush plinth
    j = jar(330)                                                              # 31% of the frame width: nearer the camera than the model
    im = paste_with_shadow(im, j, (125, 780), alpha=90)
    logo_placeholder(im, (880, 1210))
    tag(im, "REAL JAR: 31% of width, upright on a plinth in front of the model (no hand contact)", (40, 1290))
    im.save(OUT / "layout_B_hero_jar.png")
    return im


def crop_ref(name, frame):
    return Image.open(REF / name).convert("RGB").crop(frame)


def compare(A, B):
    items = [("Reference 01 (@gymbeam, CreaGlow)", crop_ref("01_creaglow_cover_glow_inside_out.png", (148, 97, 841, 962))),
             ("Reference 03 (@gymbeam, CreaGlow)", crop_ref("03_creaglow_performance_beauty.png", (33, 45, 726, 910))),
             ("FAILED cover (rejected)", Image.open(RUN / "cover_slide1_1080x1350.png").convert("RGB")),
             ("Proposed layout A: hold and present", A), ("Proposed layout B: hero jar in front", B)]
    h = 760
    cells = []
    for t, im in items:
        cells.append((t, im.resize((round(im.width * h / im.height), h), Image.LANCZOS)))
    wsum = sum(c.width for _, c in cells) + 20 * (len(cells) + 1)
    sheet = Image.new("RGB", (wsum, h + 190), (24, 20, 22))
    d = ImageDraw.Draw(sheet)
    x = 20
    swatches = ["#f7b4bd", "#f7b7c0", "#eccfd1", "#f7b4bd", "#f7b4bd"]
    for (t, c), sw in zip(cells, swatches):
        sheet.paste(c, (x, 44))
        d.text((x, 12), t, font=sans(20, True), fill=(255, 190, 205))
        d.rectangle((x, h + 54, x + 48, h + 92), fill=sw)
        d.text((x + 58, h + 58), f"background {sw}", font=sans(18), fill=(240, 232, 234))
        x += c.width + 20
    d.text((20, h + 110), "Measured from pixels: references' background #f7b4bd / #f7b7c0 (HSL saturation 80-81%) vs the failed cover #eccfd1 (43%); references' burgundy #7f2944 vs our old #6e1f35.\n"
           "References: headline spans about 90% of the width and about a quarter of the height in giant bold sans caps; the failed cover's serif headline spans about 46% of the width.",
           font=sans(18), fill=(240, 232, 234), spacing=6)
    sheet.save(OUT / "compare_references_vs_failed_vs_proposed.png")
    print(sheet.size)


if __name__ == "__main__":
    A, B = layout_A(), layout_B()
    compare(A, B)
