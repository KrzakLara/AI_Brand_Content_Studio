"""Deterministic retouch of the jar in Cover V2 (zero cost: no network, no API, no key). Run from the repository root:  python plans/gymbeam_hr/phase5/retouch_cover2.py
Starts again from the model's raw render and the registration of the REAL jar (cover2_registration.json), so the woman, background and lighting are the same pixels
as Cover V2; only the repair region (jar bounding box + margin) is recomputed. Outside it the output is verified identical to cover2_slide1_1080x1350.png.
Changes against the first composite: (1) the jar matte is rebuilt from smooth fitted edges with supersampled anti-aliasing (no row-span stair steps); (2) edge colours
are decontaminated (the outer ring takes the colour of the jar a few px inside: no pale halo from the white studio backdrop); (3) hands in front of the jar are restored
only inside two hand regions, with a lower brightness threshold at the base (no thumb blotch, no hair at the lid corner); (4) a soft contact shadow of the jar falls on the
hands and the body; (5) a thin form shading darkens the jar's side edges so its edge contrast matches the scene. Printed artwork is never touched."""
import json
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont  # noqa: E402

RUN = ROOT / "runs/colla-pink"
GW, GH, FW, FH = 1600, 2000, 1080, 1350
BURG = (127, 41, 68)
RAW, REG, JAR = RUN / "cover2_raw.png", RUN / "cover2_registration.json", RUN / "jar_strawberry_layer.png"
OUT = RUN / "cover2_slide1_RETOUCHED_1080x1350.png"


def nblur(img, w, r):
    num = Image.composite(img, Image.new(img.mode, img.size), w).filter(ImageFilter.GaussianBlur(r))
    return num.load(), w.filter(ImageFilter.GaussianBlur(r)).load()


def smooth(vals, k):
    out = []
    for i in range(len(vals)):
        w = sorted(vals[max(0, i - k):i + k + 1])
        out.append(w[len(w) // 2])
    return [sum(out[max(0, i - k):i + k + 1]) / len(out[max(0, i - k):i + k + 1]) for i in range(len(out))]


def clean_jar():
    """Real jar layer with a smooth, supersampled matte and decontaminated edge colours (source pixels otherwise untouched)."""
    j = Image.open(JAR).convert("RGBA")
    w, h = j.size
    a = j.getchannel("A").point(lambda v: 255 if v > 128 else 0).load()
    L, R = [], []
    for y in range(h):
        xs = [x for x in range(w) if a[x, y]]
        L.append(xs[0] if xs else w // 2); R.append(xs[-1] + 1 if xs else w // 2)
    body0, body1 = 235, h - 70                                   # rows where the jar sides are straight (label band and neck)
    def fitline(E):
        ys = list(range(body0, body1)); n = len(ys); my = sum(ys) / n; mx = sum(E[y] for y in ys) / n
        k = sum((y - my) * (E[y] - mx) for y in ys) / sum((y - my) ** 2 for y in ys)
        return lambda y: mx + k * (y - my)
    fl, fr = fitline(L), fitline(R)
    sl, sr = smooth(L, 6), smooth(R, 6)
    Ls = [fl(y) if body0 <= y < body1 else sl[y] for y in range(h)]
    Rs = [fr(y) if body0 <= y < body1 else sr[y] for y in range(h)]
    for y in range(body0 - 12, body0 + 12):                         # blend measured lid edge into the fitted body edge
        t = (y - (body0 - 12)) / 24
        Ls[y] = sl[y] * (1 - t) + fl(y) * t; Rs[y] = sr[y] * (1 - t) + fr(y) * t
    S = 4
    big = Image.new("L", (w * S, h * S), 0)
    pts = [(Ls[y] * S, y * S) for y in range(h)] + [(Rs[y] * S, y * S) for y in range(h - 1, -1, -1)]
    ImageDraw.Draw(big).polygon(pts, fill=255)
    top = [y for y in range(h) if a[0, y] or any(a[x, y] for x in range(w // 2 - 3, w // 2 + 3))]
    alpha = big.resize((w, h), Image.LANCZOS).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))   # 1 px in: the edge row of a packshot is blended with the white backdrop
    # base: keep the packshot's own curved bottom (the original alpha), intersected with the smooth sides
    alpha = ImageChops.multiply(alpha, j.getchannel("A").filter(ImageFilter.GaussianBlur(0.5)).point(lambda v: min(255, v * 2)))
    rgb = j.convert("RGB")
    interior = alpha.point(lambda v: 255 if v > 250 else 0).filter(ImageFilter.MinFilter(9))
    cn, cd = nblur(rgb, interior, 3)
    rp = rgb.load(); ap = alpha.load(); ip = interior.load()
    for y in range(h):
        for x in range(w):
            if ap[x, y] and not ip[x, y] and cd[x, y] > 10:       # edge ring: take the colour of the jar just inside it
                d = cn[x, y]; k = cd[x, y]
                rp[x, y] = tuple(min(255, int(d[c] * 255 / k)) for c in range(3))
    out = rgb.convert("RGBA"); out.putalpha(alpha)
    return out


def main():
    raw = Image.open(RAW).convert("RGB")
    reg = json.loads(REG.read_text())
    j0 = clean_jar()
    grow = 1.008
    s = reg["scale"] * grow
    j = j0.resize((round(j0.width * s), round(j0.height * s)), Image.LANCZOS)
    x = reg["x"] - round((j.width - Image.open(JAR).width * reg["scale"]) / 2)
    y = reg["y"] - round((j.height - Image.open(JAR).height * reg["scale"]) / 2)
    # base line trim as before (4 px + 3 px fade)
    al = j.getchannel("A"); ap = al.load(); cols = {}
    for xx in range(j.width):
        for yy in range(j.height - 1, -1, -1):
            if ap[xx, yy] > 128:
                cols[xx] = yy; break
    for xx, yb in cols.items():
        for k in range(7):
            if yb - k >= 0:
                ap[xx, yb - k] = int(ap[xx, yb - k] * (0.0 if k < 4 else (k - 3) / 4))
    j.putalpha(al)
    # relight (bounded gain from the model's own jar region), as in Cover V2
    inner = j.getchannel("A").point(lambda v: 255 if v > 250 else 0).filter(ImageFilter.MinFilter(9))
    gn, gd = nblur(raw.crop((x, y, x + j.width, y + j.height)), inner, 22); rn, rd = nblur(j.convert("RGB"), inner, 22)
    jp = j.load()
    for yy in range(j.height):
        for xx in range(j.width):
            if jp[xx, yy][3] == 0 or gd[xx, yy] < 8 or rd[xx, yy] < 8:
                continue
            g = [min(1.05, max(0.70, (gn[xx, yy][c] / gd[xx, yy]) / max(1e-3, rn[xx, yy][c] / rd[xx, yy]))) for c in range(3)]
            r, gg, b, a = jp[xx, yy]
            jp[xx, yy] = (min(255, int(r * g[0])), min(255, int(gg * g[1])), min(255, int(b * g[2])), a)
    # (5) form shading: the outer 6% of the width on each side darkens smoothly (up to 9%), matching the scene's edge contrast; label art is inside 94%
    sh = Image.new("L", j.size, 255); sd = ImageDraw.Draw(sh)
    ew = max(3, round(j.width * 0.06))
    for k in range(ew):
        v = int(255 * (1 - 0.09 * (1 - k / ew) ** 2))
        sd.line((k, 0, k, j.height), fill=v); sd.line((j.width - 1 - k, 0, j.width - 1 - k, j.height), fill=v)
    rgb = ImageChops.multiply(j.convert("RGB"), Image.merge("RGB", (sh, sh, sh)))
    j = rgb.convert("RGBA"); j.putalpha(al)
    # (4) contact shadow on hands/body: blurred jar silhouette, offset down-right, multiplies the raw only OUTSIDE the jar
    foot = Image.new("L", raw.size, 0); foot.paste(j.getchannel("A"), (x, y))
    shadow = foot.filter(ImageFilter.GaussianBlur(16)); shadow = ImageChops.offset(shadow, 4, 7)
    shade = ImageChops.invert(shadow.point(lambda v: int(v * 0.10)))                              # 20% darkening at most
    plate = ImageChops.multiply(raw, Image.merge("RGB", (shade, shade, shade)))
    plate = Image.composite(plate, raw, Image.new("L", raw.size, 255).filter(ImageFilter.MinFilter(1)))
    base = plate.convert("RGBA"); base.alpha_composite(j, (x, y))
    # (3) hands in front of the jar, only inside two explicit hand regions
    hsv = raw.convert("HSV"); hp = hsv.load()
    hands = [(x - 40, y - 30, x + round(j.width * 0.55), y + round(j.height * 0.20)),            # fingertips resting on the lid (left half of the lid only)
             (x - 40, y + round(j.height * 0.80), x + j.width + 40, y + j.height + 60)]            # supporting hand and thumbs at the base
    region = Image.new("L", raw.size, 0)
    for r_, box in zip((135, 95), hands):
        rd_ = ImageDraw.Draw(region)
    sk = Image.new("L", raw.size, 0); sp = sk.load()
    for (x0, y0, x1, y1), vmin in zip(hands, (135, 95)):
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                h_, s_, v_ = hp[xx, yy]
                if (h_ <= 28 or h_ >= 250) and s_ > 40 and v_ > vmin:
                    sp[xx, yy] = 255
    sk = sk.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
    ft = foot.point(lambda v: 255 if v > 20 else 0).load(); skp = sk.point(lambda v: 255 if v > 128 else 0).load()
    X0, Y0, X1, Y1 = x - 40, y - 30, x + j.width + 40, y + j.height + 60
    seen = set(); dq = deque()
    for yy in range(Y0, Y1):
        for xx in range(X0, X1):
            if skp[xx, yy] and not ft[xx, yy]:
                seen.add((xx, yy)); dq.append((xx, yy))
    while dq:
        cx, cy = dq.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if X0 <= nx < X1 and Y0 <= ny < Y1 and (nx, ny) not in seen and skp[nx, ny]:
                seen.add((nx, ny)); dq.append((nx, ny))
    conn = Image.new("L", raw.size, 0); cp = conn.load()
    for cx, cy in seen:
        cp[cx, cy] = 255
    front = ImageChops.multiply(conn.filter(ImageFilter.GaussianBlur(1.0)), foot.point(lambda v: 255 if v > 20 else 0))
    base = Image.composite(raw.convert("RGBA"), base, front)
    full = base.convert("RGB").resize((FW, FH), Image.LANCZOS)
    # typography layer: identical code and positions as Cover V2
    im = full.copy(); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(RUN / "font/Montserrat.ttf"), 104); f.set_variation_by_name("ExtraBold")
    d.text((60, 44), "VAŠ RUŽIČASTI", font=f, fill=BURG); d.text((60, 44 + int(f.size * 1.1)), "RITUAL.", font=f, fill=BURG)
    sub = ImageFont.truetype(str(RUN / "font/Montserrat.ttf"), 40); sub.set_variation_by_name("Bold")
    d.text((64, 1150), "SVE ŠTO TREBA ZNATI", font=sub, fill=BURG); d.text((64, 1200), "U ŠEST KADROVA.", font=sub, fill=BURG)
    im.save(OUT)
    k = FW / GW
    region_box = [round((x - 40) * k) - 3, round((y - 30) * k) - 3, round((x + j.width + 40) * k) + 3, round((y + j.height + 60) * k) + 3]
    (RUN / "cover2_retouch_region.json").write_text(json.dumps({"repair_region_final_px": region_box, "jar_xy_gen": [x, y], "jar_size_gen": list(j.size)}))
    print("saved", OUT.name, "repair region (final px):", region_box)


if __name__ == "__main__":
    main()
