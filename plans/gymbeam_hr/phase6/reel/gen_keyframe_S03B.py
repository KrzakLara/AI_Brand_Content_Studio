"""Post 3 - ONE replacement keyframe for the wafer-into-bag shot (paid image edit, reference-conditioned).
Authorised by the project lead: ONE keyframe, hard cap 0.15 USD, NO Kling, NO automatic retry.
Own usage log (api_usage_S03B.jsonl) and own request log; max 1 request; the S03 keyframe and every earlier file are left untouched.
usage: python gen_keyframe_S03B.py --preflight     (prints the guard, sends nothing)
       python gen_keyframe_S03B.py                 (sends exactly one request)"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
R = ROOT / "runs/gymbeam-wafer-reel"; REF = R / "references"; KF = R / "keyframes"; LOG = R / "logs"
MODEL, SIZE, QUALITY = "gpt-image-2.5-sunburst", "1152x2048", "xhigh"
BUDGET, MAX_REQ = 0.15, 1

COMMON = (
    "Photorealistic professional lifestyle commercial photograph for a premium fitness-snack campaign, shot on a full-frame camera, 50 mm lens, soft natural "
    "morning daylight from a large window, neutral cream, beige, white and black palette, shallow depth of field, fine film grain, realistic skin texture, "
    "vertical 9:16 composition. This must look like a real editorial photo, NOT a collage and NOT a product cutout: every object sits naturally in the scene with correct "
    "perspective, scale, contact shadows and reflections. The woman is the SAME fictional woman as in image 1 (same face, skin tone, long natural dark-brown hair). Her hair hangs "
    "calmly and naturally over her shoulders - NO wind, NO fan effect, no flyaway strands. She wears a fitted white sports top and cream leggings, no logos. Natural hands with exactly "
    "five fingers each. The GymBeam 32% Protein Wafer must look exactly like the reference wafer image: a flat chocolate-brown wrapper with the GymBeam logo, '32% PROTEIN WAFER', "
    "three green label pills, 'NET WT. 25g', same colours and layout, palm-sized. No other text anywhere, no other brand logos, no jar, no pink powder, no Colla Pink, no watermark. ")
TEXT = (
    "Image 1 shows the woman, outfit and kitchen to keep identical (same face, hair, clothes, counter, window light, warm kitchen background). Image 2 is the official black GymBeam duffle bag, "
    "whole bag. Image 3 is an official close-up showing how the handle is attached. Image 4 is the sealed wafer pack. "
    "Show ONE black GymBeam duffle bag standing on the kitchen counter, clearly UNZIPPED AND OPEN along the top (the dark lining is visible inside the opening), its rectangular GymBeam logo patch and "
    "small tag facing the camera, seen from the front at a slightly raised three-quarter angle, exactly the bag of images 2 and 3. "
    "THE BAG HANDLES ARE THE TOP PRIORITY. The bag has exactly two rolled black leather handles, one on the front side and one on the back side. BOTH ARE LOWERED: each handle lies relaxed and folded down "
    "against the bag's body (the front one leaning down toward the camera onto the upper front of the bag, above the logo patch and never covering it; the back one leaning down away from the camera, partly hidden behind the bag). "
    "NOT standing upright, NOT arched into the air. Each handle is one complete continuous loop whose BOTH ends are firmly attached to their own two metal rings on the two vertical straps, exactly like the official "
    "close-up in image 3, so both ends of each handle are visible and physically connected to the bag. NOTHING touches the handles: no hand holds, lifts, pulls or grips any handle. "
    "No shoulder strap, no chain, no chain links, no loose straps, no duplicated handles, no floating or merged parts anywhere. "
    "The woman stands behind the bag, waist-up, three-quarter view, looking down at the bag with a soft smile. Her hand on the left side of the picture holds the sealed GymBeam wafer pack above the open top of the bag, "
    "about to lower it inside, the pack front facing the camera and fully legible. Her other hand rests lightly on the top edge of the bag's opening, fingers natural, not touching any handle. Exactly five fingers on each hand.")
REFS = [R / "keyframes/S02_raw.png", REF / "bag_1.jpg", REF / "bag_5.jpg", REF / "wafer_view1.jpg"]


def adapter():
    from studio.providers.live import OpenAIImageEdit
    from studio.tools.transport import GuardedTransport, UrllibTransport
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():     # key goes into the process env only, never printed or logged
        if line.startswith("OPENAI_API_KEY="):
            os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
    t = GuardedTransport(UrllibTransport(), limit=MAX_REQ, hosts=("api.openai.com",), log_path=LOG / "api_requests_S03B.log")
    a = OpenAIImageEdit(MODEL, t, budget_usd=BUDGET, max_requests=MAX_REQ, usage_path=LOG / "api_usage_S03B.jsonl")
    # observed: 4 reference images -> ~4.4k input tokens, 2511 output tokens at 1152x2048 xhigh (earlier calls); assumed worst case with margin
    a.worst_in_tokens, a.worst_out_tokens = 6000, 2800
    return a


if __name__ == "__main__":
    a = adapter()
    print(f"S03B: requests so far {a.api_requests}/{MAX_REQ}; spent {a.spent_usd:.4f}; worst case one request {a.worst_case_usd():.4f}; cap {BUDGET}; key present {bool(a.api_key)}")
    a.check_budget()
    for p in REFS:
        assert p.is_file(), p
    prompt = COMMON + TEXT
    (R / "prompts" / "S03B_prompt_SENT.txt").write_text(prompt, encoding="utf-8")
    if "--preflight" in sys.argv:
        print("preflight OK, nothing sent; refs:", [p.name for p in REFS], "prompt chars:", len(prompt))
        sys.exit(0)
    r = a.edit(image=REFS[0].read_bytes(), mask=None, prompt=prompt, size=SIZE, quality=QUALITY, extra_images=tuple(p.read_bytes() for p in REFS[1:]))
    (KF / "S03B_raw.png").write_bytes(r["png"])
    from PIL import Image
    Image.open(KF / "S03B_raw.png").convert("RGB").resize((1080, 1920), Image.LANCZOS).save(KF / "S03B_keyframe_1080x1920.png")
    print(json.dumps({"shot": "S03B", "request_id": r["request_id"], "cost_usd": r["cost_usd"], "usage": r["usage"], "spent_total": a.spent_usd, "remaining": round(BUDGET - a.spent_usd, 6)}))
