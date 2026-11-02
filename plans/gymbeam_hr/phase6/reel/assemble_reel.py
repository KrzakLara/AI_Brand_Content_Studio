"""Post 3 reel assembly (deterministic, local; no network, no spend).

AI inputs: 4 Kling clips (S02, S03, S06, S08) + generated keyframes (stills). Everything else is local: Pillow motion on stills,
crossfades, match cut + flash, text overlay, procedurally synthesized foley/bed (foley.py), ffmpeg encode.
Run:  python assemble_reel.py
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import foley as fo  # noqa: E402
from reel_lib import FF, FPS, H, W, read_frames  # noqa: E402

R = ROOT / "runs/gymbeam-wafer-reel"; KF = R / "keyframes"; VC = R / "video_clips"; FIN = R / "final"; AUD = R / "audio"
FONT = ROOT / "runs/colla-pink/font/Montserrat.ttf"
ESPRESSO = (59, 42, 32)


def mont(size, weight="ExtraBold"):
    f = ImageFont.truetype(str(FONT), size); f.set_variation_by_name(weight); return f


def text_layer(lines):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    for xy, s, size, wt in lines:
        d.text(xy, s, font=mont(size, wt), fill=ESPRESSO + (255,))
    a = np.asarray(L).astype(np.float32)
    return a[..., :3], a[..., 3:4] / 255.0


OPEN_TXT = text_layer([((70, 1478), "MALI RITUALI", 88, "ExtraBold"), ((70, 1566), "U POKRETU.", 88, "ExtraBold")])   # free counter area under the pack
END_TXT = text_layer([((470, 1522), "TVOJ SNACK.", 82, "ExtraBold"), ((470, 1600), "TVOJ RITAM.", 82, "ExtraBold"), ((474, 1698), "GymBeam 32% Protein Wafer", 36, "Bold")])   # free counter area right of the broken wafer


def over(frame, layer):
    rgb, a = layer
    return (frame.astype(np.float32) * (1 - a) + rgb * a).astype(np.uint8)


def still(path, n, z0, z1, c0=(0.5, 0.5), c1=(0.5, 0.5), sway=0.0):
    """Generator of n frames: smooth zoom/pan on a (larger) still via sub-pixel affine resampling."""
    im = Image.open(path).convert("RGB"); sw, sh = im.size
    for k in range(n):
        u = k / max(n - 1, 1); u = u * u * (3 - 2 * u) * 0.7 + u * 0.3
        z = z0 + (z1 - z0) * u; cx = (c0[0] + (c1[0] - c0[0]) * u) * sw + sway * np.sin(k / 5.5) * sw / 100; cy = (c0[1] + (c1[1] - c0[1]) * u) * sh
        cx = min(max(cx, 0.5 * sw / z), sw - 0.5 * sw / z); cy = min(max(cy, 0.5 * sh / z), sh - 0.5 * sh / z)   # never sample outside the still
        fx, fy = sw / W, sh / H
        a, e = fx / z, fy / z
        yield np.asarray(im.transform((W, H), Image.AFFINE, (a, 0, cx - (W / 2) * a, 0, e, cy - (H / 2) * e), Image.BICUBIC))


def kling(name, n, src_len, ease=0.0):
    fr = read_frames(VC / f"{name}_kling_raw.mp4"); m = len(fr)
    for k in range(n):
        u = k / max(n - 1, 1); u = u * (1 - ease) + (u * u * (3 - 2 * u)) * ease
        p = u * min(src_len * FPS, m - 1); i = int(p); j = min(i + 1, m - 1); f = p - i
        yield (fr[i].astype(np.float32) * (1 - f) + fr[j].astype(np.float32) * f).astype(np.uint8) if f > 0.02 else fr[i]


def sweep(frames, n):
    """Moving soft light band across the opening still."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for k, f in enumerate(frames):
        pos = -0.3 + 1.6 * k / max(n - 1, 1); d = (xx / W * 0.7 + yy / H * 0.3) - pos
        band = np.exp(-(d / 0.12) ** 2)[..., None] * 0.13
        yield np.clip(f.astype(np.float32) + 255 * band * np.array([1, 0.97, 0.92], np.float32), 0, 255).astype(np.uint8)


def fr_n(s):
    return int(round(s * FPS))


# ---------------------------------------------------------------- timeline (name, seconds, generator factory, crossfade-in frames)
SEGS = [
    ("S01", 1.75, lambda n: sweep(still(KF / "S01_raw.png", n, 1.0, 1.09, (0.5, 0.5), (0.53, 0.48)), n), 0),
    ("S02", 2.50, lambda n: kling("S02", n, 3.0, 0.5), 6),
    ("S03", 2.50, lambda n: kling("S03", n, 3.0), 0),
    ("S04", 1.60, lambda n: still(KF / "S04_crop_bagwalk_1080x1920.png", n, 1.06, 1.14, (0.5, 0.56), (0.5, 0.45), sway=1.2), 0),
    ("S05", 1.40, lambda n: still(KF / "S05_raw.png", n, 1.0, 1.07, (0.5, 0.5), (0.52, 0.49)), 6),
    ("S06", 3.00, lambda n: kling("S06", n, 3.0), 0),
    ("S07a", 1.10, lambda n: still(KF / "S07a_raw.png", n, 1.0, 1.06), 0),
    ("S07b", 1.20, lambda n: still(KF / "S07b_raw.png", n, 1.05, 1.0), 0),
    ("S08", 2.70, lambda n: kling("S08", n, 3.0), 6),
    ("S09", 3.10, lambda n: still(KF / "S09_raw.png", n, 1.0, 1.06, (0.5, 0.5), (0.5, 0.54)), 8),
]


def main():
    FIN.mkdir(exist_ok=True)
    silent = FIN / "_work_silent_master.mp4"
    enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent)], stdin=subprocess.PIPE)
    idx = 0; starts = {}; pending = []; end_start = None
    cuts = []
    sample = {}

    def emit(f):
        nonlocal idx
        if idx < fr_n(1.5):
            f = over(f, OPEN_TXT)
        if end_start is not None and idx >= end_start:
            f = over(f, END_TXT)
        enc.stdin.write(f.tobytes()); idx += 1

    for si, (name, secs, fac, cf) in enumerate(SEGS):
        n = fr_n(secs); frames = list(fac(n)); nxt_cf = SEGS[si + 1][3] if si + 1 < len(SEGS) else 0
        starts[name] = idx - len(pending) if (cf and pending) else idx
        if name == "S09":
            end_start = starts[name] + cf
        head = 0
        if cf and pending:
            for j, p in enumerate(pending):                            # crossfade: tail of previous shot over head of this one
                a = (j + 1) / (len(pending) + 1)
                emit((p.astype(np.float32) * (1 - a) + frames[j].astype(np.float32) * a).astype(np.uint8))
            head = len(pending); pending = []
        if name == "S07b":                                              # match cut: 2-frame white flash on the break
            for j, a in enumerate((0.75, 0.35)):
                frames[j] = (frames[j].astype(np.float32) * (1 - a) + 255 * a).astype(np.uint8)
        body = frames[head: n - nxt_cf]
        for f in body:
            emit(f)
        pending = frames[n - nxt_cf:] if nxt_cf else []
        cuts.append((name, starts[name] / FPS))
        del frames
    for p in pending:
        emit(p)
    enc.stdin.close(); enc.wait()
    total = idx / FPS
    print("frames", idx, "seconds", round(total, 3), {k: round(v / FPS, 2) for k, v in starts.items()})

    # ---------------------------------------------------------------- audio (procedural foley + soft bed)
    t0 = {k: v / FPS for k, v in starts.items()}
    n = int(total * fo.SR) + fo.SR; mix = np.zeros(n)
    fo.place(mix, fo.keys_jingle(), 0.30, 0.8)
    fo.place(mix, fo.rustle(0.5, 90), t0["S02"] + 1.15, 0.45)
    fo.place(mix, fo.rustle(0.35, 70), t0["S03"] + 0.10, 0.4)
    fo.place(mix, fo.zipper(1.0), t0["S03"] + 1.25, 0.6)
    fo.place(mix, fo.footsteps([0.15, 0.58, 1.0, 1.42], 1.8, 0.8), t0["S04"], 0.8)
    fo.place(mix, fo._bp(fo.door_thunk(), 40, 1400), t0["S05"] - 0.04, 0.85)
    fo.place(mix, fo.rustle(1.4, 120, 2200, 8500), t0["S06"] + 1.35, 0.55)
    fo.place(mix, fo.crunch(), t0["S07b"], 1.0)
    fo.place(mix, fo.glass_door_push(), t0["S08"] + 0.05, 0.7)
    fo.place(mix, fo.footsteps([0.9, 1.32, 1.74, 2.16], 2.6, 0.7), t0["S08"] + 0.2, 0.7)
    fo.place(mix, fo.whoosh(0.7), t0["S09"] - 0.15, 0.4)
    fo.place(mix, fo.whoosh(0.5), t0["S07a"] - 0.2, 0.25)
    room = np.convolve(fo.noise(total + 1), np.ones(40) / 40, "same") * 0.006
    foley_only = (mix + room)[: int(total * fo.SR)]
    bed = fo.music_bed(total)
    with_bed = foley_only + bed[: len(foley_only)] * 1.0
    fo.to_wav(AUD / "foley_only_mix.wav", foley_only); fo.to_wav(AUD / "foley_plus_bed_mix.wav", with_bed)
    for wav, out in (("foley_plus_bed_mix.wav", "GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL.mp4"), ("foley_only_mix.wav", "GYMBEAM_WAFER_REEL_FOLEY_ONLY.mp4")):
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(AUD / wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", str(FIN / out)], check=True)
    (R / "logs/assembly_timeline.txt").write_text("\n".join(f"{k}\t{v:.3f}s" for k, v in t0.items()) + f"\ntotal\t{total:.3f}s\n", encoding="utf-8")


if __name__ == "__main__":
    main()
