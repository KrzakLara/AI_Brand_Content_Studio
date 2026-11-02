"""ONE paid Kling v4 image-to-video request for Slide 5 (approved 2026-10-29: 5 s, 1080p, max 2.00 USD, no retries)."""
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
    "hair, white sports bra and white leggings, same luminous baby-pink studio background and lighting. Locked-off camera, no camera movement, "
    "or at most an almost imperceptible slow push-in. She smiles naturally and gently raises the tall glass of soft baby-pink drink with ice, "
    "brings the rim to her lips and takes one small, realistic sip, then lowers the glass slightly and smiles contentedly, enjoying a calm "
    "beauty ritual. Subtle natural movement of hair. Keep exactly one glass with correct glass geometry, natural fingers with five fingers on "
    "the hand, realistic hand contact, glass reflections and ice. The drink stays a soft pastel baby pink. No exaggerated movement, no morphing "
    "of the face, no warped fingers, no duplicated glasses, no unnatural mouth animation. No text, no letters, no logos, no watermark anywhere."
)
v = FalKlingVideo(transport=UrllibTransport(), api_key=KEY, budget_usd=2.0, max_requests=1, usage_path=OUT / "fal_usage.jsonl")
print("preflight ok, worst-case USD:", v.check_budget(5, "1080p"))
(OUT / "kling_prompt.txt").write_text(PROMPT, encoding="utf-8")
res = v.generate_from_image(image=(OUT / "start_frame_clean_1080x1350.png").read_bytes(), prompt=PROMPT, duration_s=5, resolution="1080p")
(OUT / "kling_raw.mp4").write_bytes(res["mp4"])
(OUT / "kling_request.json").write_text(json.dumps({"endpoint": ENDPOINT, "request_id": res["request_id"], "cost_usd": res["cost_usd"],
                                                    "duration_s": 5, "resolution": "1080p", "bytes": len(res["mp4"])}, indent=1), encoding="utf-8")
print("done", res["request_id"], res["cost_usd"], len(res["mp4"]))
