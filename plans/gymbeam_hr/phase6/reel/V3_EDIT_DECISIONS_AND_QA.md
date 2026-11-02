# V3 edit decisions and QA (story edit; local only, zero new API cost)

**File:** `final/GYMBEAM_WAFER_LIFESTYLE_REEL_V3.mp4` — 1080×1920, 24 fps, H.264 + AAC (quiet foley only), **10.96 s**, 263 frames. V1 (`..._FINAL.mp4`) and V2 are untouched.
Script: `plans/gymbeam_hr/phase6/reel/assemble_reel_v3.py` · timeline: `logs/assembly_timeline_V3.txt` · audio: `audio/V3_foley_only_mix.wav`.

## Final sequence (straight cuts only, native framing, no zooms except a 2% drift on the opening still, no crossfades)
| Time | Shot | Source frames | Notes |
|---|---|---|---|
| 0.00–1.50 | 1. Wafer on the kitchen counter + `MALI RITUALI U POKRETU.` | still S01 (1.0→1.02× drift) | text sits under the pack, wafer not covered |
| 1.50–4.54 | 2. She picks up the wafer, holds it smiling (your first-screenshot shot) | Kling S02 frames 0–72 (full clip) | unchanged |
| 4.54–6.12 | 3. Wafer goes into the open bag | Kling S03 frames 0–37 | wafer slides into the already-open bag; she looks at the bag; cut BEFORE any closing |
| 6.12–9.00 | 5. Parked car: holds the sealed pack, then opens the top and the wafer appears | Kling S06 frames 4–72 | see note |
| 9.00–10.96 | 6. Enters the gym (LAST SHOT) | Kling S08 frames 26–72 | after the first awkward bag swing; ends on her walking into the gym |

Shot 4 (entering the car) was skipped: no usable footage exists (S04 was a crop of a rejected keyframe; no car-approach clip was ever generated). Direct cut bag → car, as you allowed.

## Removed completely
Isolated pack close-up, the product shot between car and gym, the broken-wafer shot (S07a/S07b), the final packshot/end card (S09), S04, S05, crossfades, zooms/push-ins, music, whooshes, door/zip/crunch sounds. No footage repeats. No end slogan: the gym-entrance frame is filled by the woman, bag and doorway, so there is no free area where "TVOJ SNACK. TVOJ RITAM." would not cover them — omitted as you instructed.

## What I inspected
- **Raw S03 (frames 6–72, every 2nd–6th frame)**: wafer enters the bag by ~f16; f16–f48 she keeps adjusting the open bag (hands at its rim, no deformation); the bag top starts to close/curve from ~f54 — that is the unnatural closing, **cut off at f37**. No zipper-opening action exists in the footage (the bag is already open at frame 0), so none is shown; I did not fabricate it.
- **Raw S06 (every 4th frame + 1080-px hand crops at f20–f72)**: stable hold of the sealed pack f0–f28; she pinches the top f34–f46 (brief motion blur on the fingers at ~f34); f52–f72 she pulls the top open and the wafer appears at the opening. At full resolution fingers and wrapper look believable — better than the V2 judgement from small thumbnails — so I used f4–f72 instead of cutting to a still. I checked 12 crops of the hands through the used range (`qa/V3_S06_hands_check.png`).
- **Frames around every cut** (4 per cut, `qa/V3_CUT_INSPECTION.png`): no black bars, no flashes, no cropped logos. `qa/V3_CONTACT_SHEET.png` = 18 samples across the timeline.
- **Last scene confirmed:** last frames (10.4–10.96 s) show her walking through the gym entrance with the bag.

## Remaining defects (not hidden)
1. S03→S06 is a hard continuity jump (kitchen → car, wafer in bag → sealed pack in hand). It is a normal editorial cut, but a close viewer will notice the wafer is back.
2. S06 f34–f36: fingers motion-blurred for ~0.1 s; the "wafer appears" at the end is the pack opening, not a full unwrap.
3. S03 has ~0.8 s of hand adjustment after the wafer is in (the hands do not do anything specific), and the clip does not show the bag being *opened*; the bag is open from frame 0.
4. S08 is rear/profile view; face is not shown; some camera drift vs. the keyframe. The last frames end while she is still walking (no "arrival" beat).
5. Faces vary slightly between kitchen, car, and gym clips.
6. No music and no end card/slogan by instruction. Audio was not auditioned (placed from frame times; very quiet).
7. I reviewed frames, not real-time playback.

## Cost
No image or video request made for V3. Ledger unchanged: images 1.401013 USD (15 requests logged), Kling 2.82 USD (4 requests, estimated). **New API cost: 0.00 USD.**
