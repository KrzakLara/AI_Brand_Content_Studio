"""Slide 5 v3 (Phase 7C): replace ONLY the unsupported claim line, rebuilt locally from kling_raw_v2.mp4 (no network, no spend, no new footage).

Same pipeline as slide5_final_v2.py (scale 1288x1608 -> 1080x1350, lanczos, static overlay, crf 14, 24 fps). The text layer is text_layer_v3 with the bottom
panel redrawn: "Ljepota počinje iznutra." stays at the same size and position, the old line "Njeguj svoju kožu, kosu i nokte." is replaced by the zinc claim
wrapped in two lines (panel grows downwards). The headline and everything above y=1130 are the unchanged pixels of text_layer_v3.

  python slide5_final_v3.py --out <dir> [--qa]     writes the v3 video (+ layer, preview frames and QA json with --qa) into <dir>; refuses to overwrite an existing file
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p5", HERE / "slide5_video_prep.py")
p5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p5)
OUT, BURG = p5.OUT, p5.BURG + (255,)
CLAIM_LINES = ("Cink doprinosi održavanju normalne", "kože, kose i noktiju.")    # "Cink doprinosi održavanju normalne kože, kose i noktiju."
CLAIM_SIZE, CLAIM_Y, CLAIM_STEP = 36, (1210, 1253), 43
CLEAR = (30, 1130, 810, 1320)                                                  # old panel + lines live inside this box; nothing above y=1130 is touched
NAME = "slide5_napitak_za_ljepotu_FINAL_v3_1080x1350.mp4"


def build_layer() -> Image.Image:
    L = Image.open(OUT / "text_layer_v3_1080x1350.png").convert("RGBA")
    d = ImageDraw.Draw(L)
    d.rectangle(CLEAR, fill=(0, 0, 0, 0))
    d.rounded_rectangle((40, 1142, 800, 1308), 28, fill=(251, 243, 242, 64))   # same fill as before, taller panel
    d.text((64, 1160), "Ljepota počinje iznutra.", font=p5.mont(38, "Bold"), fill=BURG)      # unchanged text, size and position
    for y, line in zip(CLAIM_Y, CLAIM_LINES):
        d.text((64, y), line, font=p5.mont(CLAIM_SIZE, "Bold"), fill=BURG)
    return L


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / NAME
    if out.exists():
        raise FileExistsError(f"{out} exists; refusing to overwrite")
    layer = out_dir / "text_layer_v4_zinc_1080x1350.png"
    if not layer.exists():
        build_layer().save(layer)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(OUT / "kling_raw_v2.mp4"), "-loop", "1", "-i", str(layer),
                    "-filter_complex", "[0:v]crop=1288:1608,scale=1080:1350:flags=lanczos,format=rgba[v];[v][1:v]overlay=0:0:shortest=1,format=yuv420p",
                    "-an", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-r", "24", "-movflags", "+faststart", str(out)], check=True)
    return out


def read_frames(path: Path, w=1080, h=1350) -> np.ndarray:
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w, 3)


def qa(video: Path, v2: Path, layer: Path, out_dir: Path) -> dict:
    """Every-frame checks: count/size, text pixels burgundy on every frame, region above the edited box vs the v2 video, changed region confined to the box."""
    f3, f2 = read_frames(video).astype(np.int16), read_frames(v2).astype(np.int16)
    L = np.asarray(Image.open(layer).convert("RGBA")); mask = L[..., 3] >= 250
    ys = np.arange(1350)[:, None] * np.ones((1, 1080), int)
    claim = mask & (ys >= 1200) & (ys < 1300)                      # the new claim lines
    head = mask & (ys < 300)                                       # the headline
    burg = np.array(p5.BURG, np.int16)
    claim_err = [float(np.abs(f[claim] - burg).mean()) for f in f3]
    head_err = [float(np.abs(f[head] - burg).mean()) for f in f3]
    above = ys < CLEAR[1]
    diff_above = np.abs(f3 - f2)[:, above]
    outside_box = ~((ys >= CLEAR[1]) & (ys < CLEAR[3]) & (np.arange(1080)[None, :] >= CLEAR[0]) & (np.arange(1080)[None, :] < CLEAR[2]))
    diff_out = np.abs(f3 - f2)[:, outside_box]
    res = {"frames_v3": len(f3), "frames_v2": len(f2), "size": "1080x1350",
           "claim_text_mean_abs_err_vs_burgundy_max_over_frames": round(max(claim_err), 2), "headline_mean_abs_err_max_over_frames": round(max(head_err), 2),
           "above_y1130_vs_v2": {"mean_abs_diff": round(float(diff_above.mean()), 4), "max_abs_diff": int(diff_above.max()), "note": "H.264 re-encode noise only; the source footage and layer pixels there are identical"},
           "outside_edited_box_vs_v2": {"mean_abs_diff": round(float(diff_out.mean()), 4), "max_abs_diff": int(diff_out.max())}}
    layer_old = np.asarray(Image.open(OUT / "text_layer_v3_1080x1350.png").convert("RGBA"))
    res["layer_identical_outside_box_to_v2_layer"] = bool(np.array_equal(L[:CLEAR[1]], layer_old[:CLEAR[1]]))
    res["ok"] = bool(len(f3) == len(f2) == 121 and max(claim_err) < 12 and max(head_err) < 12 and res["layer_identical_outside_box_to_v2_layer"])
    for i, tag in ((0, "frame000"), (60, "frame060"), (120, "frame120")):
        Image.fromarray(f3[i].astype(np.uint8)).save(out_dir / f"REVIEW_slide5_v3_{tag}.png")
    (out_dir / "slide5_v3_QA.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); ap.add_argument("--qa", action="store_true")
    a = ap.parse_args()
    v = build(a.out); print(v, sha(v))
    if a.qa:
        print(json.dumps(qa(v, OUT / "slide5_napitak_za_ljepotu_FINAL_v2_1080x1350.mp4", a.out / "text_layer_v4_zinc_1080x1350.png", a.out), indent=1))
