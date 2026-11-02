"""Slide 3 v2: typography-only correction (title 'PRIPREMA:'), rebuilt from kling_raw.mp4 with the SAME crop/scale/overlay/encode as the previous final. No network, no spend."""
import importlib.util
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location("p3", HERE / "slide3_video_prep.py"); p3 = importlib.util.module_from_spec(sp); sp.loader.exec_module(p3)
OUT = p3.OUT
NEW_TITLE = "PRIPREMA:"
OLD_S = 102                                   # size used by the previous export (title and, through s*0.5 / s*1.1, the subtitle)


def build():
    L = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    s = OLD_S
    while d.textlength(NEW_TITLE, font=p3.mont(s, "ExtraBold")) > p3.MAX_TITLE_W:    # only the headline size may change
        s -= 2
    d.text(p3.TITLE_XY, NEW_TITLE, font=p3.mont(s, "ExtraBold"), fill=p3.BURG + (255,))
    d.text((p3.TITLE_XY[0] + 4, p3.TITLE_XY[1] + int(OLD_S * 1.1)), p3.SUB, font=p3.mont(int(OLD_S * 0.5), "Bold"), fill=p3.BURG + (255,))   # subtitle: unchanged size/position
    return L, s


if __name__ == "__main__":
    L, s = build(); L.save(OUT / "text_layer_v2_1080x1350.png")
    Image.alpha_composite(Image.open(p3.SRC).convert("RGBA"), L).convert("RGB").save(OUT / "preview_frame_with_text_v2.png")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(OUT / "kling_raw.mp4"), "-loop", "1", "-i", str(OUT / "text_layer_v2_1080x1350.png"), "-filter_complex",
                    "[0:v]crop=1286:1608,scale=1080:1350:flags=lanczos,format=rgba[v];[v][1:v]overlay=0:0:shortest=1,format=yuv420p", "-an", "-c:v", "libx264", "-crf", "14", "-preset", "slow",
                    "-r", "24", "-movflags", "+faststart", str(OUT / "slide3_priprema_FINAL_v2_1080x1350.mp4")], check=True)
    print("title px", s)
