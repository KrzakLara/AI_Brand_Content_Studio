"""BEFORE/AFTER close-ups (nearest-neighbour zoom, real pixels). Usage: qa_sheet.py <before.png> <after.png> <out.png>"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
RUN = Path(__file__).resolve().parents[4] / "runs/hero-proof"
REGIONS = [("top-left corner + left tear notch", (380, 250, 440, 310)), ("right tear notch + top-right corner", (846, 250, 906, 310)),
           ("bottom-left corner / contact", (380, 1020, 440, 1070)), ("seal repair (shaker handle)", (846, 370, 906, 430)),
           ("glass edge (white band rows)", (830, 500, 890, 560)), ("reflection seam beside the glass", (820, 1150, 900, 1210))]
Z = 6
b, a, out = (Image.open(RUN / n if not Path(n).is_absolute() else n).convert("RGB") for n in sys.argv[1:3]) if False else (None, None, None)
before, after = Image.open(sys.argv[1]).convert("RGB"), Image.open(sys.argv[2]).convert("RGB")
cw, ch = 80 * Z, 60 * Z
sheet = Image.new("RGB", (2 * cw + 30, len(REGIONS) * (ch + 34)), (18, 16, 16))
d = ImageDraw.Draw(sheet)
f = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
for i, (name, (x0, y0, x1, y1)) in enumerate(REGIONS):
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    box = (cx - 40, cy - 30, cx + 40, cy + 30)
    y = i * (ch + 34)
    d.text((8, y + 4), f"{name}   (left: BEFORE   right: AFTER, {Z}x)", font=f, fill=(255, 140, 50))
    sheet.paste(before.crop(box).resize((cw, ch), Image.NEAREST), (0, y + 30))
    sheet.paste(after.crop(box).resize((cw, ch), Image.NEAREST), (cw + 30, y + 30))
sheet.save(sys.argv[3]); print(sheet.size)
