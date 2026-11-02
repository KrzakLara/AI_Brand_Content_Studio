"""Storyboard contact sheet for the Phase 3 art-direction revision. PREVIEW MOCKUPS ONLY.

Everything here is drawn locally with Pillow (gradients, noise, blur, simple shapes) around the REAL pouch pixels of the selected packshot (unaltered,
scaled down only). Nothing is a generated or photographed image and nothing is final. No network, no API. Run from the repository root:
    .venv/Scripts/python plans/gymbeam_hr/art_direction/make_contact_sheet.py
"""
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "runs/research-gymbeam-hr-live/research/raw/99543edff63b17e3.jpg"  # selected original packshot (sha256 99543edf...)
OUT = Path(__file__).with_name("storyboard_contact_sheet.png")
random.seed(7)

INK, GRAPHITE, BONE, DUST, ORANGE = (15, 13, 13), (45, 42, 43), (242, 237, 232), (114, 108, 107), (255, 140, 50)  # the research palette only
FONTS = Path("C:/Windows/Fonts")


def font(size, bold=False):
    for n in (("segoeuib.ttf" if bold else "segoeui.ttf"), ("arialbd.ttf" if bold else "arial.ttf")):
        try:
            return ImageFont.truetype(str(FONTS / n), size)
        except OSError:
            pass
    return ImageFont.load_default()


# ---------------------------------------------------------------- the real pouch (no badges, right edge cut where the badges start)
def pouch_cutout():
    a = Image.open(SRC).convert("RGB")
    reg = a.crop((262, 88, 770, 1000))
    work = reg.copy()
    for pt in ((0, 0), (reg.width - 1, 0), (0, reg.height - 1), (reg.width - 1, reg.height - 1)):
        ImageDraw.floodfill(work, pt, (255, 0, 255), thresh=14)
    alpha = ImageChops.difference(work.convert("RGB"), Image.new("RGB", work.size, (255, 0, 255))).convert("L").point(lambda v: 255 if v > 20 else 0)
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.7))
    reg.putalpha(alpha)
    return reg.crop(reg.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox())


POUCH = pouch_cutout()  # about 493 x 897 px, 1:1 with the source


def pouch_at(height, edge_shadow=True):
    p = POUCH.resize((round(POUCH.width * height / POUCH.height), height), Image.LANCZOS)
    if edge_shadow:  # low-key fall-off over the right ~14%: where the webshop badges hid the real edge
        w, h = p.size
        ramp = Image.linear_gradient("L").rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT).resize((w, h))  # 0 at left .. 255 at right
        ramp = ramp.point(lambda v: 0 if v < 190 else int((v - 190) / 65 * 215))
        dark = Image.new("RGB", (w, h), INK)
        base = p.convert("RGB")
        base = Image.composite(dark, base, ramp)
        p = Image.merge("RGBA", (*base.split(), p.getchannel("A")))
    return p


# ---------------------------------------------------------------- scene helpers
def vgrad(size, top, bottom):
    g = Image.linear_gradient("L").resize(size)
    return Image.composite(Image.new("RGB", size, bottom), Image.new("RGB", size, top), g)


def glow(img, center, radius, color, strength=0.55):
    m = Image.radial_gradient("L").resize((radius * 2, radius * 2)).point(lambda v: max(0, int((255 - v) * strength)))
    layer = Image.new("RGB", (radius * 2, radius * 2), color)
    img.paste(layer, (center[0] - radius, center[1] - radius), m)


def grain(img, amount=10):
    n = Image.effect_noise(img.size, 40).convert("RGB")
    return Image.blend(img, ImageChops.add(img, n, 1.0, -128), amount / 100)


def concrete(size, base=GRAPHITE, amount=26):
    img = Image.new("RGB", size, base)
    return grain(img.filter(ImageFilter.GaussianBlur(0.5)), amount)


def put_pouch(scene, height, cx, base_y, shadow=True):
    p = pouch_at(height)
    if shadow:
        sh = Image.new("L", scene.size, 0)
        d = ImageDraw.Draw(sh)
        d.ellipse((cx - p.width * 0.55, base_y - 16, cx + p.width * 0.55, base_y + 22), fill=200)
        sh = sh.filter(ImageFilter.GaussianBlur(14))
        scene.paste(Image.new("RGB", scene.size, (5, 4, 4)), (0, 0), sh)
    scene.paste(p, (cx - p.width // 2, base_y - p.height), p)


def text(d, xy, s, size, fill=BONE, bold=True, anchor="la"):
    d.text(xy, s, font=font(size, bold), fill=fill, anchor=anchor)


def logo_slot(d, x, y, w=150, h=34, scale=1):
    d.rectangle((x, y, x + w * scale, y + h * scale), outline=DUST, width=max(1, round(scale)))
    text(d, (x + w * scale // 2, y + h * scale // 2), "LOGO ASSET", int(13 * scale), DUST, False, "mm")


def tag(img, label, color=ORANGE):
    d = ImageDraw.Draw(img)
    f = font(max(11, img.width // 34), True)
    w = d.textlength(label, font=f) + 14
    d.rectangle((0, 0, w, f.size + 10), fill=color)
    d.text((7, 5), label, font=f, fill=INK)
    return img


# ---------------------------------------------------------------- the nine scenes (drawn at 1080 wide / 4:5 unless noted)
def studio_base(w=1080, h=1350, horizon=0.78):
    s = vgrad((w, h), (30, 25, 23), INK)
    glow(s, (int(w * .2), int(h * .22)), int(w * .8), (110, 62, 28), .5)
    glow(s, (int(w * .12), int(h * .5)), int(w * .35), ORANGE, .22)
    y = int(h * horizon)
    c = concrete((w, h - y), (52, 47, 45), 30)
    shade = vgrad((w, h - y), (95, 70, 50), INK)
    c = Image.blend(c, shade, .55)
    s.paste(c, (0, y))
    ImageDraw.Draw(s).line((0, y, w, y), fill=(120, 78, 44), width=2)
    return grain(s, 8), y


def hero():
    s, y = studio_base()
    put_pouch(s, 780, 700, y + 60)
    d = ImageDraw.Draw(s)
    text(d, (90, 110), "Samo", 118, BONE)
    text(d, (90, 232), "bitno.", 118, BONE)
    d.rectangle((92, 372, 92 + 300, 380), fill=ORANGE)
    logo_slot(d, 90, 1190, scale=1.6)
    return s


def car1():
    s, y = studio_base(horizon=.74)
    put_pouch(s, 680, 690, y + 60)
    d = ImageDraw.Draw(s)
    for _ in range(46):  # a few grains of powder as texture
        x, yy = random.randint(250, 520), random.randint(y + 20, y + 300)
        r = random.choice((2, 3, 3, 4))
        d.ellipse((x, yy, x + r, yy + r), fill=(232, 228, 222))
    text(d, (80, 100), "Kreatin", 104, BONE)
    text(d, (80, 214), "izbliza.", 104, BONE)
    d.rectangle((82, 352, 360, 358), fill=ORANGE)
    logo_slot(d, 80, 1210, scale=1.4)
    return s


def car2():  # video: powder falling into a glass, shallow depth
    s = vgrad((1080, 1350), (28, 22, 20), INK)
    glow(s, (260, 300), 640, (125, 70, 30), .55)
    glow(s, (900, 700), 300, ORANGE, .25)
    d = ImageDraw.Draw(s)
    d.polygon([(540, 880), (860, 880), (836, 1230), (564, 1230)], fill=(60, 56, 56), outline=(150, 140, 130))
    d.rectangle((566, 1150, 834, 1226), fill=(205, 198, 188))  # powder heap
    layer = Image.new("RGB", s.size, (0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i in range(1800):  # falling stream, curved
        t = random.random()
        x = 250 + 330 * t + random.gauss(0, 10 + 24 * t)
        yy = 220 + 960 * t + random.gauss(0, 6)
        r = random.choice((1, 2, 2, 3))
        c = random.randint(200, 250)
        ld.ellipse((x, yy, x + r, yy + r), fill=(c, c - 4, c - 10))
    layer = Image.blend(layer, layer.filter(ImageFilter.GaussianBlur(3)), .5)
    s = ImageChops.add(s, layer)
    d = ImageDraw.Draw(s)
    d.polygon([(110, 160), (330, 150), (420, 250), (210, 300)], fill=(34, 30, 30))  # dark scoop blade
    text(d, (80, 1240), "Prah u pokretu.", 78, BONE)
    d.rectangle((82, 1330 - 40, 330, 1330 - 34), fill=ORANGE)
    return grain(s, 9)


def car3():  # photo: lifestyle (illustrative placeholder)
    s = vgrad((1080, 1350), (118, 92, 70), (36, 28, 24))
    glow(s, (80, 220), 700, (255, 204, 150), .7)
    d = ImageDraw.Draw(s)
    d.rectangle((0, 900, 1080, 1350), fill=(70, 50, 36))  # bench top
    d.rectangle((0, 900, 1080, 912), fill=(150, 112, 80))
    d.rounded_rectangle((70, 800, 300, 930), 24, fill=(205, 196, 184))  # towel
    for k in range(4):
        d.line((70, 830 + k * 24, 300, 830 + k * 24), fill=(180, 170, 158), width=2)
    for cx in (900, 1010):  # weights, soft
        d.ellipse((cx - 90, 560, cx + 90, 740), fill=(40, 38, 38))
    s = s.filter(ImageFilter.GaussianBlur(1))
    lay = Image.new("RGBA", s.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle((470, 520, 650, 900), 50, fill=(235, 238, 240, 90), outline=(255, 255, 255, 170), width=4)  # clear shaker
    ld.rounded_rectangle((455, 470, 665, 530), 24, fill=(30, 30, 30, 235))  # lid
    ld.rounded_rectangle((300, 640, 480, 760), 50, fill=(150, 112, 90, 255))  # hands: faceless, no detail
    ld.rounded_rectangle((640, 640, 820, 760), 50, fill=(140, 104, 84, 255))
    ld.ellipse((505, 760, 615, 860), fill=(255, 255, 255, 60))
    s = Image.alpha_composite(s.convert("RGBA"), lay).convert("RGB")
    d = ImageDraw.Draw(s)
    text(d, (80, 100), "Prije", 104, BONE)
    text(d, (80, 214), "treninga.", 104, BONE)
    d.rectangle((82, 350, 300, 356), fill=ORANGE)
    return grain(s, 9)


def car4():  # video: water + swirl
    s = vgrad((1080, 1350), (24, 20, 19), INK)
    glow(s, (180, 280), 560, (130, 74, 32), .5)
    d = ImageDraw.Draw(s)
    gl = Image.new("RGBA", s.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    gd.polygon([(330, 420), (750, 420), (710, 1160), (370, 1160)], fill=(200, 215, 220, 55), outline=(240, 245, 250, 150))
    for i in range(2400):  # cloudy swirl
        t = random.random() * 6.28 * 2.2
        rr = 40 + t * 12
        x = 540 + rr * 0.9 * __import__("math").cos(t) * 0.8 + random.gauss(0, 14)
        y = 740 + 110 * __import__("math").sin(t) * 1.5 + t * 14 + random.gauss(0, 14)
        c = random.randint(205, 245)
        gd.ellipse((x, y, x + 3, y + 3), fill=(c, c - 2, c - 8, 150))
    gl = gl.filter(ImageFilter.GaussianBlur(2))
    s = Image.alpha_composite(s.convert("RGBA"), gl).convert("RGB")
    d = ImageDraw.Draw(s)
    text(d, (80, 120), "Voda", 100, BONE)
    text(d, (80, 232), "i prah.", 100, BONE)
    d.rectangle((82, 368, 300, 374), fill=ORANGE)
    return grain(s, 9)


def car5():  # photo: the two label crops at 1:1 + code-set typography
    s = concrete((1080, 1350), (40, 37, 38), 34)
    glow(s, (200, 200), 700, (120, 70, 32), .35)
    a = Image.open(SRC).convert("RGB")
    c1, c2 = a.crop((270, 380, 762, 500)), a.crop((270, 500, 762, 605))  # label_name, label_purity: 492 px wide, shown at 1.0x
    d = ImageDraw.Draw(s)
    text(d, (80, 90), "Što piše", 96, BONE)
    text(d, (80, 198), "na pakiranju", 96, BONE)
    x, y1 = 80, 420
    for im, y in ((c1, y1), (c2, y1 + 120 + 70)):
        s.paste(im, (x, y))
        d.rectangle((x - 5, y - 5, x + im.width + 4, y + im.height + 4), outline=ORANGE, width=3)
    text(d, (x, y1 + 128), "izvorna veličina, 1:1", 20, DUST, False)
    text(d, (640, y1 - 6), "Na pakiranju piše:", 30, DUST, False)
    text(d, (640, y1 + 34), "Creatine", 58, BONE)
    text(d, (640, y1 + 98), "Monohydrate", 58, BONE)
    text(d, (640, y1 + 232), "Na pakiranju piše:", 30, DUST, False)
    text(d, (640, y1 + 272), "100% Pure", 58, BONE)
    text(d, (640, y1 + 336), "micronised,", 58, BONE)
    text(d, (640, y1 + 400), "Unflavoured", 58, BONE)
    logo_slot(d, 80, 1210, scale=1.4)
    return grain(s, 6)


def car6():
    s, y = studio_base(horizon=.76)
    d = ImageDraw.Draw(s)
    d.rounded_rectangle((560, y - 60, 1010, y + 120), 40, fill=(196, 186, 172))  # folded towel, soft
    d.rounded_rectangle((560, y - 60, 1010, y - 30), 30, fill=(214, 204, 190))
    s = s.filter(ImageFilter.GaussianBlur(1.2))
    gl = Image.new("RGBA", s.size, (0, 0, 0, 0))
    ImageDraw.Draw(gl).polygon([(790, y - 420), (940, y - 420), (924, y - 60), (806, y - 60)], fill=(210, 222, 228, 40), outline=(240, 245, 250, 90))
    s = Image.alpha_composite(s.convert("RGBA"), gl.filter(ImageFilter.GaussianBlur(6))).convert("RGB")
    put_pouch(s, 700, 380, y + 70)
    d = ImageDraw.Draw(s)
    text(d, (80, 100), "Pogledajte", 100, BONE)
    text(d, (80, 212), "izbliza.", 100, BONE)
    d.rectangle((82, 350, 330, 356), fill=ORANGE)
    text(d, (80, 1170), "Više na linku u opisu profila.", 40, BONE, False)
    logo_slot(d, 80, 1235, scale=1.4)
    return s


# ---------------------------------------------------------------- reel (9:16 = 1080 x 1920)
R = (1080, 1920)


def r1():  # hands closing a bag zip
    s = vgrad(R, (22, 20, 20), INK)
    glow(s, (950, 400), 700, (190, 110, 50), .6)
    d = ImageDraw.Draw(s)
    d.rounded_rectangle((60, 820, 1020, 1500), 60, fill=(20, 19, 20), outline=(60, 54, 50), width=4)
    d.line((140, 1150, 960, 1130), fill=(120, 112, 105), width=10)
    d.rounded_rectangle((500, 1040, 700, 1230), 60, fill=(150, 112, 90))  # one hand, faceless
    d.rounded_rectangle((690, 1075, 880, 1190), 50, fill=(135, 100, 82))
    return grain(s.filter(ImageFilter.GaussianBlur(1.5)), 10)


def r2():  # silhouette behind frosted glass
    s = vgrad(R, (30, 26, 24), INK)
    d = ImageDraw.Draw(s)
    d.rectangle((250, 330, 830, 1500), fill=(222, 196, 160))
    glow(s, (540, 900), 520, (255, 220, 170), .6)
    d = ImageDraw.Draw(s)
    d.ellipse((490, 640, 590, 750), fill=(42, 34, 30))
    d.rounded_rectangle((440, 750, 640, 1180), 60, fill=(42, 34, 30))
    s = s.filter(ImageFilter.GaussianBlur(10))
    return grain(s, 12)


def r3():  # shoelace macro
    s = vgrad(R, (50, 44, 42), INK)
    glow(s, (250, 600), 600, (200, 120, 60), .5)
    d = ImageDraw.Draw(s)
    d.polygon([(100, 1300), (980, 1180), (1040, 1700), (60, 1760)], fill=(26, 24, 24))
    for i, y in enumerate(range(1230, 1620, 78)):
        d.line((300, y, 800, y - 30), fill=(210, 204, 196), width=16)
    d.rounded_rectangle((480, 1000, 600, 1560), 40, fill=(222, 214, 205))
    return grain(s.filter(ImageFilter.GaussianBlur(2.5)), 10)


def r4():  # reveal: orange light sweeps the shelf and reveals the pouch
    s = vgrad(R, (20, 18, 18), INK)
    d = ImageDraw.Draw(s)
    d.rectangle((0, 1380, 1080, 1920), fill=(48, 44, 44))
    d.line((0, 1380, 1080, 1380), fill=(130, 84, 46), width=3)
    glow(s, (300, 960), 600, ORANGE, .5)
    put_pouch(s, 860, 580, 1440)
    d = ImageDraw.Draw(s)
    text(d, (80, 160), "Sve je na", 74, BONE)
    text(d, (80, 250), "svom mjestu.", 74, BONE)
    return grain(s, 7)


def r5():  # slow close-up, never beyond 1:1 of the source
    s = vgrad(R, (34, 28, 26), INK)
    glow(s, (250, 520), 800, (140, 80, 34), .5)
    c = concrete((1080, 560), (50, 46, 44), 30)
    s.paste(c, (0, 1360))
    p = pouch_at(897)  # 1.0x of the source: the ceiling
    s.paste(p, (540 - p.width // 2, 1420 - p.height), p)
    return grain(s, 7)


def r6():
    s = vgrad(R, (26, 22, 21), INK)
    glow(s, (260, 500), 800, (120, 66, 28), .4)
    put_pouch(s, 800, 540, 1760)
    d = ImageDraw.Draw(s)
    logo_slot(d, 400, 330, 280, 64, 1)
    d.rectangle((420, 460, 660, 466), fill=ORANGE)
    text(d, (540, 560), "Spremno za izlazak.", 62, BONE, True, "mm")
    return grain(s, 7)


# ---------------------------------------------------------------- the fidelity panel
def fidelity_panel(w, h):
    a = Image.open(SRC).convert("RGB")
    sc = h / 1080
    im = a.resize((round(1080 * sc), h), Image.LANCZOS)
    pan = Image.new("RGB", (w, h), (24, 22, 22))
    pan.paste(im, (0, 0))
    ov = Image.new("RGBA", pan.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rectangle((765 * sc, 88 * sc, 818 * sc, 1000 * sc), fill=(255, 40, 40, 80), outline=(255, 70, 70, 255), width=3)
    od.rectangle((273 * sc, 96 * sc, 765 * sc, 994 * sc), outline=(80, 220, 120, 255), width=3)
    pan = Image.alpha_composite(pan.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(pan)
    x = im.width + 24
    lines = [("Product fidelity: what is safe", True, 26, BONE),
             ("GREEN: pouch pixels clean of badges (x 273-765).", False, 19, (110, 230, 140)),
             ("RED: ~45 px right edge hidden behind the 4", False, 19, (255, 110, 110)),
             ("webshop badges along most of its height.", False, 19, (255, 110, 110)),
             ("Not reconstructed: that would redraw the product.", False, 19, BONE),
             ("", False, 10, BONE),
             ("Plan: (1) ask GymBeam for a badge-free official", False, 19, BONE),
             ("packshot; (2) until then the right edge falls", False, 19, BONE),
             ("into low-key shadow or leaves the frame;", False, 19, BONE),
             ("(3) never scale above the source (~897 px).", False, 19, BONE),
             ("", False, 10, BONE),
             ("Both other pack images found are unusable:", False, 19, DUST),
             ("one has socks on the edge, one is the old design.", False, 19, DUST)]
    y = 40
    for t, b, sz, c in lines:
        text(d, (x, y), t, sz, c, b)
        y += sz + 11
    return pan


# ---------------------------------------------------------------- compose
def sized(img, w):
    return img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)


def main():
    W, M = 2400, 60
    sheet = Image.new("RGB", (W, 3270), (18, 16, 16))
    d = ImageDraw.Draw(sheet)
    text(d, (M, 36), "GymBeam Hrvatska  |  100% Creatine Monohydrate (SKU 3885)  |  Storyboard preview, Phase 3 art-direction revision", 40, BONE)
    d.rectangle((M, 98, W - M, 140), fill=ORANGE)
    text(d, (M + 14, 104), "PREVIEW MOCKUPS DRAWN LOCALLY - NOT generated photographs, NOT final art. The pouch pixels are the real packshot, scaled down, never altered. No API was called.", 25, INK)

    y = 180
    text(d, (M, y), "POST 01 (plan id 02)  PREMIUM PRODUCT HERO   1080x1350 photograph  |  'Samo bitno.'", 34, ORANGE)
    hp = sized(hero(), 700)
    sheet.paste(tag(hp, "PREVIEW MOCKUP"), (M, y + 56))
    fp = fidelity_panel(W - M * 2 - 700 - 40, 700 * 1350 // 1080)
    sheet.paste(fp, (M + 740, y + 56))
    notes_y = y + 56 + hp.height + 14
    for i, t in enumerate(["Dark graphite studio, warm low key from the left, one narrow orange rim-light, honed concrete with a real contact shadow.",
                           "Typography and logo are placed by code; the logo is the official asset only (slot shown, asset still pending retrieval)."]):
        text(d, (M, notes_y + i * 30), t, 21, DUST, False)

    y = notes_y + 100
    text(d, (M, y), "POST 02 (plan id 01)  MIXED-MEDIA CAROUSEL 'Kreatin izbliza'   4 photographs + 2 videos (3-4 s)", 34, ORANGE)
    cw = (W - M * 2 - 5 * 24) // 6
    labels = [("1  FOTO", "Opening: real pack + concrete texture", car1), ("2  VIDEO 3.5 s", "Powder in motion, no pack in shot", car2),
              ("3  FOTO", "Routine: faceless hands, plain shaker", car3), ("4  VIDEO 3.5 s", "Water + mixing, no solubility claim", car4),
              ("5  FOTO", "Verified label text, crops at 1:1", car5), ("6  FOTO", "Closing: pack, logo, CTA", car6)]
    for i, (lab, sub, fn) in enumerate(labels):
        x = M + i * (cw + 24)
        t = sized(fn(), cw)
        vid = "VIDEO" in lab
        sheet.paste(tag(t, "VIDEO PREVIEW" if vid else "PHOTO PREVIEW", (255, 205, 90) if vid else ORANGE), (x, y + 56))
        if vid:
            dd = ImageDraw.Draw(sheet)
            cx, cy = x + cw // 2, y + 56 + t.height // 2
            dd.ellipse((cx - 36, cy - 36, cx + 36, cy + 36), fill=(15, 13, 13), outline=BONE, width=3)
            dd.polygon([(cx - 10, cy - 16), (cx - 10, cy + 16), (cx + 18, cy)], fill=BONE)
        text(d, (x, y + 56 + t.height + 12), lab, 26, BONE)
        text(d, (x, y + 56 + t.height + 46), sub, 19, DUST, False)
    y2 = y + 56 + t.height + 100

    text(d, (M, y2), "POST 03  CINEMATIC REEL 'Klik prije izlaska'   14 s: 1.5 | 1.5 | 1.5 | 3 | 4 | 2.5   hard cuts on sound", 34, ORANGE)
    reel = [("1  1.5 s", "hands, zip: sharp zip sound", r1), ("2  1.5 s", "faceless silhouette, door handle", r2), ("3  1.5 s", "hands, shoelace macro", r3),
            ("4  3 s", "light sweep reveals the real pack", r4), ("5  4 s", "slow close-up, <= 1.0x source", r5), ("6  2.5 s", "logo + 'Spremno za izlazak.'", r6)]
    rw = (W - M * 2 - 5 * 24) // 6
    for i, (lab, sub, fn) in enumerate(reel):
        x = M + i * (rw + 24)
        t = sized(fn(), rw)
        sheet.paste(tag(t, "KEYFRAME PREVIEW"), (x, y2 + 56))
        text(d, (x, y2 + 56 + t.height + 12), lab, 26, BONE)
        text(d, (x, y2 + 56 + t.height + 46), sub, 19, DUST, False)
    yb = y2 + 56 + t.height + 100
    total = 14.0
    bx = M
    for i, dur in enumerate((1.5, 1.5, 1.5, 3, 4, 2.5)):
        wd = round((W - 2 * M) * dur / total)
        d.rectangle((bx, yb, bx + wd - 4, yb + 28), fill=ORANGE if i < 3 else (200, 110, 40))
        text(d, (bx + 10, yb + 2), f"{i + 1}", 20, INK)
        bx += wd
    text(d, (M, yb + 44), "Production path: photoreal keyframes -> human selection -> selective animation of the approved ones -> code typography and product compositing -> FFmpeg edit and QA.", 22, DUST, False)
    sheet = sheet.crop((0, 0, W, yb + 100))
    sheet.save(OUT, optimize=True)
    print("wrote", OUT, sheet.size)


if __name__ == "__main__":
    main()
