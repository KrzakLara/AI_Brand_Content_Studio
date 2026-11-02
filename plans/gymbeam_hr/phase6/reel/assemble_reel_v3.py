"""Post 3 reel - EDIT V3 (story edit; local only, zero API cost). V1 and V2 are never touched.
Sequence: counter -> pickup/hold (S02) -> wafer into open bag (S03, cut before the closing) -> straight cut to parked car (S06) -> gym entrance (S08, LAST).
Straight cuts only, native framing, no crossfades, no music."""
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import foley as fo  # noqa: E402
from assemble_reel import KF, FIN, AUD, R, still, text_layer, over  # noqa: E402
from assemble_reel_v2 import clip  # noqa: E402
from reel_lib import FF, FPS, H, W  # noqa: E402

OPEN_TXT = text_layer([((70, 1440), "MALI RITUALI", 64, "ExtraBold"), ((70, 1510), "U POKRETU.", 64, "ExtraBold")])
S01_RAW = KF / "S01_raw.png"
SEGS = [   # (name, frames, text)
    ("1_kitchen_counter", lambda: list(still(S01_RAW, 36, 1.0, 1.02)), OPEN_TXT),
    ("2_S02_pickup_and_hold", lambda: clip("S02", 0, 73), None),
    ("3_S03_wafer_into_open_bag", lambda: clip("S03", 0, 38), None),
    ("5_S06_parked_car_open_wafer", lambda: clip("S06", 4, 73), None),
    ("6_S08_gym_entrance_LAST", lambda: clip("S08", 26, 73), None),
]


def main():
    silent = FIN / "_work_V3_silent_master.mp4"
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
    fo.place(mix, fo.rustle(0.40, 70), t0["2_S02_pickup_and_hold"] + 1.30, 0.20)          # pack lifted from the counter
    fo.place(mix, fo.rustle(0.35, 60), t0["3_S03_wafer_into_open_bag"] + 0.15, 0.17)      # wafer slides into the bag
    fo.place(mix, fo.rustle(0.55, 80, 2200, 8500), t0["5_S06_parked_car_open_wafer"] + 1.30, 0.18)   # wrapper opened in the car
    fo.place(mix, fo.footsteps([0.5, 0.92, 1.34], 1.6, 0.6), t0["6_S08_gym_entrance_LAST"] + 0.9, 0.2)
    room = np.convolve(fo.noise(total + 1), np.ones(40) / 40, "same") * 0.004
    fo.to_wav(AUD / "V3_foley_only_mix.wav", (mix + room)[: int(total * fo.SR)], peak=0.35)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(AUD / "V3_foley_only_mix.wav"), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", str(FIN / "GYMBEAM_WAFER_LIFESTYLE_REEL_V3.mp4")], check=True)
    (R / "logs/assembly_timeline_V3.txt").write_text("\n".join(f"{k}\t{v:.3f}s\t{lens[k]} frames" for k, v in t0.items()) + f"\ntotal\t{total:.3f}s\n", encoding="utf-8")


if __name__ == "__main__":
    main()
