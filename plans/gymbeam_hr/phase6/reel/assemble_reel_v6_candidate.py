"""Post 3 reel - V6 CANDIDATE (zero cost, existing assets only; V4 and V5 candidate are never touched).
Human review: V4 rejected (malformed bag handle in the S03 'wafer into bag' shot); V5 candidate rejected (in the first kitchen motion
shot, S02, the cup changes position within about a second = AI instability).
V6: no kitchen motion footage at all. Kitchen = the S01 still (static scene, only a 2% push-in), then the first clean shots:
S06 car (V4 verified ranges) and S08 gym entrance (last shot). S02 and S03 are not used."""
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import foley as fo  # noqa: E402
from assemble_reel import KF, FIN, AUD, R, still, text_layer, over  # noqa: E402
from assemble_reel_v2 import clip, OPEN_TXT  # noqa: E402
from reel_lib import FF, FPS, H, W  # noqa: E402

S01_RAW = KF / "S01_raw.png"
OUT = FIN / "GYMBEAM_WAFER_LIFESTYLE_REEL_V6_CANDIDATE.mp4"
SEGS = [   # (name, frames, text)
    ("1_counter_still_pushin", lambda: list(still(S01_RAW, 36, 1.0, 1.02)), OPEN_TXT),
    ("2a_S06_car_holds_sealed_pack", lambda: clip("S06", 4, 27), None),
    ("2b_S06_car_starts_opening", lambda: clip("S06", 38, 53), None),
    ("3_S08_gym_entrance_LAST", lambda: clip("S08", 26, 73), None),
]


def main():
    silent = FIN / "_work_V6_candidate_silent_master.mp4"
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
    fo.place(mix, fo.rustle(0.30, 50, 2200, 8500), t0["2b_S06_car_starts_opening"] + 0.05, 0.14)   # wrapper pinched in the car
    fo.place(mix, fo.footsteps([0.5, 0.92, 1.34], 1.6, 0.6), t0["3_S08_gym_entrance_LAST"] + 0.9, 0.2)
    room = np.convolve(fo.noise(total + 1), np.ones(40) / 40, "same") * 0.004
    wav = AUD / "V6_candidate_foley_only_mix.wav"
    fo.to_wav(wav, (mix + room)[: int(total * fo.SR)], peak=0.35)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", str(OUT)], check=True)
    (R / "logs/assembly_timeline_V6_candidate.txt").write_text("\n".join(f"{k}\t{v:.3f}s\t{lens[k]} frames" for k, v in t0.items()) + f"\ntotal\t{total:.3f}s\n", encoding="utf-8")


if __name__ == "__main__":
    main()
