"""Post 3 keyframes (paid image edit, reference-conditioned). ONE request per call, no retries.
Hard limits: 2.00 USD image budget for this stage, 4 requests in total (GuardedTransport + adapter), own usage log and ledger.
usage: python gen_keyframe.py S01|S02|S03|S06   (add --preflight to print the guard without sending)"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
R = ROOT / "runs/gymbeam-wafer-reel"; REF = R / "references"; KF = R / "keyframes"; LOG = R / "logs"
MODEL, SIZE, QUALITY = "gpt-image-2.5-sunburst", "1152x2048", "xhigh"     # 9:16 exactly; downscaled by 1.0667 to 1080x1920
BUDGET, MAX_REQ = 2.00, 15      # 5 done + 8 planned + 2 retake slots; total project cap 4.50 USD is enforced separately before every Kling call

COMMON = (
    "Photorealistic professional lifestyle commercial photograph for a premium fitness-snack campaign, shot on a full-frame camera, 50 mm lens, soft natural "
    "morning daylight from a large window, neutral cream, beige, white and black palette, shallow depth of field, fine film grain, realistic skin texture, "
    "vertical 9:16 composition. This must look like a real editorial photo, NOT a collage and NOT a product cutout: every object sits naturally in the scene with correct "
    "perspective, scale, contact shadows and reflections. The woman is the SAME fictional woman as in the identity reference images (same face, skin tone, long natural "
    "dark-brown hair). Her hair hangs calmly and naturally over her shoulders - NO wind, NO fan effect, no flyaway strands. She wears a fitted white sports top and cream "
    "leggings, no logos. Natural hands with exactly five fingers each. The GymBeam 32% Protein Wafer must look exactly like the reference wafer image: a flat chocolate-brown "
    "wrapper with the GymBeam logo, '32% PROTEIN WAFER', three green label pills, 'NET WT. 25g', same colours and layout, palm-sized. The black duffle bag must look exactly "
    "like the reference bag photos: black grained leather-look barrel bag, two rolled handles, rectangular GymBeam logo patch on the front, small tag on the handle ring. "
    "No other text anywhere, no other brand logos, no jar, no pink powder, no Colla Pink, no watermark. ")
COMMON_GYM = (
    "Photorealistic professional lifestyle commercial photograph for a premium fitness campaign, shot on a full-frame camera, 35 mm lens, warm natural daylight, neutral architectural "
    "colours (white, concrete grey, black, warm wood), shallow depth of field, fine film grain, realistic skin texture, vertical 9:16 composition. It must look like a real editorial photo, "
    "not a stock image and not a collage: correct perspective, glass reflections, contact shadows. The woman is the SAME fictional woman as in the reference images (same face, skin tone, "
    "same long natural dark-brown hair hanging calmly over her shoulders - NO wind, NO fan effect, no flyaway strands) wearing exactly the same outfit as image 1: fitted white sports top and "
    "cream leggings, no logos. Natural hands with exactly five fingers each. The black duffle bag must look exactly like the reference bag photos: black grained leather-look barrel bag, two "
    "rolled handles, rectangular GymBeam logo patch on the front, small tag on the handle ring - one bag only, correctly held, not floating. No invented gym branding, no signs with text, "
    "no other logos, no jar, no pink powder, no Colla Pink, no watermark. ")
COMMON_PROD = (
    "Photorealistic premium commercial product photograph for a fitness-snack campaign, full-frame camera, 85 mm lens, soft natural morning daylight from a window, neutral cream, beige, "
    "white and black palette, shallow depth of field, fine film grain, vertical 9:16 composition. A real editorial photo, not a collage or cutout: correct perspective, contact shadows, "
    "reflections. The GymBeam 32% Protein Wafer pack must look exactly like the reference: flat chocolate-brown wrapper, GymBeam logo, '32% PROTEIN WAFER', three green label pills, "
    "'NET WT. 25g'. The black duffle bag must look exactly like the bag reference: black grained leather-look barrel bag, GymBeam logo patch. No other text, no other logos, no watermark. ")
SHOTS = {
 "S01": dict(refs=["wafer_view1.jpg"], base=None,
   text="Image 1 is the product reference (ignore its white background). Create a beautiful kitchen scene: the real GymBeam wafer pack lying on a cream stone kitchen counter, wrapper facing the camera and fully legible, "
        "a set of car keys and a minimalist white ceramic coffee cup beside it, bright morning window light, softly blurred white cabinets and warm wood in the background, camera slightly above counter height. No people."),
 "S02": dict(refs=["wafer_view1.jpg", "identity_head_slide5.png", "identity_face_cover.png"], base="S01",
   text="Image 1 is the kitchen reference: keep the same kitchen, counter, light, coffee cup and keys. Image 2 is the wafer reference. Images 3 and 4 show the woman's identity (face only; ignore their backgrounds). "
        "Show her standing at the counter, waist-up, three-quarter view, a soft natural smile, looking down at the wafer as her hand naturally lifts the GymBeam wafer pack off the counter. Pack front clearly visible."),
 "S03": dict(refs=["bag_1.jpg", "bag_4.jpg", "wafer_view1.jpg"], base="S02",
   text="Image 1 shows the woman, outfit and kitchen to keep identical (same face, hair, clothes, counter, light). Images 2 and 3 are the black GymBeam duffle bag references. Image 4 is the wafer pack. "
        "Show the black duffle bag standing open on the kitchen counter with its GymBeam logo patch facing the camera; she is placing the wafer pack into the bag's open top with one hand while the other holds a handle, "
        "looking down at the bag, three-quarter view, waist-up."),
 "S08": dict(refs=["bag_1.jpg", "bag_4.jpg", "identity_head_slide5.png", "identity_face_cover.png"], base="S03", common="gym",
   text="Image 1 shows the woman and outfit to keep identical. Images 2 and 3 are the black GymBeam duffle bag references; images 4 and 5 are face identity references. "
        "Medium-wide cinematic shot from behind and slightly to the side: she walks up to the large glass entrance doors of a beautiful modern gym, carrying the black GymBeam duffle bag in one hand "
        "(the bag logo patch visible and accurate), her other hand reaching for and pushing the glass door handle. Her face is partly visible in profile, glancing toward the door. The premium modern gym interior "
        "(weights area, warm wood and concrete, soft light) is visible through the glass; slight reflections on the glass. No text on the doors or walls."),
 "S02a": dict(refs=["wafer_view1.jpg", "identity_head_slide5.png", "identity_face_cover.png"], base="S02",
   text="Image 1 is the exact scene to keep: same kitchen, same camera and framing, same light, coffee cup, keys, black bag on the right, same woman, outfit and calm hair. Image 2 is the wafer pack reference; images 3 and 4 the woman's identity. "
        "Change ONLY the action: the GymBeam wafer pack now lies flat on the counter in front of her at the lower left, front legible, and she looks down at it with a soft smile while her hand (the one on the left side of the picture) reaches down toward it, fingers about to touch the pack. Her other hand rests on the counter."),
 "S06a": dict(refs=["wafer_view1.jpg", "bag_1.jpg"], base="S06",
   text="Image 1 is the exact scene to keep: same parked car interior, same camera and framing, same woman, outfit and calm hair, black bag unzipped on the passenger seat. Image 2 is the wafer pack, image 3 the bag. "
        "Change ONLY the action: the wafer pack is intact and fully sealed (no opening, no wafer visible); she holds it with both hands at chest height, front legible to camera, looking at it with a soft smile."),
 "S05": dict(refs=["bag_1.jpg"], base="S06",
   text="Image 1 is the scene to keep: same parked car interior, framing style, light, same woman, outfit and calm hair. Image 2 is the black bag. Show her sitting relaxed in the driver's seat of the PARKED car (engine off), hands resting on her lap, "
        "looking out through the windshield with a calm content smile; the black GymBeam duffle bag is zipped closed on the passenger seat beside her with its logo patch visible. No wafer pack visible, no phone, not driving."),
 "S04": dict(refs=["bag_1.jpg", "bag_4.jpg", "identity_head_slide5.png"], base="S08",
   text="Image 1 shows the woman, outfit and hair to keep identical (ignore its location). Images 2 and 3 are the black GymBeam duffle bag; image 4 is face identity. No wafer pack and no food anywhere in the picture; her free hand swings relaxed holding only a car key fob. Show her strolling along a sunny quiet sidewalk next to a parked light-grey SUV, "
        "relaxed and happy, full-length shot, she carries the black duffle bag by its handles in one hand, a soft natural smile, looking ahead, hair hanging calmly with no wind. The bag's logo patch is visible and accurate. Soft morning light, blurred trees behind."),
 "S07a": dict(refs=["wafer_view1.jpg", "wafer_view2.jpg"], base="S06",
   text="Image 1 is context (parked car interior, the woman's skin tone); images 2 and 3 show the GymBeam wafer (the illustration on the wrapper shows its layered wafer and hazelnut pieces). Extreme macro close-up, only her two hands visible (natural skin, "
        "exactly five fingers each, soft pink nail polish): the fingertips hold an intact unwrapped layered wafer bar with a milk-chocolate coating about 9 cm long, held horizontally between both hands, centred in frame; the cream car interior is softly blurred behind. No wrapper, no face."),
 "S07b": dict(refs=["wafer_view1.jpg", "wafer_view2.jpg"], base="S07a",
   text="Image 1 is the exact macro frame to keep: same camera, framing, hands, nails and blurred car background. Images 2 and 3 are wafer references. Change ONLY the wafer: it is now snapped cleanly in two halves, one half in each hand, "
        "each showing the cross-section with three crisp golden wafer layers, milk and chocolate-nougat filling and hazelnut pieces under the chocolate coating, a few fine crumbs. Fingers natural, no deformation, no melting."),
 "S08b": dict(refs=["bag_1.jpg", "bag_4.jpg", "identity_head_slide5.png"], base="S08", common="gym",
   text="Image 1 is the exact scene to keep: same camera position and framing, same glass facade, same lobby, same light. Images 2 and 3 are the bag; image 4 is face identity. Change ONLY her position: the glass door is now open and she has walked through it; "
        "she is now inside the gym entrance a few steps beyond the door, smaller in the frame, seen from behind and slightly to the side, still carrying the black GymBeam duffle bag in one hand, hair calm, one step mid-stride; the open glass door is visible beside her. No text anywhere."),
 "S09": dict(refs=["wafer_view1.jpg", "bag_1.jpg", "S07b_raw.png"], base="S01", common="prod",
   text="Image 1 is the kitchen counter mood to keep (cream stone counter, window light, shallow depth of field). Image 2 is the wafer pack, image 3 the black bag, image 4 the broken wafer halves. Hero product frame: the GymBeam wafer pack standing slightly angled "
        "on the counter, one broken wafer half lying in front of it showing the layers, the black duffle bag softly out of focus behind, generous clean empty space in the upper third of the frame for text. Cinematic, premium, no people."),
 "S06": dict(refs=["bag_1.jpg", "wafer_view1.jpg"], base="S03",
   text="Image 1 shows the woman and outfit to keep identical (same face, hair, clothes). Images 2 and 3 are the black GymBeam duffle bag and the wafer pack. Show the inside of a PARKED car, engine off, light cream/beige upholstery, "
        "soft daylight through the windshield. She sits in the driver's seat, relaxed, holding the GymBeam wafer pack in one hand with the wrapper just beginning to open, the black duffle bag unzipped on the passenger seat beside her. "
        "Hands are not on the wheel, no phone, no driving. Three-quarter view, waist-up, calm hair."),
}


def adapter():
    import os
    from studio.providers.live import OpenAIImageEdit
    from studio.tools.transport import GuardedTransport, UrllibTransport
    for line in ((ROOT / ".env").read_text(encoding="utf-8").splitlines() if (ROOT / ".env").is_file() else []):     # 7D: tolerate a missing .env; key goes into the process env only, never printed or logged
        if line.startswith("OPENAI_API_KEY="):
            os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
    t = GuardedTransport(UrllibTransport(), limit=MAX_REQ, hosts=("api.openai.com",), log_path=LOG / "api_requests.log")
    a = OpenAIImageEdit(MODEL, t, budget_usd=BUDGET, max_requests=MAX_REQ, usage_path=LOG / "api_usage.jsonl")
    a.worst_in_tokens, a.worst_out_tokens = 20000, 8000
    return a


if __name__ == "__main__":
    shot = sys.argv[1]; sp = SHOTS[shot]; a = adapter()
    LOG.mkdir(exist_ok=True); KF.mkdir(exist_ok=True)
    print(f"{shot}: requests so far {a.api_requests}/{MAX_REQ}; spent {a.spent_usd:.4f}; worst case one request {a.worst_case_usd():.4f}; budget {BUDGET}; key present {bool(a.api_key)}")
    a.check_budget()
    if "--preflight" in sys.argv:
        sys.exit(0)
    from studio.config import load_settings
    from studio.cost import CostEstimator
    from studio.ledger import Ledger, OperationRunner
    first = (KF / f"{sp['base']}_raw.png") if sp["base"] else (REF / sp["refs"][0])
    rest = [(KF / p if p.endswith("_raw.png") else REF / p) for p in (sp["refs"][1:] if not sp["base"] else sp["refs"])]
    prompt = {"gym": COMMON_GYM, "prod": COMMON_PROD}.get(sp.get("common"), COMMON) + sp["text"]
    (R / "prompts" / f"{shot}_prompt_SENT.txt").write_text(prompt, encoding="utf-8")
    runner = OperationRunner(Ledger(LOG / "ledger.db"), CostEstimator(load_settings(str(ROOT / "config.yaml"))), "post3-keyframes")

    def fn():
        r = a.edit(image=first.read_bytes(), mask=None, prompt=prompt, size=SIZE, quality=QUALITY, extra_images=tuple(p.read_bytes() for p in rest))
        (KF / f"{shot}_raw.png").write_bytes(r["png"])
        return {"file": f"{shot}_raw.png", "cost_usd": r["cost_usd"], "usage": r["usage"], "request_id": r["request_id"]}

    res = runner.run(node=f"keyframe_{shot}", scope=shot, provider=a.info, key=f"post3-keyframes/{shot}/{MODEL}/{SIZE}/{QUALITY}" + os.environ.get("ATTEMPT", ""), fn=fn, actual_cost=lambda r: r["cost_usd"])
    from PIL import Image
    Image.open(KF / f"{shot}_raw.png").convert("RGB").resize((1080, 1920), Image.LANCZOS).save(KF / f"{shot}_keyframe_1080x1920.png")
    print(json.dumps({"shot": shot, "request_id": res["request_id"], "cost_usd": res["cost_usd"], "usage": res["usage"], "spent_total": a.spent_usd, "remaining": round(BUDGET - a.spent_usd, 6)}))
