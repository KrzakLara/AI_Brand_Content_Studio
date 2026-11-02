"""Slide 5 v2 preview (no network, no spend): hair-calmed start frame + new 4-line bottom copy as the fixed typography layer."""
import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

spec = importlib.util.spec_from_file_location("p5", Path(__file__).with_name("slide5_video_prep.py"))
p5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p5)
OUT = p5.OUT
L = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
s = 96
while d.textlength("RITUAL.", font=p5.mont(s, "ExtraBold")) > 900 and s > 10: s -= 2
d.text((60, 44), "MALI", font=p5.mont(s, "ExtraBold"), fill=p5.BURG + (255,))
d.text((60, 44 + int(s * 1.08)), "RITUAL.", font=p5.mont(s, "ExtraBold"), fill=p5.BURG + (255,))
d.rounded_rectangle((40, 1062, 760, 1262), 28, fill=(251, 243, 242, 64))   # very subtle blush panel
y = 1080
d.text((64, y), "NAPITAK ZA LJEPOTU.", font=p5.mont(40, "ExtraBold"), fill=p5.BURG + (255,))
for i, line in enumerate(("Ljepota počinje iznutra.", "Njeguj svoju kožu, kosu i nokte.", "Tvoj svakodnevni beauty ritual.")):
    d.text((64, y + 56 + i * 44), line, font=p5.mont(30, "Bold"), fill=p5.BURG + (255,))
L.save(OUT / "text_layer_v2_1080x1350.png")
base = Image.open(OUT / "start_frame_hair_calmed_1080x1350.png").convert("RGBA")
Image.alpha_composite(base, L).convert("RGB").save(OUT / "preview_v2_hair_calmed_with_text.png")
