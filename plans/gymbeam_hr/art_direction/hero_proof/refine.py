"""Zero-cost refinement of hero candidate A (no network, no API, no key). Run from the repository root:
    python plans/gymbeam_hr/art_direction/hero_proof/refine.py

 A: current glass     B: free experiment, glass moved right by DX generation pixels, reflection moved with it
Disclosure (also printed at the end):
 * the pouch is SOURCE-AUTHENTIC (the real photograph's pixels) but NOT pixel-identical: a smooth lighting gain (blur 24 px, clamped 0.75..1.05)
   and a whole-frame finishing grade change values; printed text, logo, badges and colours of the print are the real ones, never redrawn.
 * one small patch of the unprinted right seal (where the shaker handle touched the real photo) is the MODEL's plain seal texture.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont  # noqa: E402

RUN = ROOT / "runs/hero-proof"
spec = importlib.util.spec_from_file_location("mh", Path(__file__).with_name("make_hero.py"))
mh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mh)
FW, FH, GW, GH, PX, PY, PW, PH = mh.FW, mh.FH, mh.GW, mh.GH, mh.PX, mh.PY, mh.PW, mh.PH
PATCH_ZONE = (1262, 548, 1334, 646)   # handle patch: the unprinted right seal only (printed area ends at x~1260)
GLASS_ZONE = (1200, 650, 1340, 1580)  # glass in front of the pouch
DX, X0 = 50, 1215                     # glass shift (gen px = 34 final px); Y0 (= RIM) is defined below


def zone_mask(gen, ref, zone):
    mh.ZONES[:] = [zone]
    return mh.glass_mask(gen, ref)


RIM = 668   # first row of the glass (its rim), read from the raw candidate
Y0 = RIM


def glass_edge_mask(gen, ref, y1=1640, run=14, thr=28):
    """Glass = everything right of its left edge. Rows where the model's image differs from the reference for `run` consecutive pixels give edge
    samples; the plausible ones (1220..1275) are fitted with a straight line (least squares, one outlier pass), because on bright rows the
    difference test fails. The glass is a straight tumbler seen from the front, so a line is the honest model of its edge."""
    d = ImageChops.difference(gen.convert("RGB"), ref.convert("RGB")).convert("L").point(lambda v: 255 if v > thr else 0)
    px = d.load()
    pts = []
    for y in range(700, y1, 4):
        for x in range(1205, 1330):
            if all(px[x + i, y] for i in range(run)):
                if 1220 <= x <= 1275:
                    pts.append((y, x))
                break

    def fit(pp):
        n = len(pp); my = sum(p[0] for p in pp) / n; mx = sum(p[1] for p in pp) / n
        k = sum((y - my) * (x - mx) for y, x in pp) / sum((y - my) ** 2 for y, x in pp)
        return k, mx - k * my
    k, c = fit(pts)
    pts = [p for p in pts if abs(p[1] - (k * p[0] + c)) < 12]
    k, c = fit(pts)
    m = Image.new("L", (GW, GH), 0)
    dr = ImageDraw.Draw(m)
    edge = [round(k * y + c) for y in range(RIM, y1)]
    for i, y in enumerate(range(RIM, y1)):
        dr.line((edge[i], y, GW, y), fill=255)
    return m, edge


def lit_mean(img, w, r=24):
    """Normalised (masked) blur: mean colour of img around each pixel, using only pixels with weight w."""
    num = Image.composite(img, Image.new("RGB", img.size), w).filter(ImageFilter.GaussianBlur(r))
    den = w.filter(ImageFilter.GaussianBlur(r))
    return num.load(), den.load()


def relit_pouch(gen, glass_final, patch_final):
    cut = Image.open(RUN / "pouch_layer_official_photo.png").convert("RGBA").resize((PW, PH), Image.LANCZOS)
    real = cut.convert("RGB")
    alpha = cut.getchannel("A").filter(ImageFilter.MinFilter(3))                       # alpha-edge cleanup: 1 px in, no backdrop fringe
    gwin = gen.crop((PX, PY, PX + PW, PY + PH))
    keep = ImageChops.multiply(alpha, ImageChops.multiply(ImageChops.invert(glass_final.crop((PX, PY, PX + PW, PY + PH))),
                                                          ImageChops.invert(patch_final.crop((PX, PY, PX + PW, PY + PH)))))
    gn, gd = lit_mean(gwin, keep)
    rn, rd = lit_mean(real, keep)
    out, rp, gains = Image.new("RGB", real.size), real.load(), []
    op = out.load()
    for y in range(PH):
        for x in range(PW):
            gdv, rdv = gd[x, y], rd[x, y]
            if gdv < 8 or rdv < 8:
                op[x, y] = rp[x, y]
                continue
            g = [min(1.05, max(0.75, (gn[x, y][c] / gdv) / max(1e-3, rn[x, y][c] / rdv))) for c in range(3)]
            gains.append(sum(g) / 3)
            op[x, y] = tuple(min(255, int(rp[x, y][c] * g[c])) for c in range(3))
    out.putalpha(alpha.filter(ImageFilter.GaussianBlur(0.6)))
    return out, gains


def finish(im):
    """Whole-frame finishing grade (subtle): gentle contrast and a little crispness. Applies to scene and pouch alike."""
    im = ImageEnhance.Contrast(im).enhance(1.06)
    return im.filter(ImageFilter.UnsharpMask(radius=1.1, percent=55, threshold=2))


def typography(im, label):
    d = ImageDraw.Draw(im, "RGBA")
    f = ImageFont.truetype(str(RUN / "font/extras/ttf/Inter-Medium.ttf"), 40)
    for y, t in ((112, "SVAKA SERIJA"), (166, "POČINJE ODLUKOM.")):
        x = 92
        for ch in t:
            d.text((x, y), ch, font=f, fill=(242, 237, 232, 255))
            x += d.textlength(ch, font=f) + 7
    d.rectangle((94, 228, 178, 231), fill=(255, 140, 50, 255))
    fb = ImageFont.truetype(str(RUN / "font/extras/ttf/Inter-Bold.ttf"), 21)
    d.rectangle((0, FH - 44, FW, FH), fill=(255, 140, 50, 255))
    d.text((18, FH - 36), label, font=fb, fill=(15, 13, 13, 255))
    return im


def build(plate_gen, gen_for_light, glass_gen, patch_gen, label):
    base = plate_gen.resize((FW, FH), Image.LANCZOS)
    glass_f = glass_gen.resize((FW, FH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.0))
    patch_f = patch_gen.resize((FW, FH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.0))
    pouch, gains = relit_pouch(gen_for_light.resize((FW, FH), Image.LANCZOS), glass_f, patch_f)
    alpha_real = pouch.getchannel("A")
    box = (PX, PY, PX + PW, PY + PH)
    seal = base.crop(box).convert("RGB")                                        # the model's plain seal (its pouch edge sits ~5 px inside the real one:
    shifted = ImageChops.offset(seal, 5, 0)                                       # dark edge pixels are replaced by the seal colour 5 px to the left)
    seal = Image.composite(shifted, seal, seal.convert("L").point(lambda v: 255 if v < 80 else 0))
    pouch_rgb = Image.composite(seal, pouch.convert("RGB"), patch_f.crop(box))    # patch: the model's seal colour, inside the REAL silhouette
    pouch = pouch_rgb.convert("RGBA")
    pouch.putalpha(ImageChops.multiply(alpha_real, ImageChops.invert(glass_f.crop(box))))
    comp = base.convert("RGBA")
    comp.alpha_composite(pouch, (PX, PY))
    comp = finish(comp.convert("RGB"))
    patch_px = sum(1 for v in patch_f.crop((PX, PY, PX + PW, PY + PH)).getdata() if v > 128)
    return typography(comp, label), gains, patch_px


def main():
    gen = Image.open(RUN / "candidate_A.png").convert("RGB")
    ref = Image.open(RUN / "edit_canvas.png")
    # the handle of the shaker that touched the real seal: a hand-drawn polygon (final-frame coordinates, measured on the old composite) that
    # stays clear of the printed (R) mark; inside it the model's plain seal texture replaces the real pixels (disclosed).
    k = GW / FW
    poly = [(861, 382), (897, 382), (897, 421), (882, 421), (869, 411), (862, 404)]
    patch = Image.new("L", (GW, GH), 0)
    ImageDraw.Draw(patch).polygon([(x * k, y * k) for x, y in poly], fill=255)
    patch = patch.filter(ImageFilter.GaussianBlur(1.5))
    glass, edge = glass_edge_mask(gen, ref)
    print("glass left edge (gen px): rim %d, middle %d, base %d (fitted line)" % (edge[0], edge[len(edge) // 2], edge[-1]))
    # --- A: current glass
    A, gains, patch_px = build(gen, gen, glass, patch, "WORKING COMPOSITE - NOT PUBLISHABLE: glass covers part of the printed text")
    A.save(RUN / "final_A_corrected_1080x1350.png")
    # --- B: glass (and its reflection) moved right; exposed strip: real pouch where the pouch is, mirrored slate below it
    plate = gen.copy()
    plate.paste(gen.crop((X0 - DX, Y0, X0, GH)).transpose(Image.FLIP_LEFT_RIGHT), (X0, Y0))
    plate.paste(gen.crop((X0, Y0, GW - DX, GH)), (X0 + DX, Y0))
    glass_b = Image.new("L", (GW, GH), 0)
    glass_b.paste(glass.crop((0, 0, GW - DX, GH)), (DX, 0))
    B, _, _ = build(plate, gen, glass_b, patch, "FREE EXPERIMENT  -  glass moved right  -  NOT PUBLISHABLE until you approve")
    B.save(RUN / "final_B_glass_shift_1080x1350.png")
    # --- C: comparison (raw A | A corrected | B experiment)
    raw = gen.resize((FW, FH), Image.LANCZOS)
    c = Image.new("RGB", (FW * 3 + 40, FH), (18, 16, 16))
    for i, im in enumerate((raw, A, B)):
        c.paste(im, (i * (FW + 20), 0))
    c.save(RUN / "compare_rawA_vs_A_vs_B.png")
    # --- close-ups at 2x: packaging label area, right seal (handle patch), glass edge (rows of the wordmark/pill)
    crops = {"packaging": (404, 500, 764, 730), "seal_handle": (780, 360, 940, 470), "glass_edge": (780, 560, 940, 720), "made_in": (700, 960, 900, 1070)}
    s = Image.new("RGB", (4 * 2 * 180 + 30, 3 * 2 * 120 + 20), (18, 16, 16))
    for r, im in enumerate((raw, A, B)):
        for k, (name, b) in enumerate(crops.items()):
            t = im.crop(b).resize((360, 240), Image.LANCZOS)
            s.paste(t, (k * 370, r * 250))
    s.save(RUN / "crops_rawA_A_B.png")
    print("gain range %.2f-%.2f mean %.2f over %d pouch px" % (min(gains), max(gains), sum(gains) / len(gains), len(gains)))
    print("generated seal patch: %d px at final scale (%.2f%% of the pouch)" % (patch_px, 100 * patch_px / (PW * PH)))


if __name__ == "__main__":
    main()
