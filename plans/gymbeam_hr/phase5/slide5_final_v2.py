"""Slide 5 v2 final video, rebuilt from kling_raw_v2.mp4 + text_layer_v3 (no network, no spend).

Added in Phase 7B: no script for this step existed before (it was run inline). The filter chain below reproduces the delivered
slide5_napitak_za_ljepotu_FINAL_v2_1080x1350.mp4 frame for frame (decoded-frame MD5 equal; no crop, scale 1288x1608 -> 1080x1350).

  python slide5_final_v2.py --out <dir>            rebuild the delivered video into <dir> (never into runs/ by default)
  python slide5_final_v2.py --preview-alt <dir>    write a TEXT-ONLY review image of the proposed claim wording into <dir>
"""
import argparse
import importlib.util
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p5", HERE / "slide5_video_prep.py")
p5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p5)
OUT, BURG = p5.OUT, p5.BURG + (255,)
ALT_LINES = ("Cink doprinosi održavanju normalne", "kože, kose i noktiju.")      # proposal, see SLIDE5_CLAIM_REVIEW.md


def rebuild(out_dir: Path) -> Path:
    out = out_dir / "slide5_napitak_za_ljepotu_FINAL_v2_rebuilt_1080x1350.mp4"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(OUT / "kling_raw_v2.mp4"), "-loop", "1", "-i", str(OUT / "text_layer_v3_1080x1350.png"),
                    "-filter_complex", "[0:v]crop=1288:1608,scale=1080:1350:flags=lanczos,format=rgba[v];[v][1:v]overlay=0:0:shortest=1,format=yuv420p",
                    "-an", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-r", "24", "-movflags", "+faststart", str(out)], check=True)
    return out


def preview_alt(out_dir: Path) -> Path:
    """First frame with the proposed wording (two lines, taller panel). A review aid only: the video is not rebuilt."""
    L = Image.open(OUT / "text_layer_v3_1080x1350.png").convert("RGBA")
    base = Image.open(OUT / "start_frame_hair_calmed_1080x1350.png").convert("RGBA")
    d = ImageDraw.Draw(L)
    d.rectangle((30, 1130, 800, 1275), fill=(0, 0, 0, 0))                          # clear the old panel and bottom lines
    d.rounded_rectangle((40, 1120, 800, 1290), 28, fill=(251, 243, 242, 64))
    d.text((64, 1130), "Ljepota počinje iznutra.", font=p5.mont(38, "Bold"), fill=BURG)
    for i, line in enumerate(ALT_LINES):
        d.text((64, 1180 + i * 46), line, font=p5.mont(38, "Bold"), fill=BURG)
    out = out_dir / "REVIEW_ONLY_slide5_alt_wording_frame0.png"
    Image.alpha_composite(base, L).convert("RGB").save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    ap.add_argument("--preview-alt", type=Path)
    a = ap.parse_args()
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True); print(rebuild(a.out))
    if a.preview_alt:
        a.preview_alt.mkdir(parents=True, exist_ok=True); print(preview_alt(a.preview_alt))
