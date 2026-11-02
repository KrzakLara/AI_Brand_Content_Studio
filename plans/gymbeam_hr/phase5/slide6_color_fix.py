"""Slide 6 final colour correction (zero cost, no API): only the jar's pink label region is touched.
Target = the official packshot's plain label colour (median over a text-free area, identical on the mango and strawberry packshots: 195,155,161 / 195,150,157 by rows).
A per-channel gain, equal for every pixel, moves the label's median to the target; pixel-to-pixel shading (the scene lighting on the jar) is therefore preserved.
Mask = real jar footprint (eroded 3 px) x pink-chroma weight (white print, silver lid/base, strawberry, ice and lemon are excluded by colour/position)."""
import importlib.util, json, statistics as st
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageDraw
ROOT = Path(__file__).resolve().parents[3]; RUN = ROOT / "runs/colla-pink"; F = RUN / "carousel_final"
spec = importlib.util.spec_from_file_location("rt", Path(__file__).with_name("retouch_cover2.py")); rt = importlib.util.module_from_spec(spec); spec.loader.exec_module(rt)
rt.JAR = RUN / "jars/jar_strawberry.png"
SRC = F / "slide6_odaberi_svoj_okus_FINAL_before_color.png"
OUT = F / "slide6_odaberi_svoj_okus_FINAL.png"
if not SRC.is_file():
    SRC.write_bytes((F / "slide6_odaberi_svoj_okus_FINAL.png").read_bytes())      # keep the previous version untouched
im = Image.open(SRC).convert("RGB")
# jar footprint in final coordinates (same transform as slide6_final.py)
j = rt.clean_jar(); h = 517; w = round(j.width * h / j.height); j = j.resize((w, h), Image.LANCZOS)
a = Image.new("L", (1092, 1440), 0); a.paste(j.getchannel("A"), ((350 + 781) // 2 - w // 2, 455))
foot = a.resize((1080, 1424), Image.LANCZOS).crop((0, 30, 1080, 1380)).point(lambda v: 255 if v > 250 else 0).filter(ImageFilter.MinFilter(7))
sc = 1080 / 1092
def poly(pts): return [(x * sc, y * sc - 30) for x, y in pts]
excl = Image.new("L", im.size, 0); d = ImageDraw.Draw(excl)
for p in ([(190, 860), (215, 830), (300, 805), (370, 808), (410, 850), (412, 900), (385, 945), (320, 975), (250, 970), (205, 930)],
          [(404, 925), (440, 920), (535, 930), (532, 985), (480, 1003), (412, 995), (404, 960)], [(703, 902), (760, 880), (857, 905), (854, 975), (790, 995), (722, 990), (703, 940)]):
    d.polygon(poly(p), fill=255)
excl = excl.filter(ImageFilter.MaxFilter(9))
px = im.load(); wp = Image.new("L", im.size, 0); wq = wp.load(); fp = foot.load(); ep = excl.load()
vals = []
for y in range(500, 900):
    for x in range(330, 790):
        if fp[x, y] and not ep[x, y]:
            r, g, b = px[x, y]; c = r - g
            wt = max(0.0, min(1.0, (c - 10) / 12.0)) if c < 70 else 0.0
            if wt > 0:
                wq[x, y] = int(255 * wt)
                if wt >= 1.0: vals.append((r, g, b))
cur = tuple(int(st.median(v[i] for v in vals)) for i in range(3))
tgt = (195, 150, 157)           # official packshot plain label (rows 420-480 of the packshot, text-free)
gain = [tgt[i] / cur[i] for i in range(3)]
out = im.copy(); op = out.load()
for y in range(500, 900):
    for x in range(330, 790):
        wv = wq[x, y] / 255
        if wv:
            r, g, b = px[x, y]
            op[x, y] = tuple(min(255, int(round(v * (1 + wv * (gn - 1))))) for v, gn in zip((r, g, b), gain))
out.save(OUT)
diff = ImageChops.difference(im, out).convert("L"); m = wp.point(lambda v: 255 if v > 0 else 0)
outside = ImageChops.multiply(diff, ImageChops.invert(m))
rep = {"current_label_median": cur, "target_label_median": tgt, "gain_rgb": [round(g, 3) for g in gain], "changed_px_inside_mask": int(sum(1 for v in diff.getdata() if v > 0)),
       "changed_px_outside_mask": int(sum(1 for v in outside.getdata() if v > 0)), "max_diff_outside": outside.getextrema()[1], "mask_px": int(sum(1 for v in m.getdata() if v))}
(F / "slide6_color_fix_report.json").write_text(json.dumps(rep, indent=1)); wp.save(F / "slide6_color_mask.png"); print(json.dumps(rep))
