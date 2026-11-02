"""ONE authorised paid edit (Lara, 2026-10-28): reconstruct ONLY the glass and its local reflection. Run from the repository root:
    python plans/gymbeam_hr/art_direction/hero_proof/glass_edit.py prepare     # free: input canvas + tight mask + prompt
    python plans/gymbeam_hr/art_direction/hero_proof/glass_edit.py preflight   # free: cost guard dry run
    python plans/gymbeam_hr/art_direction/hero_proof/glass_edit.py generate    # PAID: exactly one request (ledger + budget guard, cap 4 = 3 used + this one)
    python plans/gymbeam_hr/art_direction/hero_proof/glass_edit.py assemble    # free: deterministic composite (real pouch back on top) + headline

The model may repaint ONLY the zone right of the pouch (E) and the strip under the pouch's right end (E_low, the old glass base). The pouch is pasted into
the input as the real relit pixels and is protected by the mask; after generation the real pouch pixels are laid back by code and the model's output is
used only inside E / E_low (feathered). The glass is asked to stand beside the pouch with a small gap, never over the printed area.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageChops, ImageDraw, ImageFilter  # noqa: E402

RUN = ROOT / "runs/hero-proof"


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


mh, h3 = load("make_hero"), load("hero_v3")
hv, rf = h3.hv, h3.rf
GW, GH = mh.GW, mh.GH
E_MAIN = (1331, 600, GW, GH)        # glass + its reflection, right of the pouch edge (x = 1329)
ASM_TOP = 470                        # assembly takes the model's pixels right of the pouch from this row down
E_LOW = (1215, 1572, 1331, GH)      # below the pouch: where the old glass base / reflection sat left of x = 1331
CANVAS, MASK, PROMPT_F, OUT = RUN / "glass_edit_canvas.png", RUN / "glass_edit_mask.png", RUN / "glass_edit_prompt.txt", RUN / "candidate_G.png"
PROMPT = (
    "The image shows a real product pouch standing on wet dark slate in a premium studio photograph. Treat everything outside the editable area as untouchable: "
    "do not change, move, redraw or restyle the pouch, the slate to its left, the background or the lighting, and never add text, letters, numbers, logos or labels anywhere. "
    "In the editable area on the right, paint ONE tall, slim, plain, label-free drinking glass of water covered in genuine fine condensation, standing on the same wet slate "
    "directly to the right of the pouch. Its left wall is about 20 pixels from the pouch's right edge, leaving a small dark gap, so the glass does NOT overlap the pouch "
    "at all; the glass is cut naturally by the right edge of the frame. Physically correct glass: the dark backdrop and the slate are seen through the water with subtle "
    "warm refraction, a single clean rim ellipse (no double rim), thin natural specular highlights on the left wall from the soft key light at the upper left and a faint "
    "warm hint of the narrow orange rim light, no white or orange outline halo. The glass casts a believable soft contact shadow on the slate and a soft, blurred, "
    "darkened reflection in the wet slate that continues the existing reflection of the pouch without a visible seam. Same warm color grade, grain and depth of field as the rest of the photograph.")


def old_glass_mask(gen, ref):
    g0, fit = rf.glass_edge_mask(gen, ref)
    edge = hv.refine_glass_edge(gen, fit)
    m, _ = h3.glass_object_mask(gen, edge)
    return m


def zero_glass(g, e, d):
    return g, Image.new("L", g.size, 0)


def prepare():
    gen = Image.open(RUN / "candidate_A.png").convert("RGB")
    ref = Image.open(RUN / "edit_canvas.png")
    _, _, hv.layer_org = hv.source_layer()
    gm = old_glass_mask(gen, ref)
    _, info = hv.build(50, "", glass_fn=zero_glass, gain_excl=gm)          # real pouch, relit, repaired, wrapped; alpha unmasked
    pouch = info["pouch"].resize((round(mh.PW * mh.K), round(mh.PH * mh.K)), Image.LANCZOS)
    base = gen.convert("RGBA")
    base.alpha_composite(pouch, (round(mh.PX * mh.K), round(mh.PY * mh.K)))
    base = base.convert("RGB")
    # hint for the editable zones: plain dark backdrop above the slate, blurred slate below (the model repaints these)
    fill = Image.new("RGB", (GW, GH), (17, 15, 15))
    left_slate = base.crop((150, 1250, 150 + 270, GH)).transpose(Image.FLIP_LEFT_RIGHT).filter(ImageFilter.GaussianBlur(18))
    fill.paste(left_slate, (E_MAIN[0], 1250))
    fill.paste(base.crop((1100, 1572, 1215, GH)).transpose(Image.FLIP_LEFT_RIGHT).filter(ImageFilter.GaussianBlur(10)), (1215, 1572))
    em = Image.new("L", (GW, GH), 0)
    d = ImageDraw.Draw(em)
    d.rectangle((E_MAIN[0], E_MAIN[1], GW, GH), fill=255)
    d.rectangle((E_LOW[0], E_LOW[1], E_LOW[2], GH), fill=255)
    canvas = Image.composite(fill, base, em)
    canvas.save(CANVAS)
    mask = Image.new("RGBA", (GW, GH), (0, 0, 0, 255))                    # alpha 255 = keep
    mask.putalpha(ImageChops.invert(em))                                   # alpha 0 = edit
    mask.save(MASK)
    PROMPT_F.write_text(PROMPT, encoding="utf-8")
    print("canvas", canvas.size, "editable zones", E_MAIN, E_LOW, "prompt chars", len(PROMPT))


def adapter():
    return mh.adapter()


def preflight():
    a = adapter()
    print(f"model {mh.MODEL}  size {mh.SIZE}  quality {mh.QUALITY}  requests so far {a.api_requests}/{mh.MAX_REQ}")
    w = a.worst_case_usd()
    print(f"guard worst case for ONE request {w:.4f} USD (assumption: {a.worst_in_tokens} image-in + {a.worst_out_tokens} image-out tokens); spent so far {a.spent_usd:.6f}; "
          f"spent + worst = {a.spent_usd + w:.4f} of the {mh.BUDGET:.2f} USD experiment cap; remaining {a.remaining_usd():.6f}")
    print(f"observed cost of the same size/quality request: {a.max_seen_usd:.6f} USD (4244 output tokens); expected for this edit: about 0.14-0.17 USD; key present: {bool(a.api_key)}")
    a.check_budget()
    print("guard: the request fits")


def generate():
    from studio.config import load_settings
    from studio.cost import CostEstimator
    from studio.ledger import Ledger, OperationRunner
    a = adapter()
    ledger = Ledger(RUN / "ledger.db")
    runner = OperationRunner(ledger, CostEstimator(load_settings(str(ROOT / "config.yaml"))), "hero-proof-1")

    def fn():
        r = a.edit(image=CANVAS.read_bytes(), mask=MASK.read_bytes(), prompt=PROMPT, size=mh.SIZE, quality=mh.QUALITY)
        OUT.write_bytes(r["png"])
        return {"file": OUT.name, "cost_usd": r["cost_usd"], "usage": r["usage"], "request_id": r["request_id"]}

    runner.estimator.check_budget(ledger.total_cost("hero-proof-1"), a.worst_case_usd())
    res = runner.run(node="hero_glass_edit", scope="G", provider=a.info, key=f"hero-proof-1/G-glass-edit/{mh.MODEL}/{mh.SIZE}/{mh.QUALITY}", fn=fn,
                     actual_cost=lambda r: r["cost_usd"])
    import json
    print(json.dumps({**res, "spent_usd": a.spent_usd, "remaining_usd": a.remaining_usd()}, indent=1))


def assemble():
    gen = Image.open(RUN / "candidate_A.png").convert("RGB")
    ref = Image.open(RUN / "edit_canvas.png")
    R = Image.open(OUT).convert("RGB")
    if R.size != (GW, GH):
        R = R.resize((GW, GH), Image.LANCZOS)
    m = Image.new("L", (GW, GH), 0)
    d = ImageDraw.Draw(m)
    for i in range(24):                                                    # feather 1296..1320 lies INSIDE the pouch footprint (edge at 1324-1329): the real pouch
        d.line((1296 + i, 0, 1296 + i, GH), fill=int(255 * (i + 1) / 24))  # covers it, so no pixel of the old glass survives beside the pouch
    d.rectangle((1320, 0, GW, GH), fill=255)
    vert = Image.new("L", (GW, GH), 255)                                   # the model drew the rim above the edit zone (y~530): take its pixels from y=470, feathered
    vd = ImageDraw.Draw(vert)
    vd.rectangle((0, 0, GW, ASM_TOP), fill=0)
    for i in range(30):
        vd.line((0, ASM_TOP + i, GW, ASM_TOP + i), fill=int(255 * (i + 1) / 30))
    m = ImageChops.multiply(m, vert)
    low = Image.new("L", (GW, GH), 0)
    ld = ImageDraw.Draw(low)
    for i in range(60):                                                    # wide feather for the slate reflection rows (no seam)
        ld.line((E_LOW[0] + i, E_LOW[1], E_LOW[0] + i, GH), fill=int(255 * (i + 1) / 60))
    ld.rectangle((E_LOW[0] + 60, E_LOW[1], GW, GH), fill=255)
    top = Image.new("L", (GW, GH), 0)
    ImageDraw.Draw(top).rectangle((0, E_LOW[1], GW, GH), fill=255)
    low = ImageChops.multiply(low, top)
    m = ImageChops.lighter(m, low)
    plate = Image.composite(R, gen, m)
    plate.save(RUN / "plate_G.png")
    gm = old_glass_mask(gen, ref)
    _, _, hv.layer_org = hv.source_layer()
    comp, info = hv.build(50, "", glass_fn=lambda g, e, dx: (plate, Image.new("L", g.size, 0)), gain_excl=gm)
    comp.save(RUN / "hero_v4_nolettering_1080x1350.png")
    hv.headline(comp.copy()).save(RUN / "hero_v4_glass_edit_1080x1350.png")
    print("saved hero_v4_glass_edit_1080x1350.png", comp.size)


if __name__ == "__main__":
    {"prepare": prepare, "preflight": preflight, "generate": generate, "assemble": assemble}[sys.argv[1]]()
