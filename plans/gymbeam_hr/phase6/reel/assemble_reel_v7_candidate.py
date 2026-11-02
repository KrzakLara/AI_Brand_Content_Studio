"""Post 3 reel - V7 CANDIDATE (zero cost, existing assets only; V4, V5 and V6 candidates are never touched).
Preserves the full story: kitchen with the wafer -> she picks it up -> wafer goes into the black GymBeam bag -> car -> gym.

Problem A (cup): measured template match of the cup in S02: f0-16 = state A (corr 0.33), the cup POPS (size/position change, a Kling
  discontinuity) between f16 and f18, and f18-72 = state B, pixel-identical offset (0,0), corr 0.95-1.00. So S02 is used ONLY from f18 on
  (f18-30 touching the pack, f54-72 holding it); f0-16 (cup in the wrong state) is not used.
Problem B (bag handle): in S03 the handle starts at the strap ring at x~575 and runs to her right hand (single arch, no second anchor, fingers
  fused). The wafer-into-bag action (left hand + pack + bag opening + logo patch) lies entirely at x < 540. The shot is therefore an editorial
  CLOSE-UP of S03 f0-18: crop x 0-540, y 790-1750 (540x960), upscaled 2.0x (Lanczos + mild unsharp + fine grain). No pixel is painted or generated.
"""
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import foley as fo  # noqa: E402
from assemble_reel import KF, FIN, AUD, R, still, text_layer, over  # noqa: E402
from assemble_reel_v2 import clip, OPEN_TXT  # noqa: E402
from reel_lib import FF, FPS, H, W  # noqa: E402

S01_RAW = KF / "S01_raw.png"
OUT = FIN / "GYMBEAM_WAFER_LIFESTYLE_REEL_V7_CANDIDATE.mp4"
CROP_X, CROP_Y, CROP_W = 0, 790, 540     # 540 x 960 -> exactly 2.0x to 1080 x 1920


def closeup(name, a, b):
    out = []
    rng = np.random.default_rng(7)
    for k, f in enumerate(clip(name, a, b)):
        c = f[CROP_Y:CROP_Y + CROP_W * 16 // 9, CROP_X:CROP_X + CROP_W]
        c = cv2.resize(c, (W, H), interpolation=cv2.INTER_LANCZOS4)
        blur = cv2.GaussianBlur(c, (0, 0), 2.0)
        c = cv2.addWeighted(c, 1.45, blur, -0.45, 0)
        c = np.clip(c.astype(np.float32) + rng.normal(0, 2.2, c.shape[:2])[..., None], 0, 255).astype(np.uint8)
        out.append(c)
    return out


SEGS = [   # (name, frames, text)
    ("1_counter_still", lambda: list(still(S01_RAW, 36, 1.0, 1.02)), OPEN_TXT),
    ("2a_S02_f18-30_touches_pack", lambda: clip("S02", 18, 31), None),
    ("2b_S02_f54-72_holds_pack", lambda: clip("S02", 54, 73), None),
    ("3_S03_closeup_wafer_into_bag", lambda: closeup("S03", 0, 19), None),
    ("4a_S06_car_holds_sealed_pack", lambda: clip("S06", 4, 27), None),
    ("4b_S06_car_starts_opening", lambda: clip("S06", 38, 53), None),
    ("5_S08_gym_entrance_LAST", lambda: clip("S08", 26, 73), None),
]


def main():
    silent = FIN / "_work_V7_candidate_silent_master.mp4"
    enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent)], stdin=subprocess.PIPE)
    idx = 0; t0 = {}; lens = {}
    for name, fac, txt in SEGS:
        frames = fac(); t0[name] = idx / FPS; lens[name] = len(frames)
        for f in frames:
            enc.stdin.write((over(f, txt) if txt else f).tobytes()); idx += 1
    enc.stdin.close(); enc.wait()
    total = idx / FPS; print("frames", idx, "seconds", round(total, 3), {k: round(v, 2) for k, v in t0.items()})
    n = int(total * fo.SR) + fo.SR; mix = np.zeros(n)
    fo.place(mix, fo.rustle(0.30, 60), t0["2a_S02_f18-30_touches_pack"] + 0.10, 0.17)
    fo.place(mix, fo.rustle(0.35, 60), t0["3_S03_closeup_wafer_into_bag"] + 0.10, 0.17)
    fo.place(mix, fo.rustle(0.30, 50, 2200, 8500), t0["4b_S06_car_starts_opening"] + 0.05, 0.14)
    fo.place(mix, fo.footsteps([0.5, 0.92, 1.34], 1.6, 0.6), t0["5_S08_gym_entrance_LAST"] + 0.9, 0.2)
    room = np.convolve(fo.noise(total + 1), np.ones(40) / 40, "same") * 0.004
    wav = AUD / "V7_candidate_foley_only_mix.wav"
    fo.to_wav(wav, (mix + room)[: int(total * fo.SR)], peak=0.35)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", str(OUT)], check=True)
    (R / "logs/assembly_timeline_V7_candidate.txt").write_text("\n".join(f"{k}\t{v:.3f}s\t{lens[k]} frames" for k, v in t0.items()) + f"\ntotal\t{total:.3f}s\n", encoding="utf-8")


if __name__ == "__main__":
    main()
