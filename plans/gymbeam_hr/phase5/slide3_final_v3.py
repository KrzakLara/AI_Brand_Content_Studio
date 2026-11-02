"""Slide 3 v3 (Phase 7F): fix ONLY the spoon/subtitle overlap by shrinking the SUBTITLE "Prah. Voda. Gotovo." (51 px -> 37 px, same left edge and top edge).
The headline "PRIPREMA:" is taken pixel-for-pixel from the v2 text layer. Footage = the same kling_raw.mp4, same crop/scale/overlay/encode as v2. No network, no spend.

  python slide3_final_v3.py --out <dir> [--trim-frames N]   writes slide3_priprema_FINAL_v3_1080x1350.mp4 (full 121 frames), or with --trim-frames the shorter ALT file;
                                                            plus text layer and QA json (per-frame occlusion of both text blocks by the spoon/scoop); refuses to overwrite
"""
import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location("p3", HERE / "slide3_video_prep.py"); p3 = importlib.util.module_from_spec(sp); sp.loader.exec_module(p3)
OUT = p3.OUT
SUB_SIZE_V2, SUB_SIZE = 51, 37
FF = imageio_ffmpeg.get_ffmpeg_exe()
FILT = "[0:v]crop=1286:1608,scale=1080:1350:flags=lanczos,format=rgba[v];[v][1:v]overlay=0:0:shortest=1,format=yuv420p"


def build_layer() -> Image.Image:
    L = Image.open(OUT / "text_layer_v2_1080x1350.png").convert("RGBA")
    d = ImageDraw.Draw(L)
    d.rectangle((0, 150, 1080, 262), fill=(0, 0, 0, 0))                       # clear the old subtitle only (headline ends at y=132)
    top_v2 = 168                                                              # measured top of the v2 subtitle glyphs
    f = p3.mont(SUB_SIZE, "Bold")
    probe = Image.new("RGBA", (1080, 300)); ImageDraw.Draw(probe).text((64, 100), p3.SUB, font=f, fill=(0, 0, 0, 255))
    ys = np.where(np.asarray(probe)[..., 3] > 30)[0]
    d.text((64, 100 + top_v2 - ys.min()), p3.SUB, font=f, fill=p3.BURG + (255,))   # glyph top lands on y=168 like v2
    return L


def read(path, w=1080, h=1350):
    p = subprocess.run([FF, "-v", "error", "-i", str(path), "-vf", "crop=1286:1608,scale=1080:1350:flags=lanczos" if "kling_raw" in str(path) else "null", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w, 3)


def occlusion(layer: Image.Image, raw: np.ndarray) -> dict:
    """Per frame: footage pixels that are 'object' (steel/scoop: dark or neutral-bright, i.e. not the pink background) lying within 4 px of a text pixel, separately for headline / subtitle."""
    A = np.asarray(layer)[..., 3] > 30
    k = np.ones((9, 9), np.uint8)
    head = cv2.dilate((A[:150]).astype(np.uint8), k).astype(bool); sub = cv2.dilate((A[150:262]).astype(np.uint8), k).astype(bool)
    res = {"headline": [], "subtitle": []}
    for f in raw:
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV)
        obj = (hsv[..., 1] < 26) | (hsv[..., 2] < 175)                       # S<0.10 or V<0.69
        res["headline"].append(int((obj[:150] & head).sum())); res["subtitle"].append(int((obj[150:262] & sub).sum()))
    return res


def build(out_dir: Path, trim: int | None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    name = "slide3_priprema_FINAL_v3_1080x1350.mp4" if trim is None else f"slide3_priprema_ALT_trim{trim}f_1080x1350.mp4"
    out = out_dir / name
    if out.exists():
        raise FileExistsError(f"{out} exists; refusing to overwrite")
    layer_p = out_dir / "text_layer_v3_1080x1350.png"
    if not layer_p.exists():
        build_layer().save(layer_p)
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error", "-i", str(OUT / "kling_raw.mp4"), "-loop", "1", "-i", str(layer_p), "-filter_complex", FILT, "-an"]
    if trim:
        cmd += ["-frames:v", str(trim)]
    subprocess.run(cmd + ["-c:v", "libx264", "-crf", "14", "-preset", "slow", "-r", "24", "-movflags", "+faststart", str(out)], check=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); ap.add_argument("--trim-frames", type=int)
    a = ap.parse_args()
    v = build(a.out, a.trim_frames); print(v)
    layer = Image.open(a.out / "text_layer_v3_1080x1350.png").convert("RGBA")
    raw = read(OUT / "kling_raw.mp4"); occ = occlusion(layer, raw)
    old = occlusion(Image.open(OUT / "text_layer_v2_1080x1350.png").convert("RGBA"), raw)
    rep = {"frames_total": len(raw), "v2_subtitle_frames_with_object_pixels_near_text": [i for i, c in enumerate(old["subtitle"]) if c > 0], "v3_subtitle_frames_with_object_pixels_near_text": [i for i, c in enumerate(occ["subtitle"]) if c > 0],
           "headline_frames_with_object_pixels_near_text_(unchanged_layer)": [i for i, c in enumerate(occ["headline"]) if c > 0], "v3_subtitle_max_px": max(occ["subtitle"]), "headline_max_px": max(occ["headline"])}
    (a.out / "slide3_v3_QA.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); print(json.dumps(rep, indent=1))

