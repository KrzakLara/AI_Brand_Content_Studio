"""Cover candidate: replace ONLY the visible wrapper in the woman's hand with the sharp wrapper from our S01 still (perspective warp, local, zero cost).
Fingers stay in front: they are kept from the original cover through a hand/skin mask. Face, hair, body, pose and background are untouched."""
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
R = ROOT / "runs/gymbeam-wafer-reel"; OUT = R / "cover_options"
cov = cv2.imread(str(R / "review_package/GYMBEAM_WAFER_REEL_V4_COVER_1080x1920.png"))
s01 = cv2.imread(str(R / "keyframes/S01_keyframe_1080x1920.png"))
SRC = np.float32([[307, 1002], [855, 1005], [860, 1380], [300, 1375]])        # whole pack incl. crimps in S01
DST = np.float32([[158.3, 620], [430, 648.3], [416.7, 835], [153.3, 800]])    # same pack as it sits in the cover
M = cv2.getPerspectiveTransform(SRC, DST)
H, W = cov.shape[:2]
warp = cv2.warpPerspective(s01, M, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
quad = np.zeros((H, W), np.uint8); cv2.fillConvexPoly(quad, np.round(DST).astype(np.int32), 255)
# source pack silhouette (brown vs light counter) warped, to keep the crimp zigzag edges
sil = np.zeros(s01.shape[:2], np.uint8); cv2.fillConvexPoly(sil, np.round(SRC).astype(np.int32), 255)
INS = np.float32([[158.3 + 3, 620 + 7], [430 - 4, 648.3 + 7], [416.7 - 5, 835 - 6], [153.3 + 3, 800 - 6]])   # inset: no source background/shadow at the edges
quad = np.zeros((H, W), np.uint8); cv2.fillConvexPoly(quad, np.round(INS).astype(np.int32), 255)
# hand polygon (cover px; derived from the 3x grid crop at (100,590)): fingers/thumb in front of the pack
hp = np.float32([(0, 350), (290, 380), (300, 470), (360, 560), (372, 650), (385, 700), (335, 765), (330, 870), (0, 870)]) / 3 + np.float32([100, 590])
hand = np.zeros((H, W), np.uint8); cv2.fillPoly(hand, [np.round(hp).astype(np.int32)], 255)
hsv = cv2.cvtColor(cov, cv2.COLOR_BGR2HSV)
skin = ((hsv[..., 2] > 110) & (hsv[..., 1] < 150) & (hsv[..., 0] < 25)).astype(np.uint8) * 255      # light, orange-pink = skin/nails
occ = cv2.bitwise_and(hand, skin); occ = cv2.morphologyEx(occ, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)); occ = cv2.dilate(occ, np.ones((3, 3), np.uint8))
m = cv2.bitwise_and(quad, cv2.bitwise_not(occ)).astype(np.float32) / 255
m = cv2.GaussianBlur(m, (0, 0), 1.2)[..., None]
# colour/brightness match on the dark-brown wrapper area (excluding bright print)
reg = (quad > 0) & (occ == 0)
dark = reg & (cv2.cvtColor(cov, cv2.COLOR_BGR2GRAY) < 90) & (cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY) < 90)
gain = cov[dark].mean(0) / np.maximum(warp[dark].mean(0), 1)
warp2 = np.clip(warp.astype(np.float32) * gain, 0, 255); warp2 = cv2.GaussianBlur(warp2, (0, 0), 0.7)
res = (cov.astype(np.float32) * (1 - m) + warp2 * m).astype(np.uint8)
cv2.imwrite(str(OUT / "COVER_B_corrected_wrapper_1080x1920.png"), res)
cv2.imwrite(str(OUT / "_occluder_mask.png"), occ)
ch = (np.abs(res.astype(int) - cov.astype(int)).sum(-1) > 0); ys, xs = np.nonzero(ch)
print("gain", gain.round(3), "changed bbox", xs.min(), ys.min(), xs.max(), ys.max(), "px", int(ch.sum()), "occluder px", int((occ > 0).sum()))
box = (100, 590, 470, 880)
a = cov[box[1]:box[3], box[0]:box[2]]; b = res[box[1]:box[3], box[0]:box[2]]
cv2.imwrite(str(OUT / "_zoom.png"), cv2.resize(np.hstack([a, b]), None, fx=2.2, fy=2.2, interpolation=cv2.INTER_LANCZOS4))
