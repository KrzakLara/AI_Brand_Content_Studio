"""Phase 5, Slide 1 cover proof (ONE paid edit authorised by Lara, 2026-10-28). Run from the repository root:
    python plans/gymbeam_hr/phase5/cover_slide1.py prepare     # free: jar layer placed on a blush canvas, mask, prompt
    python plans/gymbeam_hr/phase5/cover_slide1.py preflight   # free: cost guard dry run
    python plans/gymbeam_hr/phase5/cover_slide1.py generate    # PAID: exactly one request (same ledger, same request log; cap 5 = 4 earlier + this one)
    python plans/gymbeam_hr/phase5/cover_slide1.py assemble    # free: real jar (relit) over the plate + typography -> 1080x1350
    python plans/gymbeam_hr/phase5/cover_slide1.py reference   # free: reusable fictional-model reference crops

The model paints the fictional woman, her hands, the studio, the light and the contact shadows around the real jar; the real Strawberry Lemonade packshot pixels
are laid back on top by code (relit by a smooth bounded gain). Generated jar pixels are always discarded. Output goes to the git-ignored runs/colla-pink/.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont  # noqa: E402

RUN = ROOT / "runs/colla-pink"
HERO = ROOT / "runs/hero-proof"
MODEL, SIZE, QUALITY = "gpt-image-2.5-sunburst", "1600x2000", "xhigh"
GW, GH, FW, FH = 1600, 2000, 1080, 1350
JAR_W = 480                                  # jar width in the generation canvas (30% of the frame): life-size relative to a woman's torso
SRC_JAR = RUN / "jar_strawberry_layer.png"   # RGBA silhouette matte of the official packshot (jar_matte.py), sha256 of the source in colla_pink_assets.yaml
JAR_X, JAR_Y = None, 1010                    # centre x = frame centre; top y fixed (chest height)
PHASE5_CAP = 3.0
HERO_SPENT = 0.281945                        # spent before Phase 5 (same usage file); the Phase 5 stills cap is 3.00 USD ON TOP of it
MAX_REQ = 5                                  # 4 earlier requests (401, 429, 2 paid hero images) + this one
BURGUNDY, BLUSH = (110, 31, 53), (251, 243, 242)

PROMPT = (
    "The image shows a real product jar of a pink supplement drink already standing in place on a plain blush backdrop. Treat the jar as untouchable: do not move, resize, "
    "recolor, redraw or restyle it, and never add any text, letters, numbers, logos or labels anywhere in the picture. "
    "Paint a premium editorial beauty photograph around it. A fictional young woman (a made-up person, not any real or famous person) with shoulder-length chestnut hair in a "
    "low sleek bun, natural makeup and a calm soft smile, wearing white activewear (a fitted white sports top under a white zip-up training jacket), is seen from the mid-chest "
    "upwards, facing the camera, shoulders slightly turned. She holds the jar upright and front-facing at chest height in front of her with BOTH hands at its two sides: "
    "her palms and fingers cradle the left and right edges of the jar with the fingers wrapping around the back of it, so that only the heels of her hands and her thumbs "
    "touch its sides; no finger or thumb lies in front of the jar's front, so the whole front of the jar stays completely visible. The jar is life-size (about ten centimetres "
    "wide): her shoulders are about four jar-widths wide and reach the edges of the frame. Natural hands with believable skin texture and proportions, gentle realistic contact "
    "and soft contact shadows between her hands and the jar. Seamless soft baby-pink and blush-white studio, one large soft key light from the left with a gentle pink bounce, "
    "creamy shadows, shallow depth of field, an 85 mm editorial beauty photograph with fine film grain. Keep the top fifth of the frame as empty soft blush backdrop for a "
    "headline and keep her head fully below it. No jewellery, no other objects, no text.")


def registration():
    """Where the MODEL actually drew its jar (it re-renders the jar a little smaller than the placeholder): a uniform scale + offset found by matching
    the label band (cover_registration.json, mean abs diff in the file). The real jar is registered to it; it is never stretched or distorted."""
    f = RUN / "cover_registration.json"
    return json.loads(f.read_text()) if f.is_file() else None


def jar_layer(registered=False):
    j = Image.open(SRC_JAR).convert("RGBA")
    reg = registration() if registered else None
    s = reg["scale"] if reg else JAR_W / j.width
    return j.resize((round(j.width * s), round(j.height * s)), Image.LANCZOS)


def jar_pos(j, registered=False):
    reg = registration() if registered else None
    return (reg["x"], reg["y"]) if reg else ((GW - j.width) // 2, JAR_Y)


def prepare():
    j = jar_layer()
    x, y = jar_pos(j)
    bg = Image.linear_gradient("L").resize((GW, GH))
    canvas = Image.composite(Image.new("RGB", (GW, GH), (246, 214, 220)), Image.new("RGB", (GW, GH), BLUSH), bg).convert("RGBA")
    canvas.alpha_composite(j, (x, y))
    keep = Image.new("L", (GW, GH), 0)
    keep.paste(j.getchannel("A").point(lambda v: 255 if v > 200 else 0), (x, y))
    keep = keep.filter(ImageFilter.MinFilter(3))                          # protected area 1 px inside the jar edge
    mask = Image.new("RGBA", (GW, GH), (0, 0, 0, 255))
    mask.putalpha(keep)                                                    # alpha 255 = keep, 0 = edit (OpenAI convention)
    canvas.convert("RGB").save(RUN / "cover_canvas.png")
    mask.save(RUN / "cover_mask.png")
    (RUN / "cover_prompt.txt").write_text(PROMPT, encoding="utf-8")
    print("canvas", canvas.size, "jar", j.size, "at", (x, y), "jar width share", round(j.width / GW, 3))


def adapter():
    from studio.cli import load_dotenv
    from studio.providers.live import OpenAIImageEdit
    from studio.tools.transport import GuardedTransport, UrllibTransport
    load_dotenv(ROOT / ".env")
    t = GuardedTransport(UrllibTransport(), limit=MAX_REQ, hosts=("api.openai.com",), log_path=HERO / "api_requests.log")
    return OpenAIImageEdit(MODEL, t, budget_usd=round(HERO_SPENT + PHASE5_CAP, 6), max_requests=MAX_REQ, usage_path=HERO / "api_usage.jsonl")


def preflight():
    a = adapter()
    w = a.worst_case_usd()
    print(f"model {MODEL}  size {SIZE}  quality {QUALITY}  requests so far {a.api_requests}/{MAX_REQ}  key present: {bool(a.api_key)}")
    print(f"guard worst case for ONE request {w:.4f} USD (assumption {a.worst_in_tokens} image-in + {a.worst_out_tokens} image-out tokens); spent so far {a.spent_usd:.6f} "
          f"(hero {HERO_SPENT}); Phase 5 spent {a.spent_usd - HERO_SPENT:.6f} of {PHASE5_CAP:.2f}; spent + worst = {a.spent_usd + w:.4f} of {a.budget_usd:.4f}")
    print(f"observed cost of the same size/quality request: {a.max_seen_usd:.6f} USD; expected for this edit about 0.14 USD (1 input image)")
    a.check_budget()
    print("guard: the request fits")


def generate():
    from studio.config import load_settings
    from studio.cost import CostEstimator
    from studio.ledger import Ledger, OperationRunner
    a = adapter()
    ledger = Ledger(HERO / "ledger.db")                                    # the existing ledger: nothing is reset
    runner = OperationRunner(ledger, CostEstimator(load_settings(str(ROOT / "config.yaml"))), "phase5-stills")

    def fn():
        r = a.edit(image=(RUN / "cover_canvas.png").read_bytes(), mask=(RUN / "cover_mask.png").read_bytes(), prompt=PROMPT, size=SIZE, quality=QUALITY)
        (RUN / "cover_raw.png").write_bytes(r["png"])
        return {"file": "cover_raw.png", "cost_usd": r["cost_usd"], "usage": r["usage"], "request_id": r["request_id"]}

    runner.estimator.check_budget(ledger.total_cost("phase5-stills"), a.worst_case_usd())
    res = runner.run(node="slide1_cover", scope="S1", provider=a.info, key=f"phase5-stills/slide1-cover/{MODEL}/{SIZE}/{QUALITY}", fn=fn, actual_cost=lambda r: r["cost_usd"])
    print(json.dumps({**res, "spent_usd_total": a.spent_usd, "phase5_spent_usd": round(a.spent_usd - HERO_SPENT, 6), "phase5_remaining_usd": round(PHASE5_CAP - (a.spent_usd - HERO_SPENT), 6)}, indent=1))


def nblur(img, w, r):
    num = Image.composite(img, Image.new(img.mode, img.size), w).filter(ImageFilter.GaussianBlur(r))
    return num.load(), w.filter(ImageFilter.GaussianBlur(r)).load()


def assemble(out_name="cover_slide1_1080x1350.png"):
    raw = Image.open(RUN / "cover_raw.png").convert("RGB")
    if raw.size != (GW, GH):
        raw = raw.resize((GW, GH), Image.LANCZOS)
    j = jar_layer(True)
    x, y = jar_pos(j, True)
    # smooth lighting gain from the model's own jar (it re-renders the jar in its light); bounded like the hero; the model's jar pixels are then discarded
    a = j.getchannel("A")
    box = (x, y, x + j.width, y + j.height)
    mjar = raw.crop(box)
    inner = a.point(lambda v: 255 if v > 250 else 0).filter(ImageFilter.MinFilter(9))
    gn, gd = nblur(mjar, inner, 22)
    rn, rd = nblur(j.convert("RGB"), inner, 22)
    jp = j.load()
    gains = []
    for yy in range(j.height):
        for xx in range(j.width):
            if jp[xx, yy][3] == 0 or gd[xx, yy] < 8 or rd[xx, yy] < 8:
                continue
            g = [min(1.05, max(0.75, (gn[xx, yy][c] / gd[xx, yy]) / max(1e-3, rn[xx, yy][c] / rd[xx, yy]))) for c in range(3)]
            gains.append(sum(g) / 3)
            r, gg, b, al = jp[xx, yy]
            jp[xx, yy] = (min(255, int(r * g[0])), min(255, int(gg * g[1])), min(255, int(b * g[2])), al)
    # the packshot's dark base line (a studio edge shadow) reads as a hard grey crescent once the jar is held in hands: trim its last 4 px with a 3 px fade
    ap = j.getchannel("A").load()
    cols = {}
    for xx in range(j.width):
        for yy in range(j.height - 1, -1, -1):
            if ap[xx, yy] > 128:
                cols[xx] = yy
                break
    al = j.getchannel("A")
    alp = al.load()
    for xx, yb in cols.items():
        for k in range(7):
            yy = yb - k
            if yy >= 0:
                alp[xx, yy] = int(alp[xx, yy] * (0.0 if k < 4 else (k - 3) / 4))
    j.putalpha(al)
    plate = raw.convert("RGBA")
    plate.alpha_composite(j, (x, y))
    im = plate.convert("RGB").resize((FW, FH), Image.LANCZOS)
    im.save(RUN / "cover_nolettering_1080x1350.png")
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(str(RUN / "font/PlayfairDisplay.ttf"), 84)
    font.set_variation_by_name("Bold")
    small = ImageFont.truetype(str(RUN / "font/PlayfairDisplay.ttf"), 27)
    small.set_variation_by_name("Regular")
    d.text((78, 62), "Vaš ružičasti", font=font, fill=BURGUNDY)
    d.text((78, 148), "ritual.", font=font, fill=BURGUNDY)
    for i, t in enumerate(("Colla Pink: sve što", "treba znati u", "šest kadrova.")):
        d.text((82, 262 + i * 36), t, font=small, fill=BURGUNDY)
    im.save(RUN / out_name)
    print("saved", out_name, im.size, "gain mean %.3f min %.3f max %.3f" % (sum(gains) / len(gains), min(gains), max(gains)))


def reference():
    raw = Image.open(RUN / "cover_raw.png").convert("RGB")
    d = RUN / "model_reference"
    d.mkdir(exist_ok=True)
    raw.crop((350, 330, 1250, 1100)).save(d / "face_hair_light_crop.png")
    raw.crop((0, 800, GW, 1700)).resize((800, 450), Image.LANCZOS).save(d / "outfit_hands_crop.png")
    raw.resize((800, 1000), Image.LANCZOS).save(d / "full_cover_reference.png")
    (d / "README.md").write_text("Fictional model reference (AI-generated person; not a real or identifiable person; not any influencer).\n"
                                 "Source: cover_raw.png (gpt-image-2.5-sunburst, request id in the ledger). Use as the reference input for later Slide 5 edits.\n"
                                 "Identity preservation across images and videos is NOT guaranteed; drifting results are rejected.\n"
                                 "Prompt traits: shoulder-length chestnut hair in a low sleek bun, natural makeup, white fitted sports top and white zip-up training jacket, "
                                 "soft key light from the left with a pink bounce, blush and baby-pink seamless studio.\n", encoding="utf-8")
    print("reference crops saved in", d)


if __name__ == "__main__":
    {"prepare": prepare, "preflight": preflight, "generate": generate, "assemble": assemble, "reference": reference}[sys.argv[1]]()
