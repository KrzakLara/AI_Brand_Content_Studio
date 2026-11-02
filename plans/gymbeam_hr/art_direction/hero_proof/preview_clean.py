"""Clean typography preview on the corrected composite B (no QA banner, no footer, no scrim: headline only). Free: no network, no API. Run from the repository root.
Reuses refine.py's pipeline with its typography step disabled, then sets the headline. Every other file stays untouched."""
import importlib.util
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
RUN = ROOT / "runs/hero-proof"
spec = importlib.util.spec_from_file_location("rf", Path(__file__).with_name("refine.py"))
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)
rf.typography = lambda im, label: im                       # the QA banner and the old text are NOT part of the clean design

HEADLINE = ("SVAKA SERIJA", "POČINJE ODLUKOM.")
BONE, ORANGE = (242, 237, 232), (255, 140, 50)


def tracked(d, xy, text, font, fill, track):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + track
    return x


def main():
    gen = Image.open(RUN / "candidate_A.png").convert("RGB")
    ref = Image.open(RUN / "edit_canvas.png")
    glass, _ = rf.glass_edge_mask(gen, ref)
    patch = rf.build_patch_mask() if hasattr(rf, "build_patch_mask") else None
    # same construction as refine.main() for B
    k = rf.GW / rf.FW
    patch = Image.new("L", (rf.GW, rf.GH), 0)
    ImageDraw.Draw(patch).polygon([(x * k, y * k) for x, y in [(861, 382), (897, 382), (897, 421), (882, 421), (869, 411), (862, 404)]], fill=255)
    from PIL import ImageFilter
    patch = patch.filter(ImageFilter.GaussianBlur(1.5))
    plate = gen.copy()
    plate.paste(gen.crop((rf.X0 - rf.DX, rf.Y0, rf.X0, rf.GH)).transpose(Image.FLIP_LEFT_RIGHT), (rf.X0, rf.Y0))
    plate.paste(gen.crop((rf.X0, rf.Y0, rf.GW - rf.DX, rf.GH)), (rf.X0 + rf.DX, rf.Y0))
    glass_b = Image.new("L", (rf.GW, rf.GH), 0)
    glass_b.paste(glass.crop((0, 0, rf.GW - rf.DX, rf.GH)), (rf.DX, 0))
    im, _, _ = rf.build(plate, gen, glass_b, patch, "")
    im = im.convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    fh = ImageFont.truetype(str(RUN / "font/extras/ttf/Inter-Medium.ttf"), 50)
    d.rectangle((94, 78, 94 + 84, 81), fill=ORANGE + (255,))                  # accent line above the headline
    tracked(d, (92, 104), HEADLINE[0], fh, BONE + (255,), 7)
    x = tracked(d, (92, 172), HEADLINE[1][:-1], fh, BONE + (255,), 7)
    d.text((x, 172), ".", font=fh, fill=ORANGE + (255,))                       # the full stop carries the brand accent
    out = RUN / "preview_final_typography_B_clean_no_footer_1080x1350.png"
    im.convert("RGB").save(out)
    print(out, im.size)


if __name__ == "__main__":
    main()
