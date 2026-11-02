"""Slide 6 cleanup (Phase 7F): local retouch of CONFIRMED defects only, using existing pixels. No network, no spend. The frozen original is never modified.

Defects (found at 100 % zoom on slide6_odaberi_svoj_okus_FINAL.png):
  1. stray 5x2 px dark dash at x 659-663, y 299-300 above "RITUAL." -> filled from the surrounding background
  2. rectangular retouch patch behind the subtitle (box x 59-742, y 301-354: row 353/354 and column 58/59 show a 2-6 level brightness step) ->
     the background pixels of that box + a 3 px margin are re-solved (harmonic fill from the ring outside the box); subtitle letter pixels (y 306-346) are kept exactly
  3. grey vertical streak on the sliced strawberry, x 349-352, y 810-850 -> Telea inpaint of the grey pixels from the red flesh around them
Not touched: product labels, flavours, layout, colours, text, the jar (its lighter left rim is the real packshot's glass edge), the lilac halo around the strawberry (cut-out edge, flagged).

  python slide6_cleanup.py --out <dir>     writes slide6_odaberi_svoj_okus_FINAL_v2_1080x1350.png + QA json + before/after crops; refuses to overwrite
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "runs/colla-pink/carousel_final/slide6_odaberi_svoj_okus_FINAL.png"
NAME = "slide6_odaberi_svoj_okus_FINAL_v2_1080x1350.png"
PATCH = (57, 296, 746, 358)      # x0, y0, x1, y1 (exclusive): fill box, 3 px larger than the measured patch
TEXT_Y = (306, 347)              # rows where subtitle letters live; dark pixels here are kept


def harmonic_fill(img: np.ndarray, fill: np.ndarray, iters: int = 4000) -> np.ndarray:
    """Per channel: solve Laplace's equation inside `fill` with the surrounding pixels as boundary (Jacobi iterations)."""
    out = img.astype(np.float32).copy()
    ys, xs = np.where(fill)
    y0, y1, x0, x1 = ys.min() - 1, ys.max() + 2, xs.min() - 1, xs.max() + 2
    m = fill[y0:y1, x0:x1]
    for c in range(3):
        a = out[y0:y1, x0:x1, c]
        # start from the linear blend of the rows above/below so convergence is fast
        top, bot = a[0:1, :], a[-1:, :]
        t = np.linspace(0, 1, a.shape[0])[:, None]
        a[m] = (top * (1 - t) + bot * t)[m]
        for _ in range(iters):
            n = a.copy()
            n[1:-1, 1:-1] = 0.25 * (a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:])
            a[m] = n[m]
        out[y0:y1, x0:x1, c] = a
    return out


def retouch(im: np.ndarray) -> tuple[np.ndarray, dict]:
    out = im.copy(); info = {}
    # 2 + 1: subtitle patch and stray dash
    x0, y0, x1, y1 = PATCH
    box = np.zeros(im.shape[:2], bool); box[y0:y1, x0:x1] = True
    lum = im.astype(int).sum(2)
    letters = np.zeros_like(box); letters[TEXT_Y[0]:TEXT_Y[1], :] = lum[TEXT_Y[0]:TEXT_Y[1], :] < 600   # burgundy letter pixels incl. their anti-aliasing
    letters = cv2.dilate(letters.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    fill = box & ~letters
    fill[y0:y0 + 1, :] = False; fill[y1 - 1:y1, :] = False; fill[:, x0:x0 + 1] = False; fill[:, x1 - 1:x1] = False      # outermost ring = fixed boundary
    out = np.clip(harmonic_fill(out, fill), 0, 255).astype(np.uint8)
    info["patch_fill_px"] = int(fill.sum()); info["letter_px_kept"] = int((box & letters).sum())
    # 3: grey streak on the strawberry
    sx0, sy0, sx1, sy1 = 345, 804, 358, 854
    sub = out[sy0:sy1, sx0:sx1].astype(int)
    grey = (sub[..., 0] - sub[..., 2] < 85) & (sub[..., 0] < 215)
    grey = cv2.dilate(grey.astype(np.uint8), np.ones((3, 3), np.uint8))
    m = np.zeros(out.shape[:2], np.uint8); m[sy0:sy1, sx0:sx1] = grey * 255
    out = cv2.inpaint(out, m, 4, cv2.INPAINT_TELEA)
    info["streak_px"] = int((m > 0).sum())
    return out, info


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True); dst = a.out / NAME
    if dst.exists():
        raise FileExistsError(dst)
    im = np.asarray(Image.open(SRC).convert("RGB"))
    out, info = retouch(im)
    Image.fromarray(out).save(dst)
    d = np.abs(out.astype(int) - im.astype(int)).max(2)
    ys, xs = np.where(d > 0)
    info.update({"changed_px": int((d > 0).sum()), "changed_bbox_x": [int(xs.min()), int(xs.max())], "changed_bbox_y": [int(ys.min()), int(ys.max())],
                 "max_abs_change": int(d.max()), "changed_outside_known_boxes": int(((d > 0) & ~(((np.arange(im.shape[1])[None, :] >= 56) & (np.arange(im.shape[1])[None, :] < 747) & (np.arange(im.shape[0])[:, None] >= 295) & (np.arange(im.shape[0])[:, None] < 359)) |
                                                                                          ((np.arange(im.shape[1])[None, :] >= 345) & (np.arange(im.shape[1])[None, :] < 358) & (np.arange(im.shape[0])[:, None] >= 804) & (np.arange(im.shape[0])[:, None] < 854)))).sum())})
    (a.out / "slide6_cleanup_QA.json").write_text(json.dumps(info, indent=1), encoding="utf-8"); print(json.dumps(info, indent=1))
