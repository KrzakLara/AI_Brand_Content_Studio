# V2 edit decisions and QA (local re-edit, zero new API cost)

**File:** `final/GYMBEAM_WAFER_LIFESTYLE_REEL_V2.mp4` — 1080×1920, 24 fps, H.264 + AAC (quiet foley only), **12.0 s**, 288 frames. Also `..._V2_SILENT.mp4` (no audio) and `final/GYMBEAM_WAFER_REEL_V2_END_FRAME.png`. V1 files are unchanged (`..._FINAL.mp4` still 18,381,718 bytes).
Script: `plans/gymbeam_hr/phase6/reel/assemble_reel_v2.py`. Frame timeline: `logs/assembly_timeline_V2.txt`.

## Timeline (straight cuts only; native framing; no speed changes except none)
| Time | Shot | Source | Used |
|---|---|---|---|
| 0.00–1.50 | 1. Wafer on the kitchen counter + opening text `MALI RITUALI U POKRETU.` | still S01 (hero keyframe), 2% slow drift | 36 fr |
| 1.50–4.33 | 2. She picks up the wafer | Kling S02, frames 0–67 (up to the held pack) | 68 fr |
| 4.33–5.08 | 3. Wafer goes into the bag | Kling S03, frames 0–17 (ends before the closing/zip motion) | 18 fr |
| 5.08–6.25 | 4. Direct cut: seated in the parked car holding the sealed pack | Kling S06, frames 0–27 (before the tearing starts) | 28 fr |
| 6.25–7.75 | 5. Product close-up | crop of S01 hero keyframe (official-style wrapper render, 1.45×) | 36 fr |
| 7.75–9.50 | 6. Entering the gym | Kling S08, frames 26–67 (after the first door contact, to the end) | 42 fr |
| 9.50–12.00 | 7. End frame + `TVOJ SNACK. TVOJ RITAM.` / `GymBeam 32% Protein Wafer` | still S01, static, 1.12× | 60 fr |

## Removed / trimmed
- **S03 second half** (frames 18–72, bag closing/zip): removed.
- **S04 heading to the car**: removed entirely. **S05 parked-car establishing shot**: removed entirely.
- **S06 unwrapping** (frames 28–72): removed; only the stable "holding the sealed pack" start is kept.
- **S07 wafer macro / broken wafer (S07a/S07b)**: removed — the generated interior does not match the real product, and no trustworthy source for the real interior exists in the project. Replaced by a clean close-up of the wrapped pack.
- **S08**: first 26 frames (awkward bag-in-hand walk before the door) removed; **S09** (broken wafer hero) removed — it also contained the invented broken piece.
- **Music, synthesized bed, whooshes, door/zip/crunch sounds**: removed. Remaining audio: soft rustle on the pack lift, soft rustle as the wafer slides in, three faint footsteps in the gym, near-silent room tone.
- V1 zoom/push-ins and crossfades: removed.

## QA — frames checked around EVERY cut (4 frames each, `qa/V2_CUT_INSPECTION.png`) plus 20 timeline samples (`qa/V2_CONTACT_SHEET.png`)
- No black bars, no flash frames, no cropped logo at any cut; all six cuts are clean straight cuts.
- Opening text sits under the pack in the counter area, not covering the packaging; end text sits left of/below the pack, clear of the bag and above the Instagram bottom UI (text at y≈1390–1560 of 1920).
- Pack text is stable at S01/close-up/end; in S02 (lift) and S06 (sealed pack) it is smaller and less crisp.
- Hair calm in all kept segments; no wind. No unwrapping, zipper, or tearing remains.
- I viewed sampled frames, **not the video at real-time playback**, and I could not listen to the audio; the foley is placed from frame times and is quiet by design.

## Remaining defects (not hidden)
1. **S03→S06 cut**: she is in a different place/pose and, in the kitchen, the wafer is still partly visible in her hand while in S06 she holds the sealed pack — a continuity jump that the cut cannot hide, though it reads as a normal edit.
2. **S02 pickup (frames ~36–52)** has motion blur where the pack is lifted; no deformed fingers were visible in sampled frames, but the pack looks smeared for ~0.2 s.
3. **The close-up is an enlargement (1.45×) of a 1152-px-wide generated still**, so slightly soft; the pack is the model's render of the wrapper, not the official photo (official photos are only 700 px wide).
4. **The end frame reuses S01** — no new "broken wafer" content, by design.
5. **S08** shows her from behind; the bag is held low and swings, but weight and position look believable in the kept segment. Lower-body framing remains stronger than the face; consider a different angle for a real release.
6. **Face varies slightly** between kitchen, car, and gym shots.
7. **No music** — a licensed track must be added by hand for release if wanted.

## Cost
No image or Kling request was made for V2. Spend ledger unchanged: images 1.401013 USD (15 requests logged), Kling 2.82 USD estimated (4 requests). **New API cost: 0.00 USD.**
