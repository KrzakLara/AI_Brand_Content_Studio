"""Slide 3 video prep: clean start frame (copy, no text) + the fixed typography layer (RGBA, 1080x1350). No network, no spend."""
import hashlib
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "runs/colla-pink"
OUT = RUN / "slide3_video"
SRC = RUN / "carousel/s3_nolettering_1080x1350.png"
BURG = (127, 41, 68)
TITLE, SUB = "Priprema.", "Prah. Voda. Gotovo."
TITLE_XY, MAX_TITLE_W = (60, 44), 540   # right edge stays left of the scoop (its left edge is at x~628)


def mont(size, weight):
    f = ImageFont.truetype(str(RUN / "font/Montserrat.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def build_layer():
    layer = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    s = 128
    while d.textlength(TITLE, font=mont(s, "ExtraBold")) > MAX_TITLE_W:
        s -= 2
    d.text(TITLE_XY, TITLE, font=mont(s, "ExtraBold"), fill=BURG + (255,))
    d.text((TITLE_XY[0] + 4, TITLE_XY[1] + int(s * 1.1)), SUB, font=mont(int(s * 0.5), "Bold"), fill=BURG + (255,))
    return layer, s


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    shutil.copyfile(SRC, OUT / "start_frame_clean_1080x1350.png")
    layer, s = build_layer()
    layer.save(OUT / "text_layer_1080x1350.png")
    base = Image.open(SRC).convert("RGBA")
    Image.alpha_composite(base, layer).convert("RGB").save(OUT / "preview_frame_with_text.png")
    print("title px", s, "src sha256", hashlib.sha256(SRC.read_bytes()).hexdigest()[:16])
