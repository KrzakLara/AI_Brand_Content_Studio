"""Post 3: ONE Kling v4 image-to-video request for S03B (wafer into bag), authorised: max 0.75 USD for this request, cumulative cap 5.20 USD.
3 s, 1080p, start frame only, no retry. usage: python run_kling_S03B.py [--preflight]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
R = ROOT / "runs/gymbeam-wafer-reel"; KF = R / "keyframes"; LOG = R / "logs"; VC = R / "video_clips"
CAP, THIS_MAX = 5.20, 0.75
PROMPT = ("Locked-off static camera: no zoom, no pan, no camera shake. The woman gently lowers the sealed GymBeam wafer pack with her left hand (the hand on the left side of the picture) down into the open top of the black GymBeam duffle bag "
          "until it slides inside, while her other hand keeps resting lightly on the bag's top edge, smiling softly and looking down at the bag. "
          "Both leather handles of the bag stay exactly where they are: lowered, motionless, each firmly attached at both ends to its metal rings; no hand touches, lifts or moves any handle; no handle changes shape or position. "
          "The bag, its GymBeam logo patch, the tag, the coffee cup, the keys and the counter stay completely unchanged and stable; exactly one bag. The wafer pack keeps exactly its design, colours and logo. "
          "Her long dark-brown hair hangs naturally and stays in place: no wind, no fan, no dramatic hair movement. Natural, calm, realistic movement, correct hand anatomy with five fingers on each hand, no morphing of the face, "
          "no duplicated objects, no distorted logos, no chain, no extra straps. Photorealistic.")

if __name__ == "__main__":
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("FAL_KEY="):
            key = line.split("=", 1)[1].strip().strip('"')
    from studio.providers.fal_video import ENDPOINT, FalKlingVideo
    from studio.tools.transport import UrllibTransport
    img = sum((json.loads(l).get("cost_usd") or 0) for f in ("api_usage.jsonl", "api_usage_S03B.jsonl") for l in (LOG / f).read_text(encoding="utf-8").splitlines())
    img = round(img, 6)
    v = FalKlingVideo(transport=UrllibTransport(), api_key=key, budget_usd=round(CAP - img, 6), max_requests=5, usage_path=LOG / "fal_usage.jsonl")
    worst = v.check_budget(3, "1080p")
    assert worst <= THIS_MAX, f"worst case {worst} exceeds the authorised {THIS_MAX}"
    print(f"S03B: images spent {img}; video spent {v.spent_usd}; requests {v.api_requests}/5; worst case this clip {worst}; total if sent {round(img + v.spent_usd + v.estimate_usd(3), 6)} of {CAP}")
    if "--preflight" in sys.argv:
        sys.exit(0)
    (R / "prompts" / "KLING_S03B_prompt_SENT.txt").write_text(f"endpoint={ENDPOINT}\nduration=3\nresolution=1080p\nstart=S03B_keyframe_1080x1920.png\nend=None\n\n{PROMPT}\n", encoding="utf-8")
    res = v.generate_from_image(image=(KF / "S03B_keyframe_1080x1920.png").read_bytes(), prompt=PROMPT, duration_s=3, resolution="1080p", end_image=None)
    (VC / "S03B_kling_raw.mp4").write_bytes(res["mp4"])
    (VC / "S03B_kling_request.json").write_text(json.dumps({"endpoint": ENDPOINT, "request_id": res["request_id"], "cost_usd_estimated": res["cost_usd"], "duration_s": 3,
                                                            "resolution": "1080p", "start": "S03B_keyframe_1080x1920.png", "end": None, "bytes": len(res["mp4"])}, indent=1), encoding="utf-8")
    print("done", res["request_id"], res["cost_usd"], len(res["mp4"]))
