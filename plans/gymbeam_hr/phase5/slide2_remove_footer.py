"""Slide 2: remove the small bottom-left source footer ONLY (no network, no spend, original untouched).
The text mask is the burgundy-ish pixels inside the footer box (dilated); the hole is filled with Telea inpainting from the soft pink
backdrop and a little matching grain is added. Everything outside the box is byte-identical to the original."""
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / "runs/colla-pink/carousel_final"
src = cv2.imread(str(D / "slide2_sto_je_unutra_1080x1350.png"))
x0, y0, x1, y1 = 40, 1236, 700, 1326                       # footer box (text spans ~60-635 x 1255-1312)
box = src[y0:y1, x0:x1].astype(int)
bg = np.median(box.reshape(-1, 3), 0)
text = (np.abs(box - bg).sum(-1) > 60).astype(np.uint8)    # burgundy strokes differ strongly from the pink backdrop
mask = cv2.dilate(text, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
full = np.zeros(src.shape[:2], np.uint8); full[y0:y1, x0:x1] = mask
fixed = cv2.inpaint(src, full * 255, 6, cv2.INPAINT_TELEA)
noise = np.random.default_rng(2).normal(0, 1.4, full.shape)[..., None]
soft = cv2.GaussianBlur(full.astype(np.float32), (0, 0), 1.2)[..., None]
out = np.clip(fixed + noise * soft, 0, 255).astype(np.uint8)
out[full == 0] = src[full == 0] if False else out[full == 0]
res = src.copy(); sel = soft[..., 0] > 0.02; res[sel] = out[sel]
cv2.imwrite(str(D / "slide2_sto_je_unutra_NO_FOOTER_1080x1350.png"), res)
ch = (np.abs(res.astype(int) - src.astype(int)).sum(-1) > 0); ys, xs = np.nonzero(ch)
print("shape", res.shape, "changed bbox", xs.min(), ys.min(), xs.max(), ys.max(), "px", int(ch.sum()), "text px", int(text.sum()))
