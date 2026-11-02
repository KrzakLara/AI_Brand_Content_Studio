"""Slide 5 v3 preview (no network, no spend): calm-hair start frame + final typography (headline NAPITAK ZA LJEPOTU, two bottom lines)."""
import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

spec = importlib.util.spec_from_file_location("p5", Path(__file__).with_name("slide5_video_prep.py"))
p5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p5)
OUT, BURG = p5.OUT, p5.BURG + (255,)
L = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
HEAD = "NAPITAK ZA LJEPOTU"
s = 120
while d.textlength(HEAD, font=p5.mont(s, "ExtraBold")) > 960 and s > 10: s -= 1       # one line, above her head (head top is at y~175)
d.text((60, 52), HEAD, font=p5.mont(s, "ExtraBold"), fill=BURG)
d.rounded_rectangle((40, 1142, 780, 1262), 28, fill=(251, 243, 242, 64))                 # very subtle blush panel
d.text((64, 1160), "Ljepota počinje iznutra.", font=p5.mont(38, "Bold"), fill=BURG)
d.text((64, 1210), "Njeguj svoju kožu, kosu i nokte.", font=p5.mont(38, "Bold"), fill=BURG)
L.save(OUT / "text_layer_v3_1080x1350.png")
base = Image.open(OUT / "start_frame_hair_calmed_1080x1350.png").convert("RGBA")
Image.alpha_composite(base, L).convert("RGB").save(OUT / "preview_v3_final_typography.png")
print("headline px", s, "bbox", L.getbbox())
