"""Wafer snap PROTOTYPES (local, zero cost). Built only from OFFICIAL GymBeam photos (references/official_v2) + our own counter still.
A = match cut between two official photos on their native backdrop (no compositing). B = real wafer pieces keyed out and composited on our kitchen counter."""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import foley as fo  # noqa: E402
from reel_lib import FF, FPS, H, W  # noqa: E402

R = ROOT / "runs/gymbeam-wafer-reel"; OFF = R / "references/official_v2"; PRO = R / "prototypes"
P_INTACT = OFF / "hr_copy_of_untitled-1_0004_4_2__1.jpg"     # wafer sliding out of the wrapper (right), loose pieces left
P_BROKEN = OFF / "hr_copy_of_untitled-1_0002_8_1.jpg"        # wafer broken into three pieces (centre)
RNG = np.random.default_rng(7)


def vcrop(img, cx, cy, z=1.0):
    """9:16 crop of a 1200x1200 photo centred on (cx, cy) in source px, scaled to 1080x1920 (z>1 = tighter)."""
    cw, ch = 675 / z, 1200 / z
    x0 = min(max(cx - cw / 2, 0), img.width - cw); y0 = min(max(cy - ch / 2, 0), img.height - ch)
    return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS)


def drift(img_fn, n, z0, z1):
    for k in range(n):
        yield np.asarray(img_fn(z0 + (z1 - z0) * k / max(n - 1, 1)))


def crumbs(frame, k, n, origin, count=26):
    """Procedural brown crumbs falling after the break (k = frames since the break)."""
    out = frame.copy(); rng = np.random.default_rng(3)
    for i in range(count):
        vx, vy = rng.normal(0, 1.2), rng.uniform(1, 4); x = origin[0] + rng.normal(0, 70) + vx * k * 2.0; y = origin[1] + rng.normal(0, 25) + (vy * k + 0.35 * k * k) * 1.6
        r = int(rng.uniform(2, 5)); col = np.array([196, 142, 78]) * rng.uniform(0.7, 1.05)
        if 0 <= x < W - r and 0 <= y < H - r and k > 0:
            out[int(y):int(y) + r, int(x):int(x) + r] = col.astype(np.uint8)
    return out


def encode(frames, name, audio):
    silent = PRO / f"_{name}_s.mp4"
    p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16",
                          "-preset", "slow", "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(PRO / f"{name}.mp4")], check=True)
    silent.unlink()


def audio(total, t_break):
    mix = np.zeros(int((total + 0.5) * fo.SR)); fo.place(mix, fo.crunch(), t_break, 1.0)
    fo.place(mix, fo.rustle(0.25, 40), t_break - 0.5, 0.15)
    fo.to_wav(PRO / "snap_crunch.wav", mix[: int(total * fo.SR)], peak=0.7); return PRO / "snap_crunch.wav"


def proto_a():
    a, b = Image.open(P_INTACT).convert("RGB"), Image.open(P_BROKEN).convert("RGB")
    nA, nB = 20, 28                                           # 0.83 s intact, 1.17 s broken  = 2.0 s
    fa = list(drift(lambda z: vcrop(a, 692, 604, z), nA, 1.0, 1.03))
    fb = [np.asarray(vcrop(b, 560, 540, 1.0 + 0.03 * k / (nB - 1))) for k in range(nB)]
    frames = list(fa)
    for k in range(nB):
        f = fb[k]
        if k < 2:
            f = (f.astype(np.float32) * (1 - (0.7, 0.3)[k]) + 255 * (0.7, 0.3)[k]).astype(np.uint8)  # flash on the break
        frames.append(crumbs(f, k, nB, (W // 2, int(H * 0.45))))
    encode(frames, "SNAP_PROTOTYPE_A_official_photos_match_cut", audio(len(frames) / FPS, nA / FPS))
    return frames


def key_out(img):
    """Alpha for objects on the green backdrop + cast-shadow map; only the biggest object blob is kept (neighbouring packs / stray bits are dropped)."""
    import cv2
    a = np.asarray(img).astype(np.float32); bg = np.median(a[:30, :30].reshape(-1, 3), 0)
    g = a[..., 1] - np.maximum(a[..., 0], a[..., 2]); bgg = bg[1] - max(bg[0], bg[2])
    alpha = np.clip(1 - (g - 8) / max(bgg - 20, 1), 0, 1); alpha = np.clip((alpha - 0.25) / 0.5, 0, 1)
    m = (alpha > 0.5).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        touches = x <= 1 or y <= 1 or x + w >= m.shape[1] - 1 or y + h >= m.shape[0] - 1
        if area > 1500 and not touches:
            keep[lab == i] = 1
    keep = cv2.dilate(keep, np.ones((7, 7), np.uint8)); alpha = alpha * keep
    shade = np.clip(1 - a[..., 1] / bg[1], 0, 0.9) * (g > 8)
    return alpha, shade


def proto_b():
    a, b = Image.open(P_INTACT).convert("RGB"), Image.open(P_BROKEN).convert("RGB")
    cnt = Image.open(R / "keyframes/S01_raw.png").convert("RGB").crop((0, 1000, 1152, 2048))      # sharp counter + towel region of our own still
    sc = H / cnt.height; cv = cnt.resize((int(cnt.width * sc), H), Image.LANCZOS); x0 = (cv.width - W) // 2
    canvas = np.asarray(cv.crop((x0, 0, x0 + W, H)).filter(ImageFilter.GaussianBlur(16))).astype(np.float32)
    canvas = canvas * 0.92 + 14
    def comp(src, box, scale, centre):
        s = src.crop(box); al, sh = key_out(s)
        s2 = s.resize((int(s.width * scale), int(s.height * scale)), Image.LANCZOS)
        rs = lambda m: np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize(s2.size, Image.LANCZOS)).astype(np.float32)[..., None] / 255
        al, sh = rs(al), rs(sh); out = canvas.copy(); xx = int(centre[0] - s2.width / 2); yy = int(centre[1] - s2.height / 2)
        reg = out[yy:yy + s2.height, xx:xx + s2.width]; reg *= (1 - 0.5 * sh * (1 - al))
        fg = np.asarray(s2).astype(np.float32) * np.array([1.0, 0.97, 0.92], np.float32); reg[:] = reg * (1 - al) + fg * al
        return out.astype(np.uint8)
    A = comp(a, (560, 320, 1170, 740), 1.6, (W // 2, 960))
    B = comp(b, (380, 340, 840, 800), 1.8, (W // 2, 960))
    nA, nB = 20, 28; frames = [A] * nA
    for k in range(nB):
        f = B
        if k < 2: f = (B.astype(np.float32) * (1 - (0.7, 0.3)[k]) + 255 * (0.7, 0.3)[k]).astype(np.uint8)
        frames.append(crumbs(f, k, nB, (W // 2, 900)))
    encode(frames, "SNAP_PROTOTYPE_B_composite_on_counter", audio(len(frames) / FPS, nA / FPS))
    Image.fromarray(A).save(PRO / "protoB_frame_intact.png"); Image.fromarray(frames[nA + 8]).save(PRO / "protoB_frame_broken.png")


if __name__ == "__main__":
    fa = proto_a(); Image.fromarray(fa[10]).save(PRO / "protoA_frame_intact.png"); Image.fromarray(fa[20 + 8]).save(PRO / "protoA_frame_broken.png")
    proto_b()
