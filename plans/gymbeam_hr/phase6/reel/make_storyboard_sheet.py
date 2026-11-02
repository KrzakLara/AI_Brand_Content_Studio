"""Storyboard mockup v2 (local only: official GymBeam photos + approved model reference; no AI, no network, no spend)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
R = ROOT / "runs/gymbeam-wafer-reel"; REF = R / "references"
F = lambda s, b=False: ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if b else "C:/Windows/Fonts/segoeui.ttf", s)
AI, LOC, CUT = (46, 125, 90), (70, 100, 150), (190, 110, 40)
# (n, time, name, mode, badge, note, refs)
SHOTS = [
 ("01", "0–1.5 s", "Morning counter", LOC, "LOCAL EDIT", "push-in, light sweep, steam", "S01"),
 ("02", "1.5–4 s", "The pickup", AI, "AI VIDEO · Kling 3 s · $0.705", "new start → current S02 = end frame", "S02"),
 ("03", "4–6.5 s", "Into the gym bag", AI, "AI VIDEO · Kling 3 s · $0.705", "current S03 = start; wafer in, zip closes", "S03"),
 ("04", "6.5–8 s", "Heading out", LOC, "LOCAL EDIT", "2 stills + cut + door foley", None),
 ("05", "8–9.25 s", "Parked car", LOC, "LOCAL EDIT", "seated, bag on seat; slow drift", None),
 ("06", "9.25–12.25 s", "Take out & unwrap", AI, "AI VIDEO · Kling 3 s · $0.705", "new start → current S06 = end frame", "S06"),
 ("07", "12.25–14.5 s", "Crunch hero", CUT, "MATCH CUT · $0 video", "intact → cut + crunch → broken", None),
 ("08", "14.5–17 s", "NEW: Entering the gym", CUT, "MATCH CUT (2 keyframes) · $0 video", "door → cut inside · Kling optional", "S08"),
 ("09", "17–19.5 s", "End frame", LOC, "LOCAL EDIT", "pack + piece; end copy overlay", None),
]
img = {"w": Image.open(REF / "wafer_view1.jpg"), "b": Image.open(REF / "bag_1.jpg"),
       "a": Image.open(REF / "identity_head_slide5.png").convert("RGB")}   # head crop only: no jar, no text  # below the headline: no text in crop
W, H, G = 262, 592, 10
sheet = Image.new("RGB", (9 * W + 10 * G, H + 2 * G + 92), (24, 20, 22)); d = ImageDraw.Draw(sheet)
for i, (n, t, name, col, badge, note, kf) in enumerate(SHOTS):
    x = G + i * (W + G); p = Image.new("RGB", (W, H), (238, 229, 216)); pd = ImageDraw.Draw(p)
    pd.rectangle((0, 0, W, 58), fill=col); pd.text((10, 6), f"SHOT {n} · {t}", font=F(15, True), fill="white"); pd.text((10, 30), badge, font=F(12, True), fill="white")
    pd.text((10, 62), name, font=F(14, True), fill=(60, 40, 30))
    if kf:
        p.paste(Image.open(R / f"keyframes/{kf}_keyframe_1080x1920.png").convert("RGB").resize((W, 466), Image.LANCZOS), (0, 84))
    else:
        pd.text((10, 120), "keyframe not generated yet", font=F(12), fill=(120, 100, 90))
        refs = {"04": ["b"], "05": ["a", "b"], "07": ["w"], "09": ["w", "b"]}[n]
        for j, r in enumerate(refs):
            im = img[r]; im = im.resize((110, 120)) if r == "a" else im.resize((120, 120))
            p.paste(im, (14 + j * 85, 200 + j * 60))
    pd.text((10, 560 - 0) if False else (10, 552), "", font=F(1))
    pd.text((10, 556), note, font=F(10), fill=(60, 40, 30)); pd.text((10, 574), ("GENERATED KEYFRAME" if kf else "MOCKUP – official refs only"), font=F(10), fill=(120, 100, 90))
    sheet.paste(p, (x, G))
y = H + G + 12
d.text((G, y), "AI VIDEO = 3 Kling requests (S02, S03, S06) · 3 s × 0.235 USD/s = 0.705 each = 2.115 USD (est.)    MATCH CUT = S07 + S08 (no video request)    LOCAL EDIT = ffmpeg/Pillow, 0 USD", font=F(13, True), fill=(225, 215, 205))
d.text((G, y + 26), "Total timeline 19.5 s · 9 shots · Keyframe images are separate (5 done = 0.532 USD) · no Kling video generated yet · MOJ MALI GYM ESSENTIAL — speculative portfolio concept, not an official GymBeam collaboration", font=F(12), fill=(190, 180, 170))
sheet.save(R / "storyboard/STORYBOARD_CONTACT_SHEET_v3_9SHOTS.png"); print(sheet.size)
