# V4 edit report — best zero-cost edit from existing assets

**File:** `final/GYMBEAM_WAFER_LIFESTYLE_REEL_V4.mp4` — 1080×1920, 24 fps, H.264 + AAC (very quiet foley, no music), **7.92 s**, 190 frames. V1, V2, V3 untouched. Script: `plans/gymbeam_hr/phase6/reel/assemble_reel_v4.py`; timeline: `logs/assembly_timeline_V4.txt`; contact sheet `qa/V4_CONTACT_SHEET.png`; cut inspection `qa/V4_CUT_INSPECTION.png` (4 frames at each of 6 cuts).

## Timeline (straight cuts, native framing, no zooms except 2% drift on the opening still)
| Out time | Segment | Source frames | Why this range |
|---|---|---|---|
| 0.00–1.50 | Wafer on the kitchen counter + `MALI RITUALI U POKRETU.` | S01 keyframe | text under the pack |
| 1.50–2.79 | She reaches for the pack and touches it | S02 f0–f30 | natural reach, pack clean on the counter |
| 2.79–3.58 | **jump cut** → she holds the pack up, smiling | S02 f54–f72 | hides S02 f31–f53, where the pack smears into a flat dark strip while being lifted |
| 3.58–4.38 | Wafer slides into the open gym bag | S03 f0–f18 | pack intact until it is inside; hand then leaves the bag |
| 4.38–5.33 | Direct cut: in the parked car holding the sealed pack | S06 f4–f26 | stable pack, hands correct, engine-off car |
| 5.33–5.96 | **jump cut** → she pinches the top of the wrapper to open it | S06 f38–f52 | wrapper still intact, fingers clean |
| 5.96–7.92 | Enters the gym — **LAST SHOT** | S08 f26–f72 | accepted gym entrance (same range as V3) |

## Frames deliberately removed (checked at full-res crops)
- **S02 f31–f53:** pack turns into a motion-smeared flat strip / garbled print while lifted.
- **S03 f19–f72:** after the wafer is inside, the hand floats/blurs above the bag (f20–f28) and the bag later starts closing (f54+) — the unnatural closing/zipper part.
- **S06 f27–f37:** fingers pinch air with blurred, odd shapes. **S06 f54–f72:** the top of the wrapper peels back and a pale flat rectangle (the wafer) pokes out — it reads as paper/cardboard, so every one of these frames is out. The wafer therefore never appears unwrapped in the car.

## Wafer snap / crunch — checked, NOT used
Compared the generated intact/broken pair (`keyframes/S07a_raw.png`, `S07b_raw.png`) with all official GymBeam images in `references/`. The official photos show only the sealed wrapper (and a 16-pack display box). The only depiction of the wafer's inside is the **wrapper illustration: uncoated golden wafer sheets with white cream and hazelnuts**, while the generated bar is a **chocolate-coated, bumpy-textured bar** with a different cross-section. The page text describes "three crispy wafers, milk and chocolate-nougat filling, nut pieces" and does not state a chocolate coating or the bar's dimensions. I therefore cannot verify the generated bar, and it conflicts with the only official picture → not used, and no crunch sound is added (a crunch without a real break would be a fake). The match cut itself is technically easy (same framing already exists in S07a/S07b); the missing piece is a trustworthy picture of the real wafer.
Also not used: the close-up of the wrapper (removed by your instruction), the end card, S04, S05, S09.

## Zero cost
No image or Kling request. Ledger unchanged: images 1.401013 USD (15 requests logged), Kling 2.82 USD (4 requests, estimated). New API cost **0.00 USD**.

## What this edit cannot show (needs material we don't have)
1. The wafer **unwrapped** / taken out in the car without looking like paper.
2. A **wafer snap + crunch** that is accurate to the real product (no photo of the real wafer).
3. The bag being **zipped or carried out**, and **her walking to / entering the car** (no clean footage exists).
4. Total length 7.9 s — shorter than the 10–13 s target, because the clean, usable action is about this long; padding it would mean repeating footage.
5. The face varies slightly between kitchen, car and gym clips; the gym shot is from behind, so no face-to-face continuity there. Sound was not auditioned and frames, not real-time playback, were reviewed.
