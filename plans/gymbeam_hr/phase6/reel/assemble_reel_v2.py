"""Post 3 reel — EDIT V2 (local only; zero API cost). V1 files are never touched.

Feedback applied: no music, removed S04/S05/S07(break)/zipper/unwrap distortion, straight cuts, natural framing, minimal foley, text in safe areas.
Run:  python assemble_reel_v2.py
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import foley as fo  # noqa: E402
from assemble_reel import KF, VC, FIN, AUD, R, still, text_layer, over  # noqa: E402
from reel_lib import FF, FPS, H, W, read_frames  # noqa: E402

OPEN_TXT = text_layer([((70, 1440), "MALI RITUALI", 64, "ExtraBold"), ((70, 1510), "U POKRETU.", 64, "ExtraBold")])           # counter area under the pack, above the bottom UI
END_TXT = text_layer([((70, 1388), "TVOJ SNACK.", 62, "ExtraBold"), ((70, 1454), "TVOJ RITAM.", 62, "ExtraBold"), ((74, 1532), "GymBeam 32% Protein Wafer", 32, "Bold")])


def clip(name, a, b):
    """Frames a..b-1 of a Kling clip at native framing and speed (no zoom, no speed change)."""
    fr = read_frames(VC / f"{name}_kling_raw.mp4")
    return [fr[i] for i in range(a, b)]


# (name, frames-factory, text layer or None)  — straight cuts only
S01_RAW = KF / "S01_raw.png"
SEGS = [
    ("S01_wide", lambda: list(still(S01_RAW, 36, 1.0, 1.02)), OPEN_TXT),
    ("S02_pickup", lambda: clip("S02", 0, 68), None),
    ("S03_wafer_into_bag", lambda: clip("S03", 0, 18), None),
    ("S06_car_sealed_pack", lambda: clip("S06", 0, 28), None),
    ("PRODUCT_closeup", lambda: list(still(S01_RAW, 36, 1.45, 1.47, (0.485, 0.625), (0.485, 0.625))), None),
    ("S08_gym_entry", lambda: clip("S08", 26, 68), None),
    ("END_frame", lambda: list(still(S01_RAW, 60, 1.12, 1.12, (0.56, 0.55), (0.56, 0.55))), END_TXT),
]


def main():
    silent = FIN / "_work_V2_silent_master.mp4"
    enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent)], stdin=subprocess.PIPE)
    starts = {}; idx = 0
    for name, fac, txt in SEGS:
        frames = fac(); starts[name] = idx
        for f in frames:
            enc.stdin.write((over(f, txt) if txt else f).tobytes()); idx += 1
    enc.stdin.close(); enc.wait()
    total = idx / FPS
    t0 = {k: v / FPS for k, v in starts.items()}
    print("frames", idx, "seconds", round(total, 3), {k: round(v, 2) for k, v in t0.items()})

    # ---- minimal, quiet foley only where the action is visible; NO music, no zipper/door/crunch/whoosh
    n = int(total * fo.SR) + fo.SR; mix = np.zeros(n)
    fo.place(mix, fo.rustle(0.40, 70), t0["S02_pickup"] + 1.30, 0.22)                    # pack lifted from the counter
    fo.place(mix, fo.rustle(0.35, 60), t0["S03_wafer_into_bag"] + 0.12, 0.18)           # wafer slides into the bag
    fo.place(mix, fo.footsteps([0.45, 0.88, 1.31], 1.6, 0.6), t0["S08_gym_entry"], 0.22)  # steps inside the gym
    room = np.convolve(fo.noise(total + 1), np.ones(40) / 40, "same") * 0.004
    mono = (mix + room)[: int(total * fo.SR)]
    fo.to_wav(AUD / "V2_foley_only_mix.wav", mono, peak=0.35)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(AUD / "V2_foley_only_mix.wav"), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", str(FIN / "GYMBEAM_WAFER_LIFESTYLE_REEL_V2.mp4")], check=True)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-c:v", "copy", "-an", "-movflags", "+faststart", str(FIN / "GYMBEAM_WAFER_LIFESTYLE_REEL_V2_SILENT.mp4")], check=True)
    (R / "logs/assembly_timeline_V2.txt").write_text("\n".join(f"{k}\t{v:.3f}s\t{len(fac())} frames" for (k, fac, _), v in zip(SEGS, t0.values())) + f"\ntotal\t{total:.3f}s\n", encoding="utf-8")


if __name__ == "__main__":
    main()
