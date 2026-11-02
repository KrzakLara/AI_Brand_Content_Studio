"""ONE paid Kling v4 image-to-video request for Slide 3 (approved 2026-10-29: 5 s, 1080p, max 2.00 USD, no retries)."""
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

OUT = ROOT / "runs/colla-pink/slide3_video"
PROMPT = (
    "Photorealistic luxury beauty-commercial macro video, static locked-off camera, no camera movement. Fine pale pink collagen powder "
    "keeps pouring from the white scoop into the tall clear glass of cold water with ice on a glossy baby-pink surface. After a moment "
    "the scoop tilts back and exits the frame at the top right. Then a polished metallic silver spoon enters the glass from the upper "
    "right and gently stirs the drink in smooth circles; the powder swirls and dissolves. The water gradually turns into a smooth, "
    "uniform, translucent baby-pink drink with ice cubes and tiny bubbles. Soft light reflections glide over the glossy surface and "
    "glass. Realistic liquid physics. Glass, background, lighting and framing stay identical throughout. Clean premium feminine "
    "wellness aesthetic. No people, no hands, no jar, no packaging. No text, no letters, no logos, no watermark anywhere in the frame."
)
v = FalKlingVideo(transport=UrllibTransport(), api_key=KEY, budget_usd=2.0, max_requests=1, usage_path=OUT / "fal_usage.jsonl")
print("preflight ok, worst-case USD:", v.check_budget(5, "1080p"))
(OUT / "kling_prompt.txt").write_text(PROMPT, encoding="utf-8")
res = v.generate_from_image(image=(OUT / "start_frame_clean_1080x1350.png").read_bytes(), prompt=PROMPT, duration_s=5, resolution="1080p")
(OUT / "kling_raw.mp4").write_bytes(res["mp4"])
(OUT / "kling_request.json").write_text(json.dumps({"endpoint": ENDPOINT, "request_id": res["request_id"], "cost_usd": res["cost_usd"],
                                                    "duration_s": 5, "resolution": "1080p", "bytes": len(res["mp4"])}, indent=1), encoding="utf-8")
print("done", res["request_id"], res["cost_usd"], len(res["mp4"]))
