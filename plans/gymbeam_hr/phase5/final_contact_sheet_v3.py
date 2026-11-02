"""Final carousel contact sheet v3 (Phase 7C): slide 5 = FINAL_v3 (zinc claim), slide 3 = FINAL_v2 (PRIPREMA:). Deterministic; no AI, no network, no spend. Originals are only read; v2 sheet is kept."""
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "runs/colla-pink"
D = RUN / "carousel_final"
FF = imageio_ffmpeg.get_ffmpeg_exe()


def frame0(mp4: Path, out: Path):
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(mp4), "-frames:v", "1", "-update", "1", str(out)], check=True)
    return out


s3 = frame0(RUN / "slide3_video/slide3_priprema_FINAL_v2_1080x1350.mp4", D / "slide3_FINAL_v2_VIDEO_FIRST_FRAME.png")
s5 = frame0(RUN / "slide5_video/slide5_napitak_za_ljepotu_FINAL_v3_1080x1350.mp4", D / "slide5_FINAL_v3_VIDEO_FIRST_FRAME.png")
SRC = [D / "slide1_cover_FROZEN_1080x1350.png", D / "slide2_sto_je_unutra_NO_FOOTER_1080x1350.png", s3,
       D / "slide4_kako_pripremiti_1080x1350.png", s5, D / "slide6_odaberi_svoj_okus_FINAL.png"]
PW, PH, GAP = 768, 960, 24                                   # 4:5 panels, same dark ground and thin gaps as the old strip
sheet = Image.new("RGB", (6 * PW + 7 * GAP, PH + 2 * GAP), (24, 20, 22))
for i, p in enumerate(SRC):
    im = Image.open(p).convert("RGB"); assert im.size == (1080, 1350), (p, im.size)
    sheet.paste(im.resize((PW, PH), Image.LANCZOS), (GAP + i * (PW + GAP), GAP))
sheet.save(D / "BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v3.png")
print(sheet.size)
