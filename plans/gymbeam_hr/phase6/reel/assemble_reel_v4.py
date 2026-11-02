"""Post 3 reel - EDIT V4 (best zero-cost edit from existing assets; no API calls). V1-V3 are never touched.
Every segment is a hand-picked, verified frame range of an existing Kling clip; jump cuts inside S02/S06 hide the frames where the pack
smears/warps (S02 f31-53) or looks like paper (S06 f54+) or fingers blur (S06 f27-37). Straight cuts, native framing, no music."""
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
SEGS = [   # (name, frames, text)
    ("1_counter", lambda: list(still(S01_RAW, 36, 1.0, 1.02)), OPEN_TXT),
    ("2a_S02_reach_touch_pack", lambda: clip("S02", 0, 31), None),
    ("2b_S02_holds_pack", lambda: clip("S02", 54, 73), None),
    ("3_S03_wafer_into_bag", lambda: clip("S03", 0, 19), None),
    ("4a_S06_car_holds_sealed_pack", lambda: clip("S06", 4, 27), None),
    ("4b_S06_car_starts_opening", lambda: clip("S06", 38, 53), None),
    ("5_S08_gym_entrance_LAST", lambda: clip("S08", 26, 73), None),
]


def main():
    silent = FIN / "_work_V4_silent_master.mp4"
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
    fo.place(mix, fo.rustle(0.35, 60), t0["3_S03_wafer_into_bag"] + 0.10, 0.17)              # wafer slides into the bag
    fo.place(mix, fo.rustle(0.30, 50, 2200, 8500), t0["4b_S06_car_starts_opening"] + 0.05, 0.14)   # wrapper pinched in the car
    fo.place(mix, fo.footsteps([0.5, 0.92, 1.34], 1.6, 0.6), t0["5_S08_gym_entrance_LAST"] + 0.9, 0.2)
    room = np.convolve(fo.noise(total + 1), np.ones(40) / 40, "same") * 0.004
    fo.to_wav(AUD / "V4_foley_only_mix.wav", (mix + room)[: int(total * fo.SR)], peak=0.35)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(AUD / "V4_foley_only_mix.wav"), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", str(FIN / "GYMBEAM_WAFER_LIFESTYLE_REEL_V4.mp4")], check=True)
    (R / "logs/assembly_timeline_V4.txt").write_text("\n".join(f"{k}\t{v:.3f}s\t{lens[k]} frames" for k, v in t0.items()) + f"\ntotal\t{total:.3f}s\n", encoding="utf-8")


if __name__ == "__main__":
    main()
