"""Post 3: ONE paid Kling v4 image-to-video request per call (3 s, 1080p, optional end frame). No retries.
Total project cap 4.50 USD = image spend (api_usage.jsonl) + Kling spend (fal_usage.jsonl); the adapter budget is cap - image spend.
usage: python run_kling.py S02|S03|S06|S08 [--preflight]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
R = ROOT / "runs/gymbeam-wafer-reel"; KF = R / "keyframes"; LOG = R / "logs"; VC = R / "video_clips"
CAP = 4.50
NOWIND = ("Her long dark-brown hair hangs naturally and stays in place: no wind, no fan, no dramatic hair movement, only minimal movement from her head. Natural, calm, realistic "
          "movement, correct hand anatomy with five fingers, no morphing of the face, no duplicated objects, no distorted logos. Locked-off camera: no zoom, no pan, no camera shake. Photorealistic.")
CLIPS = {
 "S02": dict(start="S02a_keyframe_1080x1920.png", end="S02_keyframe_1080x1920.png",
   prompt="In a bright modern kitchen the woman naturally picks up the GymBeam wafer pack from the counter and lifts it up in front of her, smiling softly and looking at it. The wafer pack keeps exactly its design, colours and logo. "
          "The coffee cup, keys and the black bag stay unchanged. " + NOWIND),
 "S03": dict(start="S03_keyframe_1080x1920.png", end=None,
   prompt="The woman slides the GymBeam wafer pack fully into the open black GymBeam duffle bag, then draws the zipper closed along the top of the bag with one hand while the other hand holds the handle, smiling and looking down. "
          "The bag keeps its exact shape, logo patch and tag; there is exactly one bag. " + NOWIND),
 "S06": dict(start="S06a_keyframe_1080x1920.png", end="S06_keyframe_1080x1920.png",
   prompt="She is seated in a PARKED car (engine off, not driving). She tears open the top of the sealed GymBeam wafer wrapper with her fingers so a wafer begins to slide out, smiling and looking at it. The wrapper keeps its exact design. "
          "The black bag stays on the passenger seat. " + NOWIND),
 "S08": dict(start="S08_keyframe_1080x1920.png", end="S08b_keyframe_1080x1920.png",
   prompt="The woman pushes the glass door open with her hand and walks naturally through it into the modern gym, the black GymBeam duffle bag swinging gently in her other hand; the glass door swings open smoothly and settles, with realistic reflections. "
          "Natural stride, the bag keeps its exact shape and logo patch, one bag only. " + NOWIND),
}

if __name__ == "__main__":
    shot = sys.argv[1]; c = CLIPS[shot]; key = None   # 7D: key stays None without .env
    for line in ((ROOT / ".env").read_text(encoding="utf-8").splitlines() if (ROOT / ".env").is_file() else []):   # 7D: no .env in a fresh workspace -> no key, guards still refuse
        if line.startswith("FAL_KEY="):
            key = line.split("=", 1)[1].strip().strip('"')
    from studio.providers.fal_video import ENDPOINT, FalKlingVideo
    from studio.tools.transport import UrllibTransport
    img_spent = round(sum((json.loads(l).get("cost_usd") or 0) for l in (LOG / "api_usage.jsonl").read_text(encoding="utf-8").splitlines()), 6)
    v = FalKlingVideo(transport=UrllibTransport(), api_key=key, budget_usd=round(CAP - img_spent, 6), max_requests=4, usage_path=LOG / "fal_usage.jsonl")
    print(f"{shot}: images spent {img_spent}; video spent {v.spent_usd}; requests {v.api_requests}/4; worst case this clip {v.check_budget(3, '1080p')}; "
          f"total if sent {round(img_spent + v.spent_usd + v.estimate_usd(3), 6)} of {CAP}")
    if "--preflight" in sys.argv:
        sys.exit(0)
    VC.mkdir(exist_ok=True)
    (R / "prompts" / f"KLING_{shot}_prompt_SENT.txt").write_text(f"endpoint={ENDPOINT}\nduration=3\nresolution=1080p\nstart={c['start']}\nend={c['end']}\n\n{c['prompt']}\n", encoding="utf-8")
    res = v.generate_from_image(image=(KF / c["start"]).read_bytes(), prompt=c["prompt"], duration_s=3, resolution="1080p",
                                end_image=(KF / c["end"]).read_bytes() if c["end"] else None)
    (VC / f"{shot}_kling_raw.mp4").write_bytes(res["mp4"])
    (VC / f"{shot}_kling_request.json").write_text(json.dumps({"endpoint": ENDPOINT, "request_id": res["request_id"], "cost_usd_estimated": res["cost_usd"], "duration_s": 3,
                                                                "resolution": "1080p", "start": c["start"], "end": c["end"], "bytes": len(res["mp4"])}, indent=1), encoding="utf-8")
    print("done", res["request_id"], res["cost_usd"], len(res["mp4"]))
