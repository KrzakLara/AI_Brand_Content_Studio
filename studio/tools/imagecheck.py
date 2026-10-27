"""Packshot / image inspection. Header parsing is pure Python; pixel work needs Pillow (optional extra).

``inspect_image`` answers: what format, what resolution, can it have transparency, does it actually
have any, and is the background uniform. ``cutout_background`` produces an RGBA PNG when it does not.
"""
import io
import struct

PNG_SIG = b"\x89PNG\r\n\x1a\n"


class PillowMissing(RuntimeError):
    """Pixel analysis needs the optional 'images' extra (pip install -e .[images])."""


def _pil():
    try:
        from PIL import Image
    except ImportError as e:  # explicit, never silently skipped
        raise PillowMissing("Pillow is not installed; install the 'images' extra") from e
    return Image


def _pil_version() -> str:
    import PIL
    return PIL.__version__


def header_info(data: bytes) -> dict:
    """Format, size and whether the *format* can carry alpha. No dependencies."""
    if data[:8] == PNG_SIG:
        w, h, _bd, ct = struct.unpack(">IIBB", data[16:26])
        return {"format": "png", "width": w, "height": h, "alpha_capable": ct in (4, 6) or b"tRNS" in data[:65536]}
    if data[:3] == b"\xff\xd8\xff":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            m = data[i + 1]
            if m in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return {"format": "jpeg", "width": w, "height": h, "alpha_capable": False}
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return {"format": "webp", "width": None, "height": None, "alpha_capable": None}
    raise ValueError("unrecognised image format")


def inspect_image(data: bytes, *, min_side: int = 1000) -> dict:
    """Resolution + transparency verdict. ``transparent_background`` needs Pillow for the real pixel test."""
    info = header_info(data)
    info["meets_min_resolution"] = bool(info["width"]) and min(info["width"], info["height"]) >= min_side
    info["min_side_required"] = min_side
    if not info["alpha_capable"]:
        info.update(has_transparency=False, transparent_fraction=0.0, transparent_background=False)
    else:
        im = _pil().open(io.BytesIO(data)).convert("RGBA")
        a = im.getchannel("A")
        hist = a.histogram()
        frac = sum(hist[:250]) / (im.width * im.height)
        corners = [a.getpixel(p) for p in ((0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1))]
        info.update(has_transparency=frac > 0.001, transparent_fraction=round(frac, 4),
                    transparent_background=all(c < 10 for c in corners))
    try:
        info["background"] = background_colour(data)
    except PillowMissing:
        info["background"] = None
    return info


def background_colour(data: bytes, tol: int = 12) -> dict:
    """Sample the 4 corners (RGB). ``uniform`` is True when they agree within ``tol``."""
    im = _pil().open(io.BytesIO(data)).convert("RGB")
    pts = [im.getpixel(p) for p in ((2, 2), (im.width - 3, 2), (2, im.height - 3), (im.width - 3, im.height - 3))]
    ref = pts[0]
    uniform = all(max(abs(a - b) for a, b in zip(ref, p)) <= tol for p in pts)
    return {"hex": "#%02x%02x%02x" % ref, "uniform": uniform}


def cutout_background(data: bytes, *, tol: int = 14) -> tuple[bytes, dict]:
    """Make the uniform edge-connected background transparent. Returns (png bytes, report).

    Flood-fills from the border over pixels within ``tol`` of the corner colour, so interior
    white (e.g. a label) is kept. Anything touching the pouch that is not background colour
    (claim badges, shadows) stays: this is a mechanical cut-out, not retouching.
    """
    Image = _pil()
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    bg = background_colour(data)
    if not bg["uniform"]:
        raise ValueError("background is not uniform; automatic cut-out refused")
    ref = im.getpixel((2, 2))[:3]
    w, h = im.size
    px = im.load()
    seen = bytearray(w * h)
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    cleared = 0
    while stack:
        x, y = stack.pop()
        i = y * w + x
        if seen[i]:
            continue
        seen[i] = 1
        r, g, b, _a = px[x, y]
        if max(abs(r - ref[0]), abs(g - ref[1]), abs(b - ref[2])) > tol:
            continue
        px[x, y] = (r, g, b, 0)
        cleared += 1
        if x > 0:
            stack.append((x - 1, y))
        if x < w - 1:
            stack.append((x + 1, y))
        if y > 0:
            stack.append((x, y - 1))
        if y < h - 1:
            stack.append((x, y + 1))
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue(), {"method": "edge flood-fill background removal", "tolerance": tol,
                            "background_hex": bg["hex"], "transparent_fraction": round(cleared / (w * h), 4),
                            "pillow": _pil_version()}


def dominant_colors(data: bytes, k: int = 6) -> list[dict]:
    """Top-k colours by pixel share, via median-cut quantisation of a 96x96 thumbnail."""
    Image = _pil()
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((96, 96))
    q = im.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: 3 * k]
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    return [{"hex": "#%02x%02x%02x" % tuple(pal[3 * i:3 * i + 3]), "share": round(c / total, 3)} for c, i in counts]
