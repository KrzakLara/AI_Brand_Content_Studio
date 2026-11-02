"""Phase 5 Slide 1 cover, attempt 2 (ONE paid edit, ~1 EUR authorisation). Run from the repository root:
    python plans/gymbeam_hr/phase5/cover_slide1_v2.py prepare | preflight | generate | assemble | reference
Reuses cover_slide1.py's adapter/guard but writes ONLY v2 files: the rejected attempt-1 files are never touched.
The model paints the new fictional woman, light and shadows around the fixed real jar; the real packshot is registered to the model's jar by a uniform scale
(+1.5% to cover the model's jar edge), relit by a bounded gain, and laid on top. Typography is a separate deterministic layer (Montserrat, SIL OFL)."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont  # noqa: E402

spec = importlib.util.spec_from_file_location("c1", Path(__file__).with_name("cover_slide1.py"))
c1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c1)
RUN, HERO = c1.RUN, c1.HERO
GW, GH, FW, FH = c1.GW, c1.GH, c1.FW, c1.FH
c1.MAX_REQ = 6                          # 5 earlier requests + this one
c1.PHASE5_CAP = round(1.00 + 0.141235, 6)  # this attempt may spend at most 1.00 USD (< 1 EUR) on top of the 0.141235 already spent in Phase 5
JAR_W, JAR_X, JAR_Y = 400, 450, 1060    # jar in the generation canvas: 25% of the frame width, chest height
PINK, PINK2, BURG = (247, 180, 189), (250, 219, 224), (127, 41, 68)
CANVAS, MASK, RAW, FINAL = RUN / "cover2_canvas.png", RUN / "cover2_mask.png", RUN / "cover2_raw.png", RUN / "cover2_slide1_1080x1350.png"

PROMPT = (
    "The image shows a real product jar of a pink supplement drink already placed in front of a luminous baby-pink studio backdrop. Treat the jar as untouchable: do not move, "
    "resize, recolor, redraw or restyle it, and never add any text, letters, numbers, logos or labels anywhere. Build a luxury commercial beauty-and-fitness advertising photograph "
    "around it, in the style of a premium sports-nutrition campaign shot with a professional camera and studio strobes. "
    "A fictional young athletic woman (an invented person, not any real or famous person) with LONG, LOOSE, straight dark-brown hair worn down over her shoulders, a toned fit body, "
    "bronze natural skin with realistic pores and fine skin texture, bright confident smile looking into the camera, wearing a plain white sports bra and matching white high-waist "
    "leggings, no jewellery. She is framed from the top of her head to mid-thigh, standing in a relaxed three-quarter turn to the right of the jar, with her head and the top of her "
    "hair well below the top fifth of the frame. She holds the jar up in front of her chest: her right hand supports it from underneath with fingers spread under the base, her left "
    "hand lightly steadies its upper side with fingertips on the rim of the lid, so that NO finger or thumb touches or covers the front label. Believable hand contact and soft "
    "contact shadows. The backdrop is a clean, saturated, luminous baby pink with soft white and blush highlights (not beige, not peach, not grey), bright even high-key light from "
    "the upper left with a gentle pink bounce, crisp but creamy shadows, shallow depth of field, 85 mm editorial look, fine film grain. Keep the top fifth of the frame as empty "
    "pink backdrop for a headline. No other objects, no text.")


def prepare():
    j = Image.open(c1.SRC_JAR).convert("RGBA")
    j = j.resize((JAR_W, round(j.height * JAR_W / j.width)), Image.LANCZOS)
    bg = Image.linear_gradient("L").rotate(35).resize((GW, GH))
    canvas = Image.composite(Image.new("RGB", (GW, GH), PINK), Image.new("RGB", (GW, GH), PINK2), bg).convert("RGBA")
    canvas.alpha_composite(j, (JAR_X, JAR_Y))
    keep = Image.new("L", (GW, GH), 0)
    keep.paste(j.getchannel("A").point(lambda v: 255 if v > 200 else 0), (JAR_X, JAR_Y))
    keep = keep.filter(ImageFilter.MinFilter(3))
    mask = Image.new("RGBA", (GW, GH), (0, 0, 0, 255))
    mask.putalpha(keep)
    canvas.convert("RGB").save(CANVAS)
    mask.save(MASK)
    (RUN / "cover2_prompt.txt").write_text(PROMPT, encoding="utf-8")
    print("canvas", canvas.size, "jar", j.size, "at", (JAR_X, JAR_Y), "width share", round(JAR_W / GW, 3), "prompt chars", len(PROMPT))


def adapter():
    a = c1.adapter()
    a.worst_in_tokens, a.worst_out_tokens = 6000, 8000   # ASSUMPTION: same size+quality gave 4244 output tokens three times; bound = 2x. Real cost is read from usage.
    return a


def preflight():
    a = adapter()
    w = a.worst_case_usd()
    print(f"model {c1.MODEL} size {c1.SIZE} quality {c1.QUALITY}; requests so far {a.api_requests}/{c1.MAX_REQ}; key present {bool(a.api_key)}")
    print(f"conservative worst case for ONE request {w:.4f} USD (6000 in + 8000 out tokens assumed; observed 0.141 USD); spent so far {a.spent_usd:.6f}; this attempt cap 1.00 USD "
          f"(budget line {a.budget_usd:.4f}); spent + worst = {a.spent_usd + w:.4f}")
    a.check_budget()
    print("guard: the request fits")


def generate():
    from studio.config import load_settings
    from studio.cost import CostEstimator
    from studio.ledger import Ledger, OperationRunner
    a = adapter()
    ledger = Ledger(HERO / "ledger.db")
    runner = OperationRunner(ledger, CostEstimator(load_settings(str(ROOT / "config.yaml"))), "phase5-stills")

    def fn():
        r = a.edit(image=CANVAS.read_bytes(), mask=MASK.read_bytes(), prompt=PROMPT, size=c1.SIZE, quality=c1.QUALITY)
        RAW.write_bytes(r["png"])
        return {"file": RAW.name, "cost_usd": r["cost_usd"], "usage": r["usage"], "request_id": r["request_id"]}

    runner.estimator.check_budget(ledger.total_cost("phase5-stills"), a.worst_case_usd())
    res = runner.run(node="slide1_cover_v2", scope="S1v2", provider=a.info, key=f"phase5-stills/slide1-cover-v2/{c1.MODEL}/{c1.SIZE}/{c1.QUALITY}", fn=fn, actual_cost=lambda r: r["cost_usd"])
    print(json.dumps({**res, "spent_usd_total": a.spent_usd, "this_attempt_usd": res["cost_usd"], "phase5_spent_usd": round(a.spent_usd - c1.HERO_SPENT, 6)}, indent=1))


def register(raw, j0):
    """Uniform scale + offset of the real jar that best matches the model's jar (label band, blurred grayscale). Coarse then fine."""
    g = raw.convert("L").filter(ImageFilter.GaussianBlur(1.2))
    from PIL import ImageStat
    s0 = JAR_W / j0.width
    cache = {}

    def jar_at(s):
        if s not in cache:
            w, h = round(j0.width * s), round(j0.height * s)
            cache[s] = (w, h, j0.resize((w, h), Image.LANCZOS).convert("L").filter(ImageFilter.GaussianBlur(1.2)))
        return cache[s]

    def score(s, x, y):
        w, h, jj = jar_at(s)
        box = (int(w * .25), int(h * .35), int(w * .75), int(h * .92))
        return ImageStat.Stat(ImageChops.difference(jj.crop(box), g.crop((x + box[0], y + box[1], x + box[2], y + box[3]))).convert("L")).mean[0]
    best = None
    for k in range(0, 21):                                          # the model re-draws its jar smaller than the placeholder: search absolute scale 0.30 .. 0.50
        s = round(0.30 + 0.01 * k, 4)
        for x in range(JAR_X - 40, JAR_X + 161, 8):
            for y in range(JAR_Y - 60, JAR_Y + 101, 8):
                sc = score(s, x, y)
                if best is None or sc < best[0]:
                    best = (sc, s, x, y)
    sc0, s1, x1, y1 = best
    for s in [round(s1 * (1 + 0.003 * k), 4) for k in range(-4, 5)]:
        for x in range(x1 - 8, x1 + 9, 1):
            for y in range(y1 - 8, y1 + 9, 1):
                sc = score(s, x, y)
                if sc < best[0]:
                    best = (sc, s, x, y)
    return {"score": best[0], "scale": best[1], "x": best[2], "y": best[3]}


def nblur(img, w, r):
    num = Image.composite(img, Image.new(img.mode, img.size), w).filter(ImageFilter.GaussianBlur(r))
    return num.load(), w.filter(ImageFilter.GaussianBlur(r)).load()


def assemble():
    raw = Image.open(RAW).convert("RGB")
    if raw.size != (GW, GH):
        raw = raw.resize((GW, GH), Image.LANCZOS)
    j0 = Image.open(c1.SRC_JAR).convert("RGBA")
    reg = register(raw, j0)
    (RUN / "cover2_registration.json").write_text(json.dumps(reg), encoding="utf-8")
    grow = 1.008                                                    # uniform enlargement about the centre: the real jar then covers the model's own jar edge (no duplicate edge band)
    s = reg["scale"] * grow
    j = j0.resize((round(j0.width * s), round(j0.height * s)), Image.LANCZOS)
    x = reg["x"] - round((j.width - j0.width * reg["scale"]) / 2)
    y = reg["y"] - round((j.height - j0.height * reg["scale"]) / 2)
    # trim the packshot's dark base line (4 px + 3 px fade) as in attempt 1
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
    inner = j.getchannel("A").point(lambda v: 255 if v > 250 else 0).filter(ImageFilter.MinFilter(9))
    mjar = raw.crop((x, y, x + j.width, y + j.height))
    gn, gd = nblur(mjar, inner, 22); rn, rd = nblur(j.convert("RGB"), inner, 22)
    jp = j.load(); gains = []
    for yy in range(j.height):
        for xx in range(j.width):
            if jp[xx, yy][3] == 0 or gd[xx, yy] < 8 or rd[xx, yy] < 8:
                continue
            g = [min(1.05, max(0.70, (gn[xx, yy][c] / gd[xx, yy]) / max(1e-3, rn[xx, yy][c] / rd[xx, yy]))) for c in range(3)]
            gains.append(sum(g) / 3)
            r, gg, b, a = jp[xx, yy]
            jp[xx, yy] = (min(255, int(r * g[0])), min(255, int(gg * g[1])), min(255, int(b * g[2])), a)
    plate = raw.convert("RGBA"); plate.alpha_composite(j, (x, y))
    # HANDS IN FRONT OF THE JAR: the real jar must not hide fingertips that the model drew in front of its own jar (on the lid rim, at the base). Inside the jar
    # footprint, pixels of the RAW image that are skin or nail (hue 0-40 deg, saturation > 0.18; nails by a morphological closing) are put back on top.
    import colorsys
    hsv = raw.convert("HSV"); hp = hsv.load()
    skin = Image.new("L", raw.size, 0); sp = skin.load()
    for yy in range(y - 20, y + j.height + 20):
        for xx in range(x - 20, x + j.width + 20):
            h_, s_, v_ = hp[xx, yy]
            if (h_ <= 28 or h_ >= 250) and s_ > 46 and v_ > 135:    # PIL HSV: hue 0-255 (28 = 40 deg); v > 135 leaves out dark hair
                sp[xx, yy] = 255
    skin = skin.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.GaussianBlur(1.2))
    foot = Image.new("L", raw.size, 0)
    foot.paste(j.getchannel("A").point(lambda v: 255 if v > 20 else 0), (x, y))
    # keep only skin that is CONNECTED to skin outside the jar footprint (= the hands); label text and stray pixels inside the jar are dropped
    from collections import deque
    sk = skin.point(lambda v: 255 if v > 128 else 0).load(); ft = foot.load()
    x0, y0, x1, y1 = x - 20, y - 20, x + j.width + 20, y + j.height + 20
    seen = set(); dq = deque()
    for yy in range(y0, y1):
        for xx in range(x0, x1):
            if sk[xx, yy] and not ft[xx, yy]:
                seen.add((xx, yy)); dq.append((xx, yy))
    while dq:
        cx, cy = dq.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if x0 <= nx < x1 and y0 <= ny < y1 and (nx, ny) not in seen and sk[nx, ny]:
                seen.add((nx, ny)); dq.append((nx, ny))
    conn = Image.new("L", raw.size, 0); cp = conn.load()
    for (cx, cy) in seen:
        cp[cx, cy] = 255
    skin = conn.filter(ImageFilter.GaussianBlur(1.0))
    front = ImageChops.multiply(skin, foot)
    front.save(RUN / "cover2_hands_in_front_mask.png")
    plate = Image.composite(raw.convert("RGBA"), plate, front)
    im = plate.convert("RGB").resize((FW, FH), Image.LANCZOS)
    im.save(RUN / "cover2_nolettering_1080x1350.png")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(RUN / "font/Montserrat.ttf"), 120); f.set_variation_by_name("ExtraBold")
    while d.textlength("VAŠ RUŽIČASTI", font=f) > 860:
        f = ImageFont.truetype(str(RUN / "font/Montserrat.ttf"), f.size - 2); f.set_variation_by_name("ExtraBold")
    d.text((60, 44), "VAŠ RUŽIČASTI", font=f, fill=BURG)
    d.text((60, 44 + int(f.size * 1.1)), "RITUAL.", font=f, fill=BURG)
    sub = ImageFont.truetype(str(RUN / "font/Montserrat.ttf"), 40); sub.set_variation_by_name("Bold")
    d.text((64, 1150), "SVE ŠTO TREBA ZNATI", font=sub, fill=BURG)
    d.text((64, 1200), "U ŠEST KADROVA.", font=sub, fill=BURG)
    im.save(FINAL)
    k = FW / GW
    out = {"jar_final_px": [round(j.width * k), round(j.height * k)], "jar_xy_final": [round(x * k), round(y * k)], "registration": reg, "enlarge": grow,
           "gain_mean": round(sum(gains) / len(gains), 3), "gain_min": round(min(gains), 3), "gain_max": round(max(gains), 3), "headline_px": f.size}
    (RUN / "cover2_fidelity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out))


def reference():
    raw = Image.open(RAW).convert("RGB")
    d = RUN / "model_reference_v2"; d.mkdir(exist_ok=True)
    raw.resize((800, 1000), Image.LANCZOS).save(d / "full_reference.png")
    raw.crop((300, 250, 1300, 1050)).save(d / "face_hair_light_crop.png")
    (d / "README.md").write_text("Fictional model reference v2 (AI-generated person; not a real or identifiable person). Source cover2_raw.png. NOT yet approved by Lara; "
                                 "do not use for Slide 5 until she approves the cover. Identity preservation is not guaranteed.\n", encoding="utf-8")


if __name__ == "__main__":
    {"prepare": prepare, "preflight": preflight, "generate": generate, "assemble": assemble, "reference": reference}[sys.argv[1]]()
