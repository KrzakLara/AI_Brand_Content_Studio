"""Slide 5 v2: ONE paid Kling v4 image-to-video request (approved 2026-10-29: 5 s, 1080p; total slide-5 budget 2.35 USD incl. the 1.175 already spent)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
for l in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if l.startswith("FAL_KEY="):
        KEY = l.split("=", 1)[1].strip().strip('"')

from studio.providers.fal_video import ENDPOINT, FalKlingVideo  # noqa: E402
from studio.tools.transport import UrllibTransport  # noqa: E402

OUT = ROOT / "runs/colla-pink/slide5_video"
PROMPT = (
    "Photorealistic luxury beauty-commercial video of the SAME woman as in the start image: identical face, skin tone, smile, long dark-brown "
    "hair, white sports bra and white leggings, same luminous baby-pink studio background and lighting. Completely locked-off static camera, "
    "no zoom, no pan, no push-in; the framing and the size of the woman stay exactly as in the start image. Very minimal, calm movement. "
    "She gently raises the tall glass of soft baby-pink drink with ice, brings the rim to her lips and takes one small, realistic sip, then "
    "lowers the glass slightly and smiles naturally. "
    "NO wind, NO fan effect, NO dramatic hair movement: her long brown hair hangs calmly and naturally over her shoulders and stays in place, "
    "moving only minimally with her head. Small, realistic movements only. Keep exactly one glass with correct geometry, natural fingers "
    "with five fingers, realistic hand contact, reflections and ice. The drink stays a soft pastel baby pink. No morphing of the face, "
    "no warped fingers, no duplicated glasses, no unnatural mouth animation. No text, no letters, no logos, no watermark anywhere."
)
v = FalKlingVideo(transport=UrllibTransport(), api_key=KEY, budget_usd=2.35, max_requests=2, usage_path=OUT / "fal_usage.jsonl")
assert v.api_requests == 1 and abs(v.spent_usd - 1.175) < 1e-6, (v.api_requests, v.spent_usd)   # exactly one earlier request on record
print("preflight ok, worst-case USD:", v.check_budget(5, "1080p"), "spent so far", v.spent_usd)
(OUT / "kling_prompt_v2.txt").write_text(PROMPT, encoding="utf-8")
res = v.generate_from_image(image=(OUT / "start_frame_hair_calmed_1080x1350.png").read_bytes(), prompt=PROMPT, duration_s=5, resolution="1080p")
(OUT / "kling_raw_v2.mp4").write_bytes(res["mp4"])
(OUT / "kling_request_v2.json").write_text(json.dumps({"endpoint": ENDPOINT, "request_id": res["request_id"], "cost_usd_estimated": res["cost_usd"],
                                                       "duration_s": 5, "resolution": "1080p", "bytes": len(res["mp4"])}, indent=1), encoding="utf-8")
print("done", res["request_id"], res["cost_usd"], len(res["mp4"]))
