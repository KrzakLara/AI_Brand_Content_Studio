"""Slide 5 video prep (no network, no spend): drink-tinted clean start frame + fixed typography layer + previews.
Only the liquid/ice inside the glass is tinted; skin, hair, fruit and everything else stay pixel-identical."""
import colorsys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "runs/colla-pink"
OUT = RUN / "slide5_video"
SRC = RUN / "carousel/s5_nolettering_1080x1350.png"
BURG = (127, 41, 68)
BABY = np.array([246, 168, 190], float)
GLASS = [(369, 427), (466, 444), (452, 540), (424, 652), (333, 634), (345, 560), (357, 497), (365, 457)]


def mont(size, weight):
    f = ImageFont.truetype(str(RUN / "font/Montserrat.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def tint(im):
    a = np.asarray(im).astype(float)
    poly = Image.new("L", im.size, 0); ImageDraw.Draw(poly).polygon(GLASS, fill=255)
    rgb = a / 255; mx, mn = rgb.max(-1), rgb.min(-1); sat = (mx - mn) / np.maximum(mx, 1e-6)
    water = (sat < 0.30) & (mx > 0.62)                 # clear water / ice / glass, not skin, hair, lemon or strawberry
    m = np.asarray(poly).astype(float) / 255 * water
    m = np.asarray(Image.fromarray((m * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.2))).astype(float) / 255 * 0.66
    lum = (a @ [0.299, 0.587, 0.114])[..., None] / 255
    target = BABY * (0.55 + 0.45 * lum)                 # keeps ice/highlight structure
    return Image.fromarray(np.clip(a * (1 - m[..., None]) + target * m[..., None], 0, 255).astype("uint8"))


def build_layer():
    L = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    s = 96
    while d.textlength("RITUAL.", font=mont(s, "ExtraBold")) > 900 and s > 10: s -= 2
    d.text((60, 44), "MALI", font=mont(s, "ExtraBold"), fill=BURG + (255,))
    d.text((60, 44 + int(s * 1.08)), "RITUAL.", font=mont(s, "ExtraBold"), fill=BURG + (255,))
    ImageDraw.Draw(L).rounded_rectangle((40, 1088, 640, 1262), 28, fill=(251, 243, 242, 64))   # very subtle blush panel for legibility
    d.text((64, 1106), "NAPITAK ZA LJEPOTU.", font=mont(40, "ExtraBold"), fill=BURG + (255,))
    d.text((64, 1164), "Ljepota počinje iznutra.", font=mont(30, "Bold"), fill=BURG + (255,))
    d.text((64, 1208), "Tvoj svakodnevni beauty ritual.", font=mont(30, "Bold"), fill=BURG + (255,))
    return L


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    base = Image.open(SRC).convert("RGB")
    t = tint(base); t.save(OUT / "start_frame_clean_1080x1350.png")
    L = build_layer(); L.save(OUT / "text_layer_1080x1350.png")
    Image.alpha_composite(t.convert("RGBA"), L).convert("RGB").save(OUT / "preview_frame_with_text.png")
    Image.fromarray(np.hstack([np.asarray(base)[400:680, 300:500], np.asarray(t)[400:680, 300:500]])).resize((1200, 840)).save(OUT / "drink_tint_before_after_REVIEW.png")
    diff = np.abs(np.asarray(base).astype(int) - np.asarray(t).astype(int)).sum(-1) > 0
    ys, xs = np.nonzero(diff); print("changed bbox", xs.min(), ys.min(), xs.max(), ys.max(), "px", int(diff.sum()))
