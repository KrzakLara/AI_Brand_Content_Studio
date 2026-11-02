"""Slide 5 start frame: calm the wind-blown hair on the right (no network, no spend).

Hand-drawn polygon (full-res coords) covers ONLY the flared hair/wisps to the right of a new, shoulder-hugging hair edge and of the
arm contour. Everything inside it is replaced by the pink backdrop, reconstructed with a quadratic fit to untouched backdrop pixels
(+ matching grain). Face, body, glass, outfit and the rest of the frame stay pixel-identical (feathered ~3 px at the polygon edge only).
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "runs/colla-pink/slide5_video"
SRC = OUT / "start_frame_clean_1080x1350.png"
# new hair edge (top->down), then the arm's outer contour (+2 px outward), then out to the frame edge
POLY = [(770, 215), (782, 300), (796, 400), (803, 470), (809, 530), (818, 568), (834, 590), (846, 622), (856, 660), (868, 700), (880, 740), (890, 780),
        (899, 820), (910, 860), (925, 905), (937, 950), (940, 1010), (972, 1010), (972, 215)]


def fit_bg(a, mask):
    """Quadratic surface per channel from backdrop pixels far right of any hair."""
    ys, xs = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    sel = (((xs > 976) & (xs < 1060) & (ys > 150) & (ys < 1040)) | ((xs > 830) & (xs < 1060) & (ys > 100) & (ys < 285))) & (~mask)
    X = lambda x, y: np.stack([np.ones_like(x), x, y, x * x, y * y, x * y], -1).astype(float) / [1, 1e3, 1e3, 1e6, 1e6, 1e6]
    A = X(xs[sel], ys[sel])
    out = np.zeros(a.shape, float)
    full = X(xs.ravel(), ys.ravel())
    for c in range(3):
        w, *_ = np.linalg.lstsq(A, a[..., c][sel].astype(float), rcond=None)
        out[..., c] = (full @ w).reshape(a.shape[:2])
    return out


if __name__ == "__main__":
    im = Image.open(SRC).convert("RGB"); a = np.asarray(im).astype(float)
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).polygon(POLY, fill=255)
    hard = np.asarray(m) > 127
    bg = fit_bg(a, hard)
    # row-wise seam correction: carry the measured backdrop-vs-fit residual at the right seam leftwards (fading out by x=850)
    k = np.exp(-0.5 * (np.arange(-54, 55) / 18.0) ** 2); k /= k.sum()
    raw = (a[:, 976:1000] - bg[:, 976:1000]).mean(1)
    res_y = np.stack([np.convolve(np.pad(raw[:, c], 54, mode="edge"), k, mode="valid") for c in range(3)], -1)
    ramp = np.clip((np.arange(a.shape[1]) - 850) / 122, 0, 1)
    bg = bg + res_y[:, None, :] * ramp[None, :, None]
    rng = np.random.default_rng(5)
    bg = bg + rng.normal(0, 1.6, bg.shape[:2])[..., None]          # fine film grain like the backdrop
    soft = np.asarray(m.filter(ImageFilter.GaussianBlur(2.2))).astype(float)[..., None] / 255
    res = np.clip(a * (1 - soft) + bg * soft, 0, 255).astype("uint8")
    Image.fromarray(res).save(OUT / "start_frame_hair_calmed_1080x1350.png")
    ch = np.abs(res.astype(int) - a.astype(int)).sum(-1) > 0
    ys, xs = np.nonzero(ch); print("changed bbox", xs.min(), ys.min(), xs.max(), ys.max(), "px", int(ch.sum()))
    c = (640, 330, 1000, 1010)
    s = Image.new("RGB", (720, 680)); s.paste(im.crop(c), (0, 0)); s.paste(Image.fromarray(res).crop(c), (360, 0)); s.save(OUT / "hair_before_after_REVIEW.png")
