"""Hero v2 (zero cost: no network, no API, no key). Run from the repository root:  python plans/gymbeam_hr/art_direction/hero_proof/hero_v2.py

What is new against refine.py (every earlier file stays untouched):
 1. Pouch edge = a real matte: continuous alpha from the source's own edge pixels (known backdrop colour B, known pouch colour F), the backdrop colour
    removed from the edge pixels (no pale fringe), no square min/max filters (they chamfered corners and stair-stepped the left edge).
 2. Source-derived seal repair: the shaker handle on the seal is replaced by REAL seal rows cloned from 51 source px above (the dot grid repeats every
    3 px, so 17 whole periods keep the grid aligned). Only the small part of the handle that lay over plain orange cloth takes the model's colour.
 3. Light wrap: a few edge pixels pick up the local scene colour (normalised blur of the plate OUTSIDE the pouch), strength 0.22, 3 px deep.
 4. Glass: left edge refined per row (gradient search around the fitted line); reflection rows blend the moved glass in over 30 px (no seam).
 5. Fidelity is MEASURED (CIE76 colour difference, silhouette, detail correlation) and written to hero_v2_fidelity.json.
"""
import json
import math
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
import importlib.util  # noqa: E402

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont  # noqa: E402

RUN = ROOT / "runs/hero-proof"
spec = importlib.util.spec_from_file_location("rf", Path(__file__).with_name("refine.py"))
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)
FW, FH, GW, GH, PX, PY, PW, PH = rf.FW, rf.FH, rf.GW, rf.GH, rf.PX, rf.PY, rf.PW, rf.PH
SRC = RUN / "source/creatine-monohydrate-unflavoured-lifestyle.png"
EXPECTED_SHA = "cc19b0cd800dc8bd2fba06eec193335192d1e3ac02b601dd24098628e92358e0"
L, T, R, B, RING, SHAKER_Y = 219, 121, 806, 1056, 14, 270
SEAL_X0, SEAL_X1, HANDLE_Y0, HANDLE_Y1, CLONE_DY = 777, 806, 270, 326, 51   # seal strip columns, handle rows, clone offset (17 x 3 px)
LUG_X0, LUG_Y0, LUG_Y1, LUG_SRC_Y0 = 786, 444, 548, 436
BODY_X0 = 762                                                                 # handle part over plain orange cloth: x 762..782 (the (R) ends at x 769, y 303..322)
REG = (L - RING - 2, T - RING - 2, R + RING + 3, B + 3)                       # working region of the source


def nblur(img, w, r):
    """Normalised blur: local mean of img over the pixels where weight w is on."""
    num = Image.composite(img, Image.new(img.mode, img.size), w).filter(ImageFilter.GaussianBlur(r))
    return num.load(), w.filter(ImageFilter.GaussianBlur(r)).load()


def source_layer():
    import hashlib
    if hashlib.sha256(SRC.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise SystemExit("source photograph hash mismatch")
    full = Image.open(SRC).convert("RGB")
    im = full.crop(REG)
    ox, oy = REG[0], REG[1]
    W, H = im.size
    px = im.load()

    def inreg(x, y):
        return 0 <= x < W and 0 <= y < H
    # --- 1. backdrop flags: smooth-colour flood fill from the region border (right side below the shaker row is not backdrop)
    bg = [[False] * W for _ in range(H)]
    q = deque()
    for y in range(H):
        for x in range(W):
            gx, gy = x + ox, y + oy
            if (x in (0, W - 1) or y == 0) and not (gy >= SHAKER_Y and gx >= R - 1):
                bg[y][x] = True
                q.append((x, y))
    while q:
        x, y = q.popleft()
        a = px[x, y]
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if inreg(nx, ny) and not bg[ny][nx]:
                gx, gy = nx + ox, ny + oy
                if gy >= B or (gy >= SHAKER_Y and gx >= R - 1):
                    continue
                b = px[nx, ny]
                if abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) <= 9:
                    bg[ny][nx] = True
                    q.append((nx, ny))
    bgm = Image.new("L", (W, H), 0)
    nbm = Image.new("L", (W, H), 0)
    bp, np_ = bgm.load(), nbm.load()
    for y in range(H):
        for x in range(W):
            gx, gy = x + ox, y + oy
            inside_rect = L - 8 <= gx < R + RING and T - 8 <= gy < B
            if bg[y][x]:
                bp[x, y] = 255
            elif inside_rect and not (gy >= SHAKER_Y and gx >= R) and not (gy >= B - 14 and gx < L - 2):
                np_[x, y] = 255
    # --- 2. interior (>= 3 px from the backdrop) and the unknown band
    interior = nbm.filter(ImageFilter.MinFilter(7))
    ip = interior.load()
    bn, bd = nblur(im, bgm, 5)
    fn, fd = nblur(im, interior, 3)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    op = out.load()
    for y in range(H):
        for x in range(W):
            gx, gy = x + ox, y + oy
            if np_[x, y] == 0:
                continue
            c = px[x, y]
            if ip[x, y] or (gy >= SHAKER_Y and gx >= R - 7):
                op[x, y] = c + (255,)
                continue
            if bd[x, y] < 5 or fd[x, y] < 5:
                op[x, y] = c + (255,)
                continue
            Bc = [bn[x, y][k] * 255 / bd[x, y] for k in range(3)]
            Fc = [fn[x, y][k] * 255 / fd[x, y] for k in range(3)]
            d = [Fc[k] - Bc[k] for k in range(3)]
            dd = sum(v * v for v in d)
            if dd < 700:                                         # pouch colour too close to the backdrop to separate: keep as is
                op[x, y] = c + (255,)
                continue
            a = max(0.0, min(1.0, sum((c[k] - Bc[k]) * d[k] for k in range(3)) / dd))
            if a < 0.04:
                continue
            if a > 0.5:                                          # remove the backdrop colour from the edge pixel
                col = tuple(int(max(0, min(255, (c[k] - (1 - a) * Bc[k]) / a))) for k in range(3))
            else:
                col = tuple(int(Fc[k]) for k in range(3))
            op[x, y] = col + (int(round(a * 255)),)
    for gy in range(B - 14, B + 1):
        for gx in range(L - 4, L + 10):
            x, y = gx - ox, gy - oy
            r, g, b, a = op[x, y]
            if a and max(r, g, b) - min(r, g, b) < 45 and (r + g + b) / 3 > 110 and gx < L + 5:
                op[x, y] = (r, g, b, 0)
    # --- 3. straight right edge below the shaker row: edge profile measured on clean rows above (140..260)
    prof = {}
    for gx in range(R - 3, R + 4):
        vals = [op[gx - ox, gy - oy][3] for gy in range(140, 260) if 0 <= gx - ox < W]
        prof[gx] = sum(vals) / len(vals) if vals else 0
    for gy in range(SHAKER_Y, B):                                  # real colours up to R-4; the last columns take column R-4's colour with the measured alpha
        for gx in range(R - 3, R + 4):
            x, y = gx - ox, gy - oy
            op[x, y] = px[R - 4 - ox, y] + (int(round(prof[gx])),) if prof[gx] > 4 else (0, 0, 0, 0)
    # --- 4. SEAL REPAIR from real seal rows (same columns, 51 rows up = 17 dot periods); body part is left for the model's colour
    for gy in range(HANDLE_Y0, HANDLE_Y1):
        for gx in range(SEAL_X0, R - 1):
            x, y = gx - ox, gy - oy
            sx, sy = x, y - CLONE_DY
            r, g, b, a = op[x, y]
            op[x, y] = op[sx, sy][:3] + (a,)
    # --- 4b. SECOND shaker contact: a translucent shaker piece over the seal strip beside the white band (rows 444..547). Clean seal rows above it (436..444, below the band edge)
    #     are tiled downward with a 9-row period (3 dot periods), so the grid stays aligned. Columns 786..R-2 only (the printed band ends at x~780).
    for gy in range(LUG_Y0, LUG_Y1):
        sy = LUG_SRC_Y0 + (gy - LUG_Y0) % 9
        for gx in range(LUG_X0, R - 1):
            x, y = gx - ox, gy - oy
            op[x, y] = op[gx - ox, sy - oy][:3] + (op[x, y][3],)
    body = Image.new("L", (W, H), 0)
    ImageDraw.Draw(body).polygon([(gx - ox, gy - oy) for gx, gy in [(BODY_X0 + 2, 274), (SEAL_X0, 274), (SEAL_X0, 326), (SEAL_X0 - 8, 322), (BODY_X0 + 7, 312), (BODY_X0 + 4, 296)]], fill=255)
    # tight crop to the pouch (alpha > 0)
    bbox = out.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    return out.crop(bbox), body.crop(bbox), (bbox[0] + ox, bbox[1] + oy)


def edge_light_wrap(pouch, base, strength=0.22, depth=3):
    """Edge pixels pick up the local scene colour: normalised blur of the scene OUTSIDE the pouch, fading in over `depth` px."""
    a = pouch.getchannel("A")
    full_a = Image.new("L", base.size, 0)
    full_a.paste(a, (PX, PY))
    outside = ImageChops.invert(full_a.filter(ImageFilter.MaxFilter(5)))
    sn, sd = nblur(base.convert("RGB"), outside, 9)
    inner = a.filter(ImageFilter.MinFilter(2 * depth + 1))
    wgt = ImageChops.subtract(a, inner).filter(ImageFilter.GaussianBlur(1.0))      # 1 at the rim, 0 deeper than `depth`
    wp, pp = wgt.load(), pouch.load()
    for y in range(pouch.height):
        for x in range(pouch.width):
            w = wp[x, y] / 255 * strength
            if w < 0.01:
                continue
            gx, gy = x + PX, y + PY
            den = sd[gx, gy]
            if den < 5:
                continue
            r, g, b, al = pp[x, y]
            wc = [sn[gx, gy][k] * 255 / den for k in range(3)]
            pp[x, y] = (int(r * (1 - w) + wc[0] * w), int(g * (1 - w) + wc[1] * w), int(b * (1 - w) + wc[2] * w), al)
    return pouch


def refine_glass_edge(gen, fitted, y1=1640, search=12):
    """Per-row glass edge: strongest luminance step within +-12 px of the fitted line, median-smoothed over rows."""
    g = gen.convert("L").load()
    raw = []
    for i, y in enumerate(range(rf.RIM, y1)):
        f = fitted[i]
        best = max(range(f - search, f + search + 1), key=lambda x: abs(g[x + 3, y] - g[x - 3, y]))
        raw.append(best)
    sm = [sorted(raw[max(0, i - 10):i + 11])[len(raw[max(0, i - 10):i + 11]) // 2] for i in range(len(raw))]
    return sm


def lab(c):
    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    r, g, b = [(v / 255) ** 2.2 for v in c]
    x, y, z = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, 0.2126 * r + 0.7152 * g + 0.0722 * b, (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def build(dx, label_out, glass_fn=None, gain_excl=None):
    gen = Image.open(RUN / "candidate_A.png").convert("RGB")
    ref = Image.open(RUN / "edit_canvas.png")
    glass0, fitted = rf.glass_edge_mask(gen, ref)
    edge = refine_glass_edge(gen, fitted)
    glass = Image.new("L", (GW, GH), 0)
    gd = ImageDraw.Draw(glass)
    for i, y in enumerate(range(rf.RIM, 1640)):
        gd.line((edge[i] + 1, y, GW, y), fill=255)
    if glass_fn is not None:
        plate, glass_b = glass_fn(gen, edge, dx)
    else:
        # --- plate B: glass block moved right by dx; exposed strip = mirror clone; reflection rows blend over 30 px (no seam)
        X0, Y0 = 1215, rf.RIM
        mir = gen.copy()
        wide = gen.crop((X0 - (dx + 30), Y0, X0, GH)).transpose(Image.FLIP_LEFT_RIGHT)
        mir.paste(wide, (X0, Y0))
        sh = mir.copy()
        sh.paste(gen.crop((X0, Y0, GW - dx, GH)), (X0 + dx, Y0))
        ramp = Image.new("L", (GW, GH), 0)
        rd = ImageDraw.Draw(ramp)
        for i in range(30):
            rd.line((X0 + dx + i, Y0, X0 + dx + i, GH), fill=int(255 * (i + 1) / 30))
        rd.rectangle((X0 + dx + 30, Y0, GW, GH), fill=255)
        plate = Image.composite(sh, mir, ramp)
        glass_b = Image.new("L", (GW, GH), 0)
        glass_b.paste(glass.crop((0, 0, GW - dx, GH)), (dx, 0))
    base = plate.resize((FW, FH), Image.LANCZOS).convert("RGB")
    gl_f = glass_b.resize((FW, FH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.8))
    # --- the pouch: v2 layer, relit with the same smooth gain, seal repair, light wrap
    layer, body, org = source_layer()
    layer_w, layer_h = layer.size                                                  # source pixels
    k = 0.868                                                                      # same scale as before (810 / 933), downscale only
    pouch = layer.resize((round(layer_w * k), round(layer_h * k)), Image.LANCZOS)  # RGBA resize is alpha-premultiplied inside Pillow
    bodym = body.resize(pouch.size, Image.LANCZOS)
    # final position: the old pouch box (PX, PY) corresponds to source (219.., 122..): keep the same registration
    off_x = PX + round((org[0] - 215) * k)
    off_y = PY + round((org[1] - 122) * k)
    canvas = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    canvas.paste(pouch, (off_x, off_y))
    pouch_full = canvas.crop((PX, PY, PX + PW, PY + PH))
    body_full = Image.new("L", (FW, FH), 0)
    body_full.paste(bodym, (off_x, off_y))
    body_full = body_full.crop((PX, PY, PX + PW, PY + PH))
    # smooth lighting gain from the model's own pouch (outside glass), as before
    gwin = Image.open(RUN / "candidate_A.png").convert("RGB").resize((FW, FH), Image.LANCZOS).crop((PX, PY, PX + PW, PY + PH))
    a0 = pouch_full.getchannel("A")
    gl_gain = gain_excl.resize((FW, FH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.8)) if gain_excl is not None else gl_f   # pixels of the model's pouch that were glass must not drive the lighting gain
    keep = ImageChops.multiply(a0, ImageChops.invert(gl_gain.crop((PX, PY, PX + PW, PY + PH))))
    rgb = pouch_full.convert("RGB")
    gn, gdn = nblur(gwin, keep, 24)
    rn, rdn = nblur(rgb, keep, 24)
    pr, gains = rgb.load(), []
    rp = pouch_full.load()
    for y in range(PH):
        for x in range(PW):
            if rp[x, y][3] == 0:
                continue
            if gdn[x, y] < 8 or rdn[x, y] < 8:
                continue
            gg = [min(1.05, max(0.75, (gn[x, y][c] / gdn[x, y]) / max(1e-3, rn[x, y][c] / rdn[x, y]))) for c in range(3)]
            gains.append(sum(gg) / 3)
            r, g, b, a = rp[x, y]
            rp[x, y] = (min(255, int(r * gg[0])), min(255, int(g * gg[1])), min(255, int(b * gg[2])), a)
    src_relit = pouch_full.copy()                                                  # reference for the fidelity measurement (relit, before body patch)
    # body part of the handle repair: the model's plain cloth colour inside the real silhouette
    seal_rgb = base.crop((PX, PY, PX + PW, PY + PH))
    rgb2 = Image.composite(seal_rgb, pouch_full.convert("RGB"), body_full.filter(ImageFilter.GaussianBlur(1.0)))
    pouch_full = rgb2.convert("RGBA")
    pouch_full.putalpha(a0)
    pouch_full.putalpha(ImageChops.multiply(a0, ImageChops.invert(gl_f.crop((PX, PY, PX + PW, PY + PH)))))
    pouch_full = edge_light_wrap(pouch_full, base)
    comp = base.convert("RGBA")
    comp.alpha_composite(pouch_full, (PX, PY))
    comp = rf.finish(comp.convert("RGB"))
    return comp, {"gains": gains, "pouch": pouch_full, "relit": src_relit, "glass": gl_f.crop((PX, PY, PX + PW, PY + PH)), "body": body_full, "edge": edge}


def headline(im):
    d = ImageDraw.Draw(im, "RGBA")
    fh = ImageFont.truetype(str(RUN / "font/extras/ttf/Inter-Medium.ttf"), 50)
    d.rectangle((94, 78, 94 + 84, 81), fill=(255, 140, 50, 255))

    def tr(xy, t, fill):
        x, y = xy
        for ch in t:
            d.text((x, y), ch, font=fh, fill=fill)
            x += d.textlength(ch, font=fh) + 7
        return x
    tr((92, 104), "SVAKA SERIJA", (242, 237, 232, 255))
    x = tr((92, 172), "POČINJE ODLUKOM", (242, 237, 232, 255))
    d.text((x, 172), ".", font=fh, fill=(255, 140, 50, 255))
    return im


def fidelity(comp, info):
    """Colour difference and geometry of the visible pouch against the real source (relit layer = same pixels before the gain? no: raw source)."""
    layer, _, _ = source_layer()
    k = 0.868
    srcp = layer.resize((round(layer.width * k), round(layer.height * k)), Image.LANCZOS)
    pf = info["pouch"]
    a = pf.getchannel("A")
    ap = a.load()
    # visible, un-patched pouch pixels: alpha > 0.98, not glass, not body patch
    cp = comp.crop((PX, PY, PX + PW, PY + PH)).load()
    raw = info["relit"].convert("RGB").load()                                   # source colours at final scale (before relight): reconstruct from layer
    # raw source colours at final scale
    canvas = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    canvas.paste(srcp, (PX + round((layer_org[0] - 215) * k), PY + round((layer_org[1] - 122) * k)))
    sc = canvas.crop((PX, PY, PX + PW, PY + PH)).load()
    des, n, lum_s, lum_f = [], 0, [], []
    for y in range(0, PH, 2):
        for x in range(0, PW, 2):
            if ap[x, y] < 250 or info["glass"].getpixel((x, y)) > 10 or info["body"].getpixel((x, y)) > 10:
                continue
            r0, g0, b0, a0 = sc[x, y]
            if a0 < 250:
                continue
            l1, a1, b1 = lab((r0, g0, b0))
            l2, a2, b2 = lab(cp[x, y])
            des.append(math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2))
            lum_s.append(l1)
            lum_f.append(l2)
            n += 1
    des.sort()
    # detail correlation on the label area (high-pass luminance, source at final scale vs final image)
    box = (404 - PX, 500 - PY, 764 - PX, 730 - PY)
    sc_img = canvas.crop((PX, PY, PX + PW, PY + PH)).crop(box).convert("L")
    fi_img = comp.crop((PX, PY, PX + PW, PY + PH)).crop(box).convert("L")
    hs = ImageChops.subtract(sc_img, sc_img.filter(ImageFilter.GaussianBlur(3)), 1, 128).getdata()
    hf = ImageChops.subtract(fi_img, fi_img.filter(ImageFilter.GaussianBlur(3)), 1, 128).getdata()
    ms, mf = sum(hs) / len(hs), sum(hf) / len(hf)
    cov = sum((a - ms) * (b - mf) for a, b in zip(hs, hf))
    ncc = cov / math.sqrt(sum((a - ms) ** 2 for a in hs) * sum((b - mf) ** 2 for b in hf))
    return {"label_detail_correlation": round(ncc, 4), "scale_x": k, "scale_y": k, "stretch": "none (one uniform scale 0.868, downscale only)",
            "cloned_seal_px_final": round((R - 1 - SEAL_X0) * (HANDLE_Y1 - HANDLE_Y0) * k * k),"pixels_compared": n, "deltaE76_median": round(des[len(des) // 2], 2), "deltaE76_p95": round(des[int(len(des) * .95)], 2),
            "deltaE76_mean": round(sum(des) / len(des), 2), "mean_L_source": round(sum(lum_s) / n, 1), "mean_L_final": round(sum(lum_f) / n, 1)}


layer_org = (0, 0)


def main():
    global layer_org
    _, _, layer_org = source_layer()
    dx = 50
    comp, info = build(dx, "")
    out = headline(comp.copy())
    out.save(RUN / "hero_v2_corrected_1080x1350.png")
    comp.save(RUN / "hero_v2_nolettering_1080x1350.png")
    gains = info["gains"]
    fid = fidelity(comp, info)
    p = info["pouch"].getchannel("A")
    bbox = p.point(lambda v: 255 if v > 128 else 0).getbbox()
    fid.update({"smooth_gain_mean": round(sum(gains) / len(gains), 3), "smooth_gain_min": round(min(gains), 3), "smooth_gain_max": round(max(gains), 3),
                "pouch_bbox_final_px": [bbox[2] - bbox[0], bbox[3] - bbox[1]], "glass_shift_gen_px": dx,
                "body_patch_px_final": sum(1 for v in info["body"].getdata() if v > 128),
                "seal_rows_cloned_from_source_gen": f"x {SEAL_X0}-{R - 2}, rows {HANDLE_Y0}-{HANDLE_Y1 - 1} from rows {HANDLE_Y0 - CLONE_DY}-{HANDLE_Y1 - 1 - CLONE_DY} (source px)"})
    (RUN / "hero_v2_fidelity.json").write_text(json.dumps(fid, indent=1), encoding="utf-8")
    print(json.dumps(fid, indent=1))


if __name__ == "__main__":
    main()
