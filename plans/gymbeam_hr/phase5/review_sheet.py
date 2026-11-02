"""Human review document for a cover candidate (zero cost). Usage: review_sheet.py <final.png> <raw.png> <outdir> <jar_x> <jar_y> <jar_w> <jar_h>
Pages: 1 overview (original vs final side by side + Instagram-size previews), 2 every hand-jar contact at 100% and 300%, 3 lid, base and label.
Red boxes with numbers mark places a reviewer should look at; the legend states what was seen there. No metric is used as a pass/fail."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
final, raw, out = Image.open(sys.argv[1]).convert("RGB"), Image.open(sys.argv[2]).convert("RGB").resize((1080, 1350), Image.LANCZOS), Path(sys.argv[3])
jx, jy, jw, jh = map(int, sys.argv[4:8])
F = lambda s, b=False: ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if b else "C:/Windows/Fonts/segoeui.ttf", s)
BG, INK, RED = (28, 22, 25), (240, 232, 234), (255, 70, 90)


def page(w, h):
    im = Image.new("RGB", (w, h), BG)
    return im, ImageDraw.Draw(im)


def box(d, xy, n, color=RED, off=(0, 0)):
    x0, y0, x1, y1 = xy
    d.rectangle((x0 + off[0], y0 + off[1], x1 + off[0], y1 + off[1]), outline=color, width=3)
    d.rectangle((x0 + off[0], y0 + off[1] - 22, x0 + off[0] + 22, y0 + off[1]), fill=color)
    d.text((x0 + off[0] + 6, y0 + off[1] - 21), str(n), font=F(16, True), fill=(255, 255, 255))


# ---------------- page 1: overview
p, d = page(2300, 1560)
d.text((20, 10), "Slide 1 cover: original model output (left) and final authentic-packaging composite (right), full frame", font=F(26, True), fill=INK)
p.paste(raw.resize((1080 * 1, 1350)), (20, 60)); p.paste(final, (1120, 60))
d.text((20, 1415), "LEFT: raw model output (jar and label are AI-drawn, discarded)", font=F(20), fill=INK); d.text((1120, 1415), "RIGHT: final, real jar composited, typography by code", font=F(20), fill=INK)
d.text((20, 1450), "Instagram feed size (390 px wide) and profile-grid thumbnail:", font=F(20, True), fill=INK)
p.paste(final.resize((390, 488), Image.LANCZOS), (20, 1480 - 0)) if False else None
for n, (x0, y0, x1, y1) in enumerate([(78, 62, 580, 372), (408, 813, 669, 1112), (330, 330, 770, 700)], 1):
    box(d, (1120 + x0, 60 + y0, 1120 + x1, 60 + y1), n)
d.text((1120, 1445), "1 headline block close to the hair; subtitle small    2 jar small in frame (24% of width)    3 face: AI-portrait skin smoothness", font=F(17), fill=RED)
page1 = p
# instagram previews on a separate strip appended below
ig, igd = page(2300, 700)
igd.text((20, 10), "Actual Instagram-size preview: feed width 390 px (left), 2x of it (middle), profile grid thumbnail 3:4 at 120 px (right)", font=F(22, True), fill=INK)
ig.paste(final.resize((390, 488), Image.LANCZOS), (20, 60)); ig.paste(final.resize((780, 975), Image.LANCZOS).crop((0, 0, 780, 640)), (440, 60))
ig.paste(final.resize((120, 150), Image.LANCZOS), (1260, 60)); igd.text((1260, 215), "grid thumbnail", font=F(16), fill=INK)
igd.text((1440, 60), "What reads at feed size: headline, face, jar and hands.\nWhat does NOT read: the ingredient list, net weight and flavour\nline on the jar (they are tiny); the three-line subtitle is small.", font=F(20), fill=INK)
pp = Image.new("RGB", (2300, 1560 + 700), BG); pp.paste(page1.crop((0, 0, 2300, 1450)), (0, 0)); pp.paste(ig, (0, 1450)); pp.save(out / "page1_overview_instagram_size.png")

NOTES = {"L-top": (0.2, 0.15, 0.8, 0.75, 1, "OBSERVED/CHECK: left fingertip meets the lid neck. The real lid sits on top of\nthe model's hand; confirm the depth ordering (finger in front or behind) looks right."),
         "L-low": (0.70, 0.55, 1.0, 0.82, 2, "ARTIFACT: stair-stepped white wedge at the left base corner (matte notch,\nabout 3 px at 100%). Visible at 300%."),
         "R-top": (0.38, 0.25, 0.80, 0.75, 3, "OBSERVED/CHECK: right fingertip overlaps the jar neck; the real jar is drawn over the\nmodel's, so a finger that was in front of the jar edge may now read as behind it."),
         "R-mid": (0.40, 0.0, 0.56, 1.0, 4, "ARTIFACT: a thin lighter band runs along the jar's right edge beside the hand: probably the model's own jar edge showing past the real jar (a duplicate edge), plus 1-2 px stair-steps."),
         "R-low": (0.0, 0.55, 0.30, 0.95, 5, "OBSERVED: light base ring ends abruptly where the heel of the hand starts;\nedge of the base is hard against the skin.")}
# ---------------- page 2: hand-jar contacts at 100% and 300%
contacts = [
    ("L-top: left fingertips against the lid / neck", (jx - 55, jy - 15, jx + 55, jy + 85)),
    ("L-mid: left palm edge along the label", (jx - 60, jy + 85, jx + 50, jy + 185)),
    ("L-low: left heel of hand and base corner", (jx - 70, jy + 190, jx + 40, jy + jh + 20)),
    ("R-top: right fingertips against the lid / neck", (jx + jw - 55, jy - 15, jx + jw + 55, jy + 85)),
    ("R-mid: right palm edge along the label", (jx + jw - 50, jy + 85, jx + jw + 60, jy + 185)),
    ("R-low: right heel of hand and base corner", (jx + jw - 40, jy + 190, jx + jw + 70, jy + jh + 20)),
]
Z = 3
cw, ch = 110, 100
p2, d2 = page(1900, 80 + len(contacts) * (ch * Z + 40))
d2.text((20, 8), "Every hand-to-jar contact at 300% (large: raw left, final right) and 100% (small, same order). Red = look here.", font=F(22, True), fill=INK)
y = 52
for name, (x0, y0, x1, y1) in contacts:
    c = (x0 + x1) // 2, (y0 + y1) // 2
    b = (c[0] - cw // 2, c[1] - ch // 2, c[0] + cw // 2, c[1] + ch // 2)
    d2.text((20, y), name, font=F(18, True), fill=(255, 170, 190))
    for k, im in enumerate((raw, final)):
        t = im.crop(b)
        p2.paste(t.resize((cw * Z, ch * Z), Image.LANCZOS), (20 + k * (cw * Z + 20), y + 26))
        p2.paste(t, (20 + 2 * (cw * Z + 20) + k * (cw + 10), y + 26))
    note = NOTES.get(name[:5])
    if note:
        rx0, ry0, rx1, ry1, n, text = note
        ox, oy = 20 + (cw * Z + 20), y + 26
        box(d2, (ox + int(rx0 * cw * Z), oy + int(ry0 * ch * Z), ox + int(rx1 * cw * Z), oy + int(ry1 * ch * Z)), n)
        d2.multiline_text((1000, y + 40), f"{n}  {text}", font=F(19), fill=RED, spacing=6)
    else:
        d2.text((1000, y + 40), "No artifact seen at this contact at 300% (human check still required).", font=F(19), fill=(150, 220, 150))
    y += ch * Z + 40
p2.save(out / "page2_hand_contacts_100_300.png")

# ---------------- page 3: lid, base, label (final only, 100% / 300%), with annotations
p3, d3 = page(1800, 1700)
d3.text((20, 8), "Lid, base and label of the final (real jar). Top: lid 100% + 300%. Middle: base 100% + 300%. Bottom: label 100% + 300%. Red boxes = look here.", font=F(22, True), fill=INK)
sections = [("Lid and neck", (jx - 10, jy - 10, jx + jw + 10, jy + 70)), ("Base", (jx - 10, jy + jh - 55, jx + jw + 10, jy + jh + 15)), ("Label text block", (jx + 20, jy + 175, jx + jw - 20, jy + jh - 30))]
y = 50
for name, b in sections:
    w, h = b[2] - b[0], b[3] - b[1]
    d3.text((20, y), name + f"  (100% = {w}x{h} px as delivered; 300% below)", font=F(18, True), fill=(255, 170, 190))
    t = final.crop(b)
    p3.paste(t, (20, y + 26))
    big = t.resize((min(w * 3, 1760), h * 3), Image.LANCZOS if name == "Label text block" else Image.NEAREST) if w * 3 <= 1760 else t.resize((1760, round(h * 1760 / w)), Image.LANCZOS)
    p3.paste(big, (20, y + 26 + h + 12))
    by = y + 26 + h + 12
    if name == "Lid and neck":
        box(d3, (20 + int(.93 * big.width), by + int(.25 * big.height), 20 + big.width, by + int(.75 * big.height)), 1)
        d3.text((880, by + 20), "1 fingertip meets the lid neck: check depth ordering (see page 2)", font=F(18), fill=RED)
    if name == "Base":
        box(d3, (20, by + int(.12 * big.height), 20 + int(.20 * big.width), by + int(.58 * big.height)), 2)
        box(d3, (20 + int(.86 * big.width), by + int(.08 * big.height), 20 + big.width, by + int(.72 * big.height)), 3)
        d3.text((880, by + 20), "2 stair-stepped notch at the left base corner (ARTIFACT)\n3 jagged right base edge (ARTIFACT)\nThe packshot's dark base line was trimmed by 4 px.", font=F(18), fill=RED)
    if name == "Label text block":
        box(d3, (20 + int(.22 * big.width), by + int(.08 * big.height), 20 + int(.88 * big.width), by + int(.92 * big.height)), 4)
        d3.text((720, by + 20), "4 label: real packshot text, readable at 300%; at 100% (small image left) the\ningredient boxes and net weight are barely readable: tiny in the frame.", font=F(18), fill=RED)
    y += 26 + h + 12 + big.height + 30
p3 = p3.crop((0, 0, 1800, min(1700, y)))
p3.save(out / "page3_lid_base_label.png")
print("pages:", [str(x) for x in out.glob("page*.png")])
