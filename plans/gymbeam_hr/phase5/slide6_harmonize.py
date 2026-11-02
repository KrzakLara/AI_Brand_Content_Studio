"""Slide 6 harmonised CANDIDATE (zero cost, local, deterministic). Reads the approved current final; writes runs/colla-pink/carousel_final/slide6_HARMONIZED_CANDIDATE.png only.
1. Background pink around the jar (scene area x 290..960, y < 1020; pink hue, not fruit/leaf/text/ice/jar): saturation x0.80 at the jar, feathered out with distance, plus a soft blush glow
   (blend toward #fde4e8 up to 22%) centred behind the jar, so jar and backdrop share one pink-on-pink palette while the dusty-rose jar stays darker and distinct.
2. Jar: label colour untouched in hue/saturation; a gentle cylindrical luminance shading (+4% on the lit left, -4% on the right, -3% toward the bottom) restores dimension. White print
   and lid/base are excluded by the same pink-chroma mask as the colour fix."""
import colorsys, json, math
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter
ROOT = Path(__file__).resolve().parents[3]; F = ROOT / "runs/colla-pink/carousel_final"
src = Image.open(F / "slide6_odaberi_svoj_okus_FINAL.png").convert("RGB"); W, H = src.size
px = src.load(); out = src.copy(); op = out.load()
mask_jar = Image.open(F / "slide6_color_mask.png"); mj = mask_jar.load()          # pink label region of the jar (from the colour fix)
# jar footprint (any non-label part: lid, base) : dilated label mask bbox
JCX, JCY = 556, 690
fp = Image.new("L", (W, H), 0); ImageDraw.Draw(fp).rounded_rectangle((330, 410, 782, 940), 30, fill=255); fp = fp.filter(ImageFilter.MaxFilter(15)); fpp = fp.load()
BLUSH = (253, 228, 232)
changed_bg = 0
for y in range(380, 1020):
    for x in range(290, 960):
        if fpp[x, y] or mj[x, y]:
            continue
        r, g, b = px[x, y]
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        hd = h * 360
        if not ((hd >= 325 or hd <= 12) and 0.10 <= s <= 0.55 and v >= 0.78):
            continue                                                  # fruit, leaves, lemon, strawberry, ice, text, shadows are not background pink
        d = math.hypot((x - JCX) / 420.0, (y - JCY) / 430.0)
        w = max(0.0, 1 - d) ** 1.2
        if w <= 0.01:
            continue
        s2 = s * (1 - 0.42 * w)
        glow = 0.38 * max(0.0, 1 - math.hypot((x - JCX) / 300.0, (y - (JCY - 20)) / 320.0)) ** 1.5
        r2, g2, b2 = [int(c * 255) for c in colorsys.hsv_to_rgb(h, s2, min(1.0, v + 0.01 * w))]
        r2, g2, b2 = [int(c * (1 - glow) + k * glow) for c, k in zip((r2, g2, b2), BLUSH)]
        op[x, y] = (r2, g2, b2); changed_bg += 1
# jar dimension shading inside the pink label mask only
lab_changed = 0
for y in range(500, 900):
    for x in range(330, 790):
        wv = mj[x, y] / 255
        if wv:
            u = (x - 336) / 444.0; vv = (y - 520) / 370.0
            f = 1 + 0.06 * (1 - 2 * u) - 0.04 * vv + 0.05 * math.exp(-((u - 0.16) / 0.07) ** 2)
            r, g, b = px[x, y]
            op[x, y] = tuple(max(0, min(255, int(round(c * (1 + wv * (f - 1)))))) for c in (r, g, b)); lab_changed += 1
# ambient pink bounce on the NEUTRAL parts of the jar (silver lid, glass neck band, silver base): blend 16% toward the scene's pink, weighted by how neutral the pixel is
BOUNCE = (252, 196, 212); bounce_px = 0
for y in range(410, 945):
    for x in range(330, 786):
        if not fpp[x, y] or mj[x, y]:
            continue
        r, g, b = op[x, y]
        if max(r, g, b) - min(r, g, b) > 26 or max(r, g, b) < 150:
            continue                                                  # not neutral silver/white (print, label, fruit)
        if y < 600 or y > 880:                                        # lid + neck above, base below (the label's own white print lies in between and is excluded by rows)
            k = 0.16 * (1 - (y - 410) / 300.0 * 0.5 if y < 600 else 1.0)
            op[x, y] = tuple(int(c * (1 - k) + t * k) for c, t in zip((r, g, b), BOUNCE)); bounce_px += 1
# edge light wrap: the outer 5 px of the jar take 22% of the local backdrop colour so the contour belongs to the scene
foot = fp.filter(ImageFilter.MinFilter(3)); inner = foot.filter(ImageFilter.MinFilter(11))
wrap = ImageChops.subtract(foot, inner).filter(ImageFilter.GaussianBlur(1.5)); wp_ = wrap.load(); bgblur = out.filter(ImageFilter.GaussianBlur(14)); bp_ = bgblur.load(); wrapped = 0
for y in range(410, 945):
    for x in range(330, 786):
        wv = wp_[x, y] / 255
        if wv > 0.05 and mj[x, y] == 0 or (wv > 0.05 and mj[x, y]):
            r, g, b = op[x, y]; br, bg_, bb = bp_[x, y]
            k = 0.22 * wv
            if abs(x - 336) < 14 or abs(x - 780) < 14:                # only the left/right contours (top/bottom edges carry lid and base)
                op[x, y] = (int(r * (1 - k) + br * k), int(g * (1 - k) + bg_ * k), int(b * (1 - k) + bb * k)); wrapped += 1
# floor: a soft rose reflection/occlusion under the jar's base (multiply up to 10%, elliptical, feathered)
refl = Image.new("L", (W, H), 0); ImageDraw.Draw(refl).ellipse((360, 905, 770, 985), fill=255); refl = refl.filter(ImageFilter.GaussianBlur(18)); rp_ = refl.load()
for y in range(900, 1010):
    for x in range(340, 790):
        if rp_[x, y] and not fpp[x, y]:
            r, g, b = op[x, y]; hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if (hh * 360 >= 325 or hh * 360 <= 12) and ss < 0.6 and vv > 0.7:
                k = 0.10 * rp_[x, y] / 255
                op[x, y] = (int(r * (1 - k * 0.9)), int(g * (1 - k * 1.3)), int(b * (1 - k * 1.1)))
out.save(F / "slide6_HARMONIZED_CANDIDATE.png")
diff = ImageChops.difference(src, out).convert("L").point(lambda v: 255 if v > 0 else 0)
rep = {"bounce_px": bounce_px, "edge_wrap_px": wrapped, "background_px_adjusted": changed_bg, "label_px_adjusted": lab_changed, "bbox_changed": diff.getbbox(),
       "headline_zone_changed": diff.crop((0, 0, 1080, 380)).getbbox() is not None, "bottom_flavours_zone_changed": diff.crop((0, 1020, 1080, 1350)).getbbox() is not None}
(F / "slide6_harmonize_report.json").write_text(json.dumps(rep, indent=1)); print(json.dumps(rep))
