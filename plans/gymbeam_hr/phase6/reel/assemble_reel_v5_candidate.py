"""Post 3 reel - V5 CANDIDATE (zero cost, existing assets only; V4 is never touched).
Human review rejected V4: in the 'wafer into the bag' shot (V4 3.583-4.375 s = S03 f0-18) the bag handle is malformed
(one handle arch ends in her hand with no second anchor; fingers merge with the handle; chain-link shoulder strap).
Repair strategy C: the whole S03 shot is removed (no other footage of that action exists; S03 f19-72 was already
rejected for a floating hand). All other segments are the V4 ranges, unchanged. Foley for the removed shot is dropped."""
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
OUT = FIN / "GYMBEAM_WAFER_LIFESTYLE_REEL_V5_CANDIDATE.mp4"
SEGS = [   # (name, frames, text) - identical to V4 minus "3_S03_wafer_into_bag"
    ("1_counter", lambda: list(still(S01_RAW, 36, 1.0, 1.02)), OPEN_TXT),
    ("2a_S02_reach_touch_pack", lambda: clip("S02", 0, 31), None),
    ("2b_S02_holds_pack", lambda: clip("S02", 54, 73), None),
    ("4a_S06_car_holds_sealed_pack", lambda: clip("S06", 4, 27), None),
    ("4b_S06_car_starts_opening", lambda: clip("S06", 38, 53), None),
    ("5_S08_gym_entrance_LAST", lambda: clip("S08", 26, 73), None),
]


def main():
    silent = FIN / "_work_V5_candidate_silent_master.mp4"
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
    fo.place(mix, fo.rustle(0.30, 60), t0["2a_S02_reach_touch_pack"] + 0.95, 0.17)          # fingertips touch the wrapper
    fo.place(mix, fo.rustle(0.30, 50, 2200, 8500), t0["4b_S06_car_starts_opening"] + 0.05, 0.14)   # wrapper pinched in the car
    fo.place(mix, fo.footsteps([0.5, 0.92, 1.34], 1.6, 0.6), t0["5_S08_gym_entrance_LAST"] + 0.9, 0.2)
    room = np.convolve(fo.noise(total + 1), np.ones(40) / 40, "same") * 0.004
    wav = AUD / "V5_candidate_foley_only_mix.wav"
    fo.to_wav(wav, (mix + room)[: int(total * fo.SR)], peak=0.35)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", str(OUT)], check=True)
    (R / "logs/assembly_timeline_V5_candidate.txt").write_text("\n".join(f"{k}\t{v:.3f}s\t{lens[k]} frames" for k, v in t0.items()) + f"\ntotal\t{total:.3f}s\n", encoding="utf-8")


if __name__ == "__main__":
    main()
