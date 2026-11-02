"""Hero proof pipeline (one 1080x1350 PNG per candidate). Run from the repository root:

    python plans/gymbeam_hr/art_direction/hero_proof/make_hero.py prepare        # free: canvas + mask + prompts
    python plans/gymbeam_hr/art_direction/hero_proof/make_hero.py preflight      # free: cost guard dry run
    python plans/gymbeam_hr/art_direction/hero_proof/make_hero.py generate A|B   # PAID (one request each, ledger + budget guard)
    python plans/gymbeam_hr/art_direction/hero_proof/make_hero.py composite A|B  # free: real pouch pixels back on top + headline
    python plans/gymbeam_hr/art_direction/hero_proof/make_hero.py compare        # free: side by side of the two real results

The model only paints the world AROUND the fixed pouch (mask-based edit); the real cut-out pixels are laid back on top by code.
Generated pouch pixels are always discarded. Outputs live in runs/hero-proof/ (git-ignored: brand-owned imagery is not published).
"""
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont  # noqa: E402

RUN = ROOT / "runs/hero-proof"
CUT = RUN / "pouch_layer_official_photo.png"
MODEL, SIZE, QUALITY = "gpt-image-2.5-sunburst", "1600x2000", "xhigh"
FW, FH = 1080, 1350                      # final
GW, GH = 1600, 2000                      # generation canvas (4:5, multiples of 16, 3.2 MP: below the 'experimental' 3.7 MP line)
K = GW / FW
PW, PH, PX, PY = 513, 810, 384, 250      # pouch in the FINAL frame (height 60%, bottom at y=1060, scale 0.868 of the source: downscale only)
STRIP = (1236, 520, 1330, 930)           # generation coords: the right-seal strip the model may repaint (the glass goes there)
BUDGET, MAX_REQ = 2.5, 4   # experiment cap 2.50 USD; 4 requests total = failed 401 + failed 429 + 1 paid hero image + ONE authorised glass edit (raised 3 -> 4 by Lara, 2026-10-28)

COMMON = ("The image shows a real product pouch already standing in place on a plain backdrop. Treat the pouch as untouchable: do not move, resize, "
          "rotate, recolor, redraw, restyle or add anything to it, and never add any text, letters, numbers, logos or labels anywhere in the scene. "
          "Paint the world around it so that it looks like one real photograph taken with a professional camera. ")
GLASS = ("A tall, plain, label-free drinking glass of water covered in genuine fine condensation stands in the right foreground, slightly in front of "
         "the pouch: its left side overlaps the right edge of the pouch by about 80 pixels, it rises from the same surface to about the height of the "
         "pouch's zip seal (roughly 85-90% of the pouch height) and is clearly in focus enough to read as glass. The glass and the pouch both touch the "
         "surface and cast believable contact shadows. The pouch's soft, darkened, blurred reflection in the wet surface must contain no readable text. "
         "Leave the upper-left quarter of the frame calm and empty. Photorealistic 85 mm commercial product photograph, f/4, fine film grain, "
         "real material textures, no plastic look, no neon, no steam, no extra objects.")
PROMPTS = {
    "A": COMMON + ("Dark luxury studio: a wet, dark honed slate slab fills the lower fifth of the frame with a thin film of water, tiny droplets and a "
                   "few condensation runs; warm charcoal and graphite backdrop with a soft natural gradient; one large soft key light from the upper "
                   "left with deep controlled shadows to the right, and only a narrow, subtle warm orange rim light on the far-left background edge "
                   "(no flat orange glow). ") + GLASS,
    "B": COMMON + ("Natural cinematic studio: honed natural stone (pale warm travertine, darker where it is wet) with a thin film of water and "
                   "droplets in the lower fifth; warm natural window light entering from the upper left as a soft shaft with gentle atmospheric "
                   "haze; muted warm grey-beige backdrop falling off to charcoal at the corners; subtle warm highlights, soft long shadows to the "
                   "right, editorial depth of field. ") + GLASS,
}


def pouch_final():
    c = Image.open(CUT).convert("RGBA")
    return c.resize((PW, PH), Image.LANCZOS)


def prepare():
    c = Image.open(CUT).convert("RGBA")
    pw, ph, px, py = round(PW * K), round(PH * K), round(PX * K), round(PY * K)
    p = c.resize((pw, ph), Image.LANCZOS)                       # reference only: the model sees it, the final uses the real pixels at 0.868
    bgc = Image.linear_gradient("L").resize((GW, GH))
    canvas = Image.composite(Image.new("RGB", (GW, GH), (24, 22, 22)), Image.new("RGB", (GW, GH), (52, 47, 45)), bgc).convert("RGBA")
    canvas.alpha_composite(p, (px, py))
    keep = Image.new("L", (GW, GH), 0)
    keep.paste(p.getchannel("A").point(lambda v: 255 if v > 200 else 0), (px, py))
    ImageDraw.Draw(keep).rectangle(STRIP, fill=0)                  # strip repaintable: the glass overlaps it
    keep = keep.filter(ImageFilter.MinFilter(3))                   # keep the protected area 1 px inside the pouch edge
    mask = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))               # alpha 0 = edit, 255 = keep (OpenAI mask convention)
    mask.putalpha(keep)
    canvas.convert("RGB").save(RUN / "edit_canvas.png")
    mask.save(RUN / "edit_mask.png")
    (RUN / "prompt_A.txt").write_text(PROMPTS["A"], encoding="utf-8")
    (RUN / "prompt_B.txt").write_text(PROMPTS["B"], encoding="utf-8")
    print("canvas", canvas.size, "pouch", (pw, ph), "at", (px, py), "strip", STRIP)


def adapter():
    from studio.cli import load_dotenv
    from studio.providers.live import OpenAIImageEdit
    from studio.tools.transport import GuardedTransport, UrllibTransport
    load_dotenv(ROOT / ".env")
    t = GuardedTransport(UrllibTransport(), limit=MAX_REQ, hosts=("api.openai.com",), log_path=RUN / "api_requests.log")
    return OpenAIImageEdit(MODEL, t, budget_usd=BUDGET, max_requests=MAX_REQ, usage_path=RUN / "api_usage.jsonl")


def preflight():
    a = adapter()
    img, msk = (RUN / "edit_canvas.png").stat().st_size, (RUN / "edit_mask.png").stat().st_size
    print(f"model {MODEL}  size {SIZE}  quality {QUALITY}  requests so far {a.api_requests}/{MAX_REQ}")
    print(f"worst case per request {a.worst_case_usd():.4f} USD (assumes {a.worst_in_tokens} image-in + {a.worst_out_tokens} image-out tokens); "
          f"two requests {2 * a.worst_case_usd():.4f} USD of {BUDGET:.2f}; spent {a.spent_usd:.4f}")
    print("upload sizes:", img, msk, "bytes; key present:", bool(a.api_key))
    a.check_budget()
    print("guard: first request fits")


def generate(tag):
    from studio.config import load_settings
    from studio.cost import CostEstimator
    from studio.ledger import Ledger, OperationRunner
    a = adapter()
    settings = load_settings(str(ROOT / "config.yaml"))
    ledger = Ledger(RUN / "ledger.db")
    runner = OperationRunner(ledger, CostEstimator(settings), "hero-proof-1")
    prompt = PROMPTS[tag]

    def fn():
        r = a.edit(image=(RUN / "edit_canvas.png").read_bytes(), mask=(RUN / "edit_mask.png").read_bytes(), prompt=prompt, size=SIZE, quality=QUALITY)
        (RUN / f"candidate_{tag}.png").write_bytes(r["png"])
        return {"file": f"candidate_{tag}.png", "cost_usd": r["cost_usd"], "usage": r["usage"], "request_id": r["request_id"]}

    runner.estimator.check_budget(ledger.total_cost("hero-proof-1"), a.worst_case_usd())  # ledger-level guard before the adapter's own
    res = runner.run(node=f"hero_candidate_{tag}", scope=tag, provider=a.info, key=f"hero-proof-1/{tag}/{MODEL}/{SIZE}/{QUALITY}", fn=fn,
                     actual_cost=lambda r: r["cost_usd"])
    print(json.dumps({**res, "spent_usd": a.spent_usd, "remaining_usd": a.remaining_usd()}, indent=1))


ZONES = [(1290, 540, 1340, 650),     # the black shaker handle sits here on the real seal: replaced by the model's plain seal texture (disclosed)
         (1200, 650, 1340, 1580)]    # the glass in front of the pouch, from its rim down (the model drew it wherever it overlaps)


def glass_mask(gen: Image.Image, ref: Image.Image) -> Image.Image:
    """Pixels inside ZONES that the model really changed AND that connect to the area right of the pouch = glass (or the plain seal fill)."""
    m = Image.new("L", (GW, GH), 0)
    mp = m.load()
    for zone in ZONES:
        x0, y0, x1, y1 = zone
        d = ImageChops.difference(gen.convert("RGB").crop(zone), ref.convert("RGB").crop(zone)).convert("L").point(lambda v: 255 if v > 28 else 0)
        d = d.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(3))
        w, h = d.size
        px = d.load()
        seen, stack = set(), [(w - 1, y) for y in range(h) if px[w - 1, y]]   # right column = outside the pouch
        while stack:
            x, y = stack.pop()
            if (x, y) in seen or not (0 <= x < w and 0 <= y < h) or not px[x, y]:
                continue
            seen.add((x, y))
            stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        for x, y in seen:
            mp[x0 + x, y0 + y] = 255
    return m


def composite(tag):
    gen = Image.open(RUN / f"candidate_{tag}.png").convert("RGB")
    if gen.size != (GW, GH):
        gen = gen.resize((GW, GH), Image.LANCZOS)
    ref = Image.open(RUN / "edit_canvas.png")
    gm = glass_mask(gen, ref)
    gm.save(RUN / f"glass_mask_{tag}.png")
    base = gen.resize((FW, FH), Image.LANCZOS).convert("RGBA")
    pouch = pouch_final()
    glass = gm.resize((FW, FH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.0)).crop((PX, PY, PX + PW, PY + PH))
    a = ImageChops.multiply(pouch.getchannel("A").filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6)),  # 1 px in: no pale backdrop fringe
                            ImageChops.invert(glass))
    pouch.putalpha(a)
    base.alpha_composite(pouch, (PX, PY))
    d = ImageDraw.Draw(base)
    f = ImageFont.truetype(str(RUN / "font/extras/ttf/Inter-Bold.ttf"), 100)
    d.text((90, 120), "Samo", font=f, fill=(242, 237, 232))
    d.text((90, 224), "bitno.", font=f, fill=(242, 237, 232))
    w = d.textlength("bitno", font=f)
    d.rectangle((92, 340, 92 + int(w), 347), fill=(255, 140, 50))
    out = RUN / f"hero_{tag}_1080x1350.png"
    base.convert("RGB").save(out)
    print(out, base.size, "glass px (final scale):", sum(1 for v in glass.getdata() if v > 128))


def compare():
    a, b = (Image.open(RUN / f"hero_{t}_1080x1350.png") for t in "AB")
    s = Image.new("RGB", (FW * 2 + 40, FH), (18, 16, 16))
    s.paste(a, (0, 0))
    s.paste(b, (FW + 40, 0))
    s.save(RUN / "hero_A_vs_B.png")
    print(RUN / "hero_A_vs_B.png")


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"prepare": prepare, "preflight": preflight, "compare": compare}.get(cmd, lambda: {"generate": generate, "composite": composite}[cmd](sys.argv[2]))()
