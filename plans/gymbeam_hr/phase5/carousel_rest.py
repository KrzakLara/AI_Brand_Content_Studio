"""Phase 5: slides 2-6 of the Colla Pink carousel. Run from the repository root:
    python plans/gymbeam_hr/phase5/carousel_rest.py prepare|preflight|generate|assemble <slide>     slide in 2,3,4,5,6
Same pipeline as the approved cover: the model paints scene, props and light around FIXED real jar packshots (mask-protected); the real jars are registered to
the model's by a uniform scale + offset, edge-cleaned, relit by a bounded gain and laid on top; all text is deterministic Montserrat (SIL OFL). Slides 3 and 5 are
VIDEO slots: only KEYFRAMES are produced here (no video provider is available); they are labelled as keyframes and never presented as video.
Every paid call goes through the existing adapter, ledger and budget guard (Phase 5 cap 3.00 USD, request cap raised for this production)."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


c1, rt = _load("cover_slide1"), _load("retouch_cover2")
RUN, HERO = c1.RUN, c1.HERO
OUTD = RUN / "carousel"
OUTD.mkdir(exist_ok=True)
GW, GH, FW, FH = 1600, 2000, 1080, 1350
K = FW / GW
c1.MAX_REQ = 14
c1.PHASE5_CAP = 3.0
PINK, PINK2, BURG, BLUSH = (247, 180, 189), (250, 219, 224), (127, 41, 68), (251, 243, 242)
JARS = {n: RUN / f"jars/jar_{n}.png" for n in ("strawberry", "grape", "mango", "raspberry", "wild")}
ASPECT = 875 / 762


def mont(size, weight="ExtraBold"):
    f = ImageFont.truetype(str(RUN / "font/Montserrat.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def fit(d, text, width, weight="ExtraBold", hi=300):
    s = hi
    while s > 10 and d.textlength(text, font=mont(s, weight)) > width:
        s -= 2
    return s


def bg_canvas():
    g = Image.linear_gradient("L").rotate(35).resize((GW, GH))
    return Image.composite(Image.new("RGB", (GW, GH), PINK), Image.new("RGB", (GW, GH), PINK2), g).convert("RGBA")


def adapter():
    a = c1.adapter()
    a.worst_in_tokens, a.worst_out_tokens = 12000, 8000
    return a


# ---------------------------------------------------------------- slide definitions (generation-canvas coordinates, 1600x2000)
NEG = (" Never add any text, letters, numbers, logos or labels anywhere in the picture. Photorealistic luxury commercial photography, high-key bright light from the upper left with a "
       "soft pink bounce, saturated luminous baby-pink and blush-white palette (not beige, not peach, not grey), shallow depth of field, 85 mm, fine film grain.")
UNTOUCH = "The jar (or jars) already standing in the picture are real products: treat them as untouchable, do not move, resize, recolor, redraw or restyle them."


def slide_spec(n):
    if n == 2:
        return dict(jars=[("grape", 520, 120, 780)], mask=True, size=(1600, 2000),
                    prompt=UNTOUCH + " Build an editorial macro product photograph on a luminous baby-pink surface and backdrop around the jar on the left: fine pale collagen powder softly scattered "
                    "and mounded in front of the jar, a small white scoop dusted with powder lying beside it, a few GREEN grapes with fresh water droplets and a green grape leaf, subtle sparkle "
                    "highlights on the powder. The jar and its props occupy the left 60% of the frame; keep the right 35% of the frame and the top 28% of the frame as clean empty pink backdrop." + NEG)
    if n == 4:
        return dict(jars=[("strawberry", 440, 90, 800)], mask=True, size=(1600, 2000),
                    prompt=UNTOUCH + " Build an appetizing editorial beverage photograph on a luminous baby-pink surface around the jar on the left: to the right of the jar a tall clear glass of plain water "
                    "(transparent, no colour added) with ice cubes, a slice of lemon and a fresh strawberry on the rim, beside it a few whole ripe strawberries and halved lemons and a small "
                    "white measuring scoop with fine pale powder; condensation droplets on the glass. Keep the top 25% and the bottom 25% of the frame as clean empty pink backdrop." + NEG)
    if n == 6:
        # back row: strawberry, grape, mango; front row: raspberry, wild berries (generation coordinates, jar width 400)
        return dict(jars=[("strawberry", 400, 90, 490), ("grape", 400, 600, 490), ("mango", 400, 1110, 490),
                          ("raspberry", 400, 345, 1020), ("wild", 400, 855, 1020)], mask=True, size=(1600, 2000),
                    prompt=UNTOUCH + " The five jars are identical dusty-rose product jars with different printed flavour words; do not change any of them. Build a luxurious editorial still-life of "
                    "premium food photography on a luminous baby-pink surface around them, placing fresh fruit in the gaps and in front, strictly matched to each jar's printed flavour: "
                    "at the base of the top-left jar (strawberry lemonade) fresh strawberries and lemon halves; at the top-middle jar (grape) GREEN grapes on the vine; at the top-right jar "
                    "(mango orange) a halved mango and orange slices; at the lower-left jar (raspberry) fresh raspberries; at the lower-right jar (wild berries) mixed berries: blueberries, "
                    "blackberries, strawberries and raspberries. Soft contact shadows, water droplets on the fruit. Keep the top 22% and the bottom 20% of the frame as clean empty pink backdrop." + NEG)
    if n == 3:
        return dict(jars=[], mask=False, size=(1600, 2000), extra=[],
                    prompt="Create a photorealistic macro commercial photograph, frozen mid-motion, of fine pale pink-white collagen powder pouring from a small white scoop into a tall clear glass of "
                    "water on a luminous baby-pink surface: the powder stream, a swirling cloud of powder dissolving in the water, tiny bubbles, glass highlights, water droplets on the glass, "
                    "completely clean glass with no markings. No jar, no packaging, no person. The glass is in the lower-middle of the frame; keep the top 28% as clean empty pink backdrop." + NEG)
    if n == 5:
        return dict(jars=[], mask=False, size=(1600, 2000), extra=[RUN / "cover2_raw.png"], base=RUN / "carousel_final/slide1_cover_FROZEN_1080x1350.png",
                    prompt="The input pictures show one fictional woman. Create a NEW photograph of exactly the SAME woman (same face, same long loose dark-brown hair, same skin tone, same athletic "
                    "build, same white sports bra and white leggings) in the same luminous baby-pink studio, now in a candid lifestyle moment: she is laughing softly with her eyes half closed, holding a tall "
                    "clear glass of water with ice, a lemon slice and a strawberry in one hand raised near her chin, the other hand relaxed at her waist, hair moving slightly as if turning. She is "
                    "framed from the head to the mid-thigh, her head well below the top fifth of the frame. No jar, no packaging, no text anywhere. Keep the same quality, lighting and colour as the "
                    "inputs." + NEG)
    raise SystemExit("unknown slide")


def canvas_for(n):
    sp = slide_spec(n)
    if n == 5:
        return Image.open(sp["extra"][0]).convert("RGB").resize((GW, GH), Image.LANCZOS), None
    c = bg_canvas()
    keep = Image.new("L", (GW, GH), 0)
    for key, w, x, y in sp["jars"]:
        j0 = Image.open(JARS[key]).convert("RGBA")
        j = j0.resize((w, round(w * ASPECT)), Image.LANCZOS)
        c.alpha_composite(j, (x, y))
        keep.paste(j.getchannel("A").point(lambda v: 255 if v > 200 else 0), (x, y))
    if not sp["mask"]:
        return c.convert("RGB"), None
    mask = Image.new("RGBA", (GW, GH), (0, 0, 0, 255))
    mask.putalpha(keep.filter(ImageFilter.MinFilter(3)))
    return c.convert("RGB"), mask


def prepare(n):
    c, m = canvas_for(n)
    c.save(OUTD / f"s{n}_canvas.png")
    if m:
        m.save(OUTD / f"s{n}_mask.png")
    (OUTD / f"s{n}_prompt.txt").write_text(slide_spec(n)["prompt"], encoding="utf-8")
    print("slide", n, "canvas saved; jars", [(k, w, x, y) for k, w, x, y in slide_spec(n)["jars"]])


def preflight(n):
    a = adapter()
    w = a.worst_case_usd()
    print(f"slide {n}: requests {a.api_requests}/{c1.MAX_REQ}; spent {a.spent_usd:.6f}; worst case one request {w:.4f}; budget line {a.budget_usd:.4f} "
          f"(Phase 5 spent {a.spent_usd - c1.HERO_SPENT:.4f} of 3.00); fits: {a.spent_usd + w <= a.budget_usd}")
    a.check_budget()


def generate(n):
    from studio.config import load_settings
    from studio.cost import CostEstimator
    from studio.ledger import Ledger, OperationRunner
    sp = slide_spec(n)
    a = adapter()
    ledger = Ledger(HERO / "ledger.db")
    runner = OperationRunner(ledger, CostEstimator(load_settings(str(ROOT / "config.yaml"))), "phase5-stills")
    img = (sp.get("base") or (OUTD / f"s{n}_canvas.png"))
    mask = (OUTD / f"s{n}_mask.png").read_bytes() if (OUTD / f"s{n}_mask.png").is_file() and sp["mask"] else None
    extra = tuple(Path(p).read_bytes() for p in sp.get("extra", [])) if n == 5 else ()
    if n == 5:
        extra = (Path(sp["extra"][0]).read_bytes(),)

    def fn():
        r = a.edit(image=Path(img).read_bytes(), mask=mask, prompt=sp["prompt"], size=c1.SIZE, quality=c1.QUALITY, extra_images=extra)
        (OUTD / f"s{n}_raw.png").write_bytes(r["png"])
        return {"file": f"s{n}_raw.png", "cost_usd": r["cost_usd"], "usage": r["usage"], "request_id": r["request_id"]}

    runner.estimator.check_budget(ledger.total_cost("phase5-stills"), a.worst_case_usd())
    res = runner.run(node=f"carousel_slide{n}", scope=f"S{n}", provider=a.info, key=f"phase5-stills/carousel-slide{n}/{c1.MODEL}/{c1.SIZE}/{c1.QUALITY}", fn=fn, actual_cost=lambda r: r["cost_usd"])
    print(json.dumps({"slide": n, "request_id": res["request_id"], "cost_usd": res["cost_usd"], "usage": res["usage"], "spent_total": a.spent_usd,
                      "phase5_spent": round(a.spent_usd - c1.HERO_SPENT, 6), "phase5_remaining": round(3.0 - (a.spent_usd - c1.HERO_SPENT), 6)}))


# ---------------------------------------------------------------- jar registration + composite
def jar_mask(raw):
    """Pixels that look like the model's jar: dusty-rose body (R-G 25..52, darker than the backdrop, B>=G) or the neutral silver lid/base. Fruit (green/yellow/red) and the
    saturated pink backdrop are excluded by colour."""
    sm = raw.resize((GW // 4, GH // 4), Image.BILINEAR)
    m = Image.new("L", sm.size, 0); mp = m.load(); px = sm.load()
    for y in range(sm.height):
        for x in range(sm.width):
            r, g, b = px[x, y]
            v = max(r, g, b)
            body = 25 <= r - g <= 52 and v <= 228 and b >= g - 2
            neutral = abs(r - g) <= 10 and abs(g - b) <= 12 and v >= 110
            if body or neutral:
                mp[x, y] = 255
    return m


def register(raw, j0, w0, x0, y0, rng=110, mask=None):
    """Silhouette registration: uniform scale + offset of the real jar's alpha maximising IoU with the colour mask of the model's jar (1/4 resolution)."""
    m = mask or jar_mask(raw)
    a0 = j0.convert("RGBA").getchannel("A").point(lambda v: 255 if v > 128 else 0)
    s0 = w0 / j0.width
    best = None
    for k in range(0, 21):
        s = round(s0 * (0.70 + 0.03 * k), 4)
        w, h = round(j0.width * s / 4), round(j0.height * s / 4)
        t = a0.resize((w, h), Image.BILINEAR).point(lambda v: 255 if v > 128 else 0)
        ta = ImageStat.Stat(t).sum[0] / 255
        for x in range((x0 - rng) // 4, (x0 + rng) // 4 + 1, 2):
            for y in range((y0 - rng) // 4, (y0 + rng) // 4 + 1, 2):
                if x < 0 or y < 0 or x + w > m.width or y + h > m.height:
                    continue
                mc = m.crop((x, y, x + w, y + h))
                inter = ImageStat.Stat(ImageChops.multiply(mc, t)).sum[0] / 255 / 255 * 255
                inter = ImageStat.Stat(ImageChops.darker(mc, t)).sum[0] / 255
                ma = ImageStat.Stat(mc).sum[0] / 255
                union = ta + ma - inter
                sc = inter / union if union else 0
                if best is None or sc > best[0]:
                    best = (sc, s, x * 4, y * 4)
    sc, s1, x1, y1 = best
    for s in [round(s1 * (1 + 0.006 * k), 4) for k in range(-5, 6)]:
        w, h = round(j0.width * s / 4), round(j0.height * s / 4)
        t = a0.resize((w, h), Image.BILINEAR).point(lambda v: 255 if v > 128 else 0); ta = ImageStat.Stat(t).sum[0] / 255
        for x in range(x1 // 4 - 3, x1 // 4 + 4):
            for y in range(y1 // 4 - 3, y1 // 4 + 4):
                if x < 0 or y < 0 or x + w > m.width or y + h > m.height:
                    continue
                mc = m.crop((x, y, x + w, y + h)); inter = ImageStat.Stat(ImageChops.darker(mc, t)).sum[0] / 255
                union = ta + ImageStat.Stat(mc).sum[0] / 255 - inter
                sc2 = inter / union if union else 0
                if sc2 > best[0]:
                    best = (sc2, s, x * 4, y * 4)
    return {"iou": round(best[0], 3), "scale": best[1], "x": best[2], "y": best[3]}


def front_mask(raw, canvas, n_blur=2, thr=62):
    """Objects the model drew IN FRONT of a protected jar (fruit, berries, drops) = where the raw differs strongly from the canvas it was given."""
    d = ImageChops.difference(raw.convert("RGB"), canvas.convert("RGB"))
    r, g, b = d.split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), b).filter(ImageFilter.GaussianBlur(n_blur)).point(lambda v: 255 if v > thr else 0)
    return m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.0))


def place_real_jar(raw_rgba, key, reg, front, grow=1.03):
    rt.JAR = JARS[key]
    j0 = rt.clean_jar()
    base_w, base_h = Image.open(JARS[key]).size
    s = reg["scale"] * grow
    j = j0.resize((round(j0.width * s), round(j0.height * s)), Image.LANCZOS)
    x = reg["x"] - round((j.width - base_w * reg["scale"]) / 2)
    y = reg["y"] - round((j.height - base_h * reg["scale"]) / 2)
    al = j.getchannel("A"); ap = al.load(); cols = {}
    for xx in range(j.width):
        for yy in range(j.height - 1, -1, -1):
            if ap[xx, yy] > 128:
                cols[xx] = yy; break
    for xx, yb in cols.items():
        for k in range(7):
            if yb - k >= 0:
                ap[xx, yb - k] = int(ap[xx, yb - k] * (0.0 if k < 4 else (k - 3) / 4))
    j.putalpha(al)
    raw_rgb = raw_rgba.convert("RGB")
    # LUMINANCE-ONLY relight (one gain for R, G and B, so no colour of fruit can leak into the jar), measured only where nothing is in front of the jar
    fr = front.crop((x, y, x + j.width, y + j.height))
    inner = ImageChops.multiply(j.getchannel("A").point(lambda v: 255 if v > 250 else 0).filter(ImageFilter.MinFilter(9)), ImageChops.invert(fr.point(lambda v: 255 if v > 20 else 0).filter(ImageFilter.MaxFilter(7))))
    gl, gd = rt.nblur(raw_rgb.crop((x, y, x + j.width, y + j.height)).convert("L"), inner, 22); rl, rd = rt.nblur(j.convert("L"), inner, 22)
    jp = j.load(); gains = []
    for yy in range(j.height):
        for xx in range(j.width):
            if jp[xx, yy][3] == 0 or gd[xx, yy] < 8 or rd[xx, yy] < 8:
                continue
            g = min(1.08, max(0.78, (gl[xx, yy] / gd[xx, yy]) / max(1e-3, rl[xx, yy] / rd[xx, yy])))
            gains.append(g)
            r, gg, b, a = jp[xx, yy]
            jp[xx, yy] = (min(255, int(r * g)), min(255, int(gg * g)), min(255, int(b * g)), a)
    sh = Image.new("L", j.size, 255); sd = ImageDraw.Draw(sh); ew = max(3, round(j.width * 0.06))
    for k in range(ew):
        v = int(255 * (1 - 0.09 * (1 - k / ew) ** 2))
        sd.line((k, 0, k, j.height), fill=v); sd.line((j.width - 1 - k, 0, j.width - 1 - k, j.height), fill=v)
    j2 = ImageChops.multiply(j.convert("RGB"), Image.merge("RGB", (sh, sh, sh))).convert("RGBA"); j2.putalpha(al)
    raw_rgba.alpha_composite(j2, (x, y))
    foot = Image.new("L", raw_rgba.size, 0); foot.paste(al, (x, y))
    return {"xy": [x, y], "size": list(j.size), "gain_mean": round(sum(gains) / max(1, len(gains)), 3), "gain_min": round(min(gains), 3) if gains else None}, foot


def plate_with_jars(n):
    sp = slide_spec(n)
    raw = Image.open(OUTD / f"s{n}_raw.png").convert("RGB")
    if raw.size != (GW, GH):
        raw = raw.resize((GW, GH), Image.LANCZOS)
    canvas = Image.open(OUTD / f"s{n}_canvas.png").convert("RGB")
    front = front_mask(raw, canvas)
    base = raw.convert("RGBA")
    info = {}; foot_all = Image.new("L", raw.size, 0)
    for key, w, x, y in sp["jars"]:
        # the model kept its jars in the protected positions (silhouette and label-band searches both drifted, because it re-renders the label text): the real jar goes back
        # exactly where the canvas had it, enlarged 3% about its centre so that it covers the model's own jar edge (uniform scale only)
        reg = {"scale": round(w / Image.open(JARS[key]).width, 4), "x": x, "y": y, "method": "placement"}
        i2, foot = place_real_jar(base, key, reg, front)
        info[key] = {"registration": reg, **i2}
        foot_all = ImageChops.lighter(foot_all, foot)
    # objects in front of the jars (fruit, berries, water drops) are put back from the raw, only inside the jars footprint and only in the bottom 8% of each jar, below the printed text
    lower = Image.new("L", raw.size, 0); ld = ImageDraw.Draw(lower)
    for key, w, x, y in sp["jars"]:
        ld.rectangle((x - 40, y + int(w * ASPECT * 0.92), x + w + 40, y + int(w * ASPECT) + 60), fill=255)
    hsv = raw.convert("HSV"); hp = hsv.load(); fruit = Image.new("L", raw.size, 0); fp = fruit.load()
    fm = front.load(); ftm = foot_all.load()
    for yy in range(GH):
        for xx in range(GW):
            if fm[xx, yy] > 40 and ftm[xx, yy] > 0:
                h_, s_, v_ = hp[xx, yy]
                if s_ > 115 or v_ < 105 or 38 <= h_ <= 120:     # saturated (strawberry, lemon, orange, mango), dark (berries) or green (grapes, leaves); jar pink/white is neither
                    fp[xx, yy] = 255
    fruit = fruit.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    restore = ImageChops.multiply(ImageChops.multiply(fruit, foot_all), lower)
    info["front_objects_restored_px"] = int(ImageStat.Stat(restore.point(lambda v: 255 if v > 128 else 0)).sum[0] / 255)
    base = Image.composite(raw.convert("RGBA"), base, restore)
    restore.save(OUTD / f"s{n}_front_mask.png")
    return base.convert("RGB").resize((FW, FH), Image.LANCZOS), info


# ---------------------------------------------------------------- typography (deterministic)
def type_slide(n, im):
    d = ImageDraw.Draw(im)

    def line(text, xy, size, weight="ExtraBold", fill=BURG):
        d.text(xy, text, font=mont(size, weight), fill=fill)
    if n == 2:
        s = fit(d, "UNUTRA?", 800, hi=150)
        line("ŠTO JE", (60, 44), s); line("UNUTRA?", (60, 44 + int(s * 1.08)), s)
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle((530, 410, 1046, 1000), 34, fill=(251, 243, 242, 218))   # readability panel
        im.paste(Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")); d = ImageDraw.Draw(im)
        x, y = 566, 440
        for big, small in (("6300 mg", "kolagenskih peptida"), ("400 mg", "ekstrakta sjemenki grožđa 20:1"), ("40 mg", "hijaluronske kiseline")):
            line(big, (x, y), 66); line(small, (x + 2, y + 74), 25, "SemiBold"); y += 130
        line("cink 10 mg · selen 89 μg", (x + 2, y + 8), 26, "Bold"); line("vitamin C 500 mg", (x + 2, y + 42), 26, "Bold")
        line("niacin 32 mg · B2 2,8 mg", (x + 2, y + 92), 26, "Bold"); line("A 800 μg · biotin 50 μg", (x + 2, y + 126), 26, "Bold")
        line("Na stranici proizvoda piše: količine u 8 g (1 mjerica).", (60, 1252), 22, "SemiBold"); line("Izvor: gymbeam.hr, 28. 10. 2026.", (60, 1284), 22, "SemiBold")
    if n == 3:
        s = fit(d, "PRIPREMA.", 900, hi=128)
        line("PRIPREMA.", (60, 44), s); line("PRAH, VODA, MIJEŠANJE.", (64, 44 + int(s * 1.1)), 42, "Bold")
    if n == 4:
        s = fit(d, "PRIPREMITI?", 900, hi=112)
        line("KAKO", (60, 44), s); line("PRIPREMITI?", (60, 44 + int(s * 1.08)), s)
        steps = [("1", "1 mjerica", "(8 g) praha", "scoop"), ("2", "200–300 ml", "vode", "glass"), ("3", "promiješajte", "do otapanja", "stir")]
        cw = 320
        for i, (num, a, b, icon) in enumerate(steps):
            x0 = 40 + i * (cw + 20); y0 = 1030
            d.rounded_rectangle((x0, y0, x0 + cw, y0 + 250), 26, fill=(255, 240, 243), outline=BURG, width=3)
            cx, cy = x0 + 60, y0 + 62
            d.ellipse((cx - 38, cy - 38, cx + 38, cy + 38), fill=BURG); d.text((cx - 11, cy - 24), num, font=mont(44, "ExtraBold"), fill=(255, 240, 243))
            ix, iy = x0 + cw - 90, y0 + 62
            if icon == "scoop":
                d.ellipse((ix - 34, iy - 6, ix + 20, iy + 40), outline=BURG, width=6); d.line((ix + 16, iy + 4, ix + 54, iy - 26), fill=BURG, width=7)
            if icon == "glass":
                d.polygon([(ix - 32, iy - 34), (ix + 32, iy - 34), (ix + 24, iy + 40), (ix - 24, iy + 40)], outline=BURG, width=6); d.line((ix - 28, iy - 4, ix + 28, iy - 4), fill=BURG, width=5)
            if icon == "stir":
                for r in (8, 18, 28):
                    d.arc((ix - r, iy - r, ix + r, iy + r), 200, 520, fill=BURG, width=6)
            d.text((x0 + 22, y0 + 128), a, font=mont(40, "ExtraBold"), fill=BURG); d.text((x0 + 22, y0 + 178), b, font=mont(30, "SemiBold"), fill=BURG)
    if n == 5:
        s = fit(d, "MALI RITUAL.", 900, hi=96)
        line("MALI", (60, 44), s); line("RITUAL.", (60, 44 + int(s * 1.08)), s)
        line("KAD VAM ODGOVARA.", (64, 1180), 40, "Bold"); line("Na stranici proizvoda piše: napitak možete konzumirati", (64, 1244), 22, "SemiBold"); line("u bilo koje doba dana. Izvor: gymbeam.hr, 28. 10. 2026.", (64, 1274), 22, "SemiBold")
    if n == 6:
        s = fit(d, "SVOJ OKUS.", 900, hi=124)
        line("ODABERI", (60, 44), s); line("SVOJ OKUS.", (60, 44 + int(s * 1.08)), s)
        line("Jagoda - limunada · grožđe · mango - naranča", (60, 1190), 28, "Bold"); line("malina · šumsko voće", (60, 1228), 28, "Bold")
        line("Spremite objavu. Više na linku u opisu profila.", (60, 1280), 26, "SemiBold")
    return im


def assemble(n):
    sp = slide_spec(n)
    if sp["jars"]:
        plate, info = plate_with_jars(n)
    else:
        raw = Image.open(OUTD / f"s{n}_raw.png").convert("RGB")
        plate, info = raw.resize((FW, FH), Image.LANCZOS), {}
    plate.save(OUTD / f"s{n}_nolettering_1080x1350.png")
    name = {3: "slide3_VIDEO_KEYFRAME_NOT_A_VIDEO", 5: "slide5_VIDEO_KEYFRAME_NOT_A_VIDEO"}.get(n, f"slide{n}")
    type_slide(n, plate.copy()).save(OUTD / f"{name}_1080x1350.png")
    (OUTD / f"s{n}_assembly.json").write_text(json.dumps(info, indent=1))
    print(name, json.dumps(info))


if __name__ == "__main__":
    {"prepare": prepare, "preflight": preflight, "generate": generate, "assemble": assemble}[sys.argv[1]](int(sys.argv[2]))
