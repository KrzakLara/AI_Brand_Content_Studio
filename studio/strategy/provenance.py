"""Visual provenance contact sheet: every label crop next to its source image, bounding box and origin.

Reads the operator-labelled crops file and the stored original packshot (sha256-checked) and draws ONE PNG for a human to inspect. Nothing is
re-rendered or "enhanced": crops are plain rectangles of the source, scaled only for display.
Usage: python -m studio.strategy.provenance --image <packshot.jpg> --crops research/imports/label_crops_gymbeam_hr.yaml --out sheet.png
"""
import argparse
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

from studio.fingerprint import sha256_file

COLOURS = {"physical_packaging": (30, 140, 60), "webshop_graphic": (230, 120, 20), "uncertain": (150, 30, 150)}
LABEL = {"physical_packaging": "PRINTED ON THE POUCH", "webshop_graphic": "WEBSHOP GRAPHIC (not packaging print)", "uncertain": "UNCERTAIN"}


def _font(size):
    for f in ("C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def contact_sheet(image_path: Path, crops_yaml: Path, out: Path) -> Path:
    doc = yaml.safe_load(Path(crops_yaml).read_text(encoding="utf-8"))
    if sha256_file(Path(image_path)) != doc["provenance"]["source_sha256"]:
        raise ValueError("image does not match the sha256 recorded in the crops file")
    src = Image.open(image_path).convert("RGB")
    scale = 720 / src.width
    left = src.resize((720, int(src.height * scale)))
    d = ImageDraw.Draw(left)
    f, fs = _font(15), _font(12)
    for c in doc["crops"]:
        x0, y0, x1, y1 = [int(v * scale) for v in c["box"]]
        col = COLOURS[c["origin"]]
        d.rectangle([x0, y0, x1, y1], outline=col, width=3 if c["usable"] else 1)
        d.text((x0 + 3, y0 + 2), c["id"] + ("" if c["usable"] else " (not used)"), fill=col, font=fs)
    used = [c for c in doc["crops"] if c["usable"]]
    rows = []
    for c in used:
        x0, y0, x1, y1 = c["box"]
        tile = src.crop((x0, y0, x1, y1))
        tile.thumbnail((380, 170))
        rows.append((c, tile))
    row_h = 200
    ref = [c for c in doc["crops"] if c["id"].startswith("printed_badge")]
    W, H = 720 + 20 + 380 + 20 + 360, max(left.height, row_h * len(rows)) + 380
    sheet = Image.new("RGB", (W, H), "white")
    sheet.paste(left, (0, 0))
    g = ImageDraw.Draw(sheet)
    for i, (c, tile) in enumerate(rows):
        y = i * row_h + 8
        col = COLOURS[c["origin"]]
        g.rectangle([740, y, 740 + tile.width + 6, y + tile.height + 6], outline=col, width=4)
        sheet.paste(tile, (743, y + 3))
        t = [f"{c['id']}   box {c['box']}", LABEL[c["origin"]], "shows: " + ", ".join(c["printed_text"])]
        words, line = c["origin_basis"].split(), ""
        for w in words:
            if len(line) + len(w) > 52:
                t.append(line)
                line = ""
            line += w + " "
        t.append(line)
        for j, s in enumerate(t[:9]):
            g.text((1140, y + 4 + j * 16), s, fill=col if j == 1 else (30, 30, 30), font=f if j < 2 else fs)
    y = max(left.height, row_h * len(rows)) + 12
    g.text((10, y), "Reference, NOT used: the same four badges printed small on the pouch face (arc text only partly legible when enlarged; no clearer version is made)", fill=(30, 30, 30), font=f)
    for k, c in enumerate(ref):
        x0, y0, x1, y1 = c["box"]
        t = src.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 4, (y1 - y0) * 4), Image.LANCZOS)
        sheet.paste(t, (10 + k * (t.width + 20), y + 28))
        g.text((10 + k * (t.width + 20), y + 28 + t.height + 4), f"{c['id']} (~{x1 - x0}px wide at 1:1, shown 4x)", fill=COLOURS["physical_packaging"], font=fs)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return Path(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--crops", default="research/imports/label_crops_gymbeam_hr.yaml")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print(contact_sheet(Path(a.image), Path(a.crops), Path(a.out)))
