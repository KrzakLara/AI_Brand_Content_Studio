# FINAL QA REPORT — GymBeam lifestyle Reel ("Moj mali gym essential")

*Speculative portfolio advertisement — not an official GymBeam collaboration, not a real influencer endorsement. The woman is a fictional AI-generated model.*

**Deliverable:** `final/GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL.mp4` — 1080×1920, 24 fps, H.264 (High) + AAC, **19.75 s**, 18.4 MB.
Alternate (foley only, no generated bed): `final/GYMBEAM_WAFER_REEL_FOLEY_ONLY.mp4`. Cover: `final/GYMBEAM_WAFER_REEL_COVER.png`. Contact sheet: `qa/FINAL_REEL_CONTACT_SHEET.png`.

## How QA was done — and its limits
I checked the encoded file's technical properties and looked at 20 sampled frames of the final MP4 plus 8–9 frames of each Kling clip (not every frame of the video). **I could not listen to the audio**; sound timing is correct by construction (cues are placed from the measured segment start frames), not verified by ear. Technical QA passing does **not** mean the video is flawless — see "Remaining defects".

## Checklist
| Check | Result |
|---|---|
| 9:16, 1080×1920, 24 fps, H.264 | ✅ verified from the file |
| Duration 19–20 s | ✅ 19.75 s |
| Same woman and outfit throughout | ✅ mostly. Same hair, white top, cream leggings; gym and bag shots show her from behind/profile. ⚠ some face drift between shots (S06/S03 faces are slightly different from S02) — a viewer who looks closely will notice |
| Calm hair, no wind | ✅ no fan/wind look in any sampled frame; hair moves only with her head. ⚠ S08 walk: hair sways naturally with steps (not wind) |
| Realistic hands | ✅ no deformed fingers seen in sampled frames; ⚠ motion frames in S02 (pickup, ~1.7 s) are motion-blurred and can't be fully verified |
| Wafer wrapper accurate | ✅ brown wrapper, GymBeam logo, "32% PROTEIN WAFER", three green pills, "NET WT. 25g" legible in S01/S09. ⚠ in S02/S03/S06 the small print is softer and the pill text slightly warped; the wrapper in S02/S06 is rendered by the model, not composited from the official photo |
| Duffle bag accurate | ✅ logo patch, tag, handles, strap consistent across S01–S09; one bag per shot |
| Kitchen/car consistent | ✅ same counter and light S01–S03; same cream car interior S05–S07a |
| Parked car only | ✅ engine off, no driving, no phone (S05, S06) |
| Wafer break + visible layers | ⚠ the match cut works visually (intact → broken, layers and filling visible). The wafer's **exact real-world shape/interior is not verified against the actual product** — the generated bar is plausible, based on the wrapper illustration and page description only |
| Gym entrance | ✅ Kling S08 clip: she pushes the glass door and walks in; door and bag stable. ⚠ camera framing drifts slightly compared with the keyframe |
| Audio synced | ⚠ placed from frame timings; **not auditioned**. All sounds are synthesized (see below) and will sound more artificial than real foley |
| Text legible | ✅ opening `MALI RITUALI U POKRETU.` (0–1.5 s) on the free counter area; ending `TVOJ SNACK. TVOJ RITAM.` + `GymBeam 32% Protein Wafer` (from ~16.7 s) beside the wafer. Static, cut-on/cut-off (no animation). ⚠ the end text sits low in the frame (y ≈ 1520–1730); Instagram's bottom UI/caption can cover the label line. ⚠ the end text touches a towel at the right |
| No artifacts | ⚠ **not artifact-free** — see below |
| Text only in post | ✅ no text generated inside AI video; all copy composited with Pillow |

## Remaining visual defects (honest list)
1. **S04 ("heading out") is a crop, not a full shot.** The only accepted S04 keyframe showed her holding the wafer pack (continuity error — it should be in the bag). A reshoot was blocked by the image provider's safety filter (HTTP 400, not billed) and the request quota. S04 therefore uses the **lower part of that frame** (bag, legs, sneakers) where the pack isn't visible, upscaled ~1.56× → slightly soft, and no face. The rejected keyframe is preserved as `keyframes/S04_attempt2_REJECTED_wafer_in_hand_*.png`.
2. **Face variation** between keyframes/clips (jawline and smile differ a little shot to shot).
3. **Small wrapper text** is not perfectly stable in the Kling clips (S02, S06); the hero frames S01/S09 are clean.
4. **S07 crunch shot** is two generated stills with a cut — acceptable per brief, but it is not a continuous break and the wafer geometry is generated.
5. **Slight "AI gloss"**: very smooth skin and strongly stylised light; Kling clips are 3 s each with gentle motion.
6. **S08 composition** emphasises the rear view of the model's figure (leggings fit); consider a more side-on framing if brand tone requires it.
7. **Audio** is entirely synthesized (foley + quiet generated bed); no licensed library music could be obtained (FreePD closed; no login-free CC0 source reachable), so no third-party audio is used. A licensed track should replace the bed for a real release.

## AI vs local editing
| Step | Method |
|---|---|
| 13 keyframes (S01, S02, S02a, S03, S04, S05, S06, S06a, S07a, S07b, S08, S08b, S09) | **AI** — OpenAI image edit (`gpt-image-2.5-sunburst`, 1152×2048, xhigh), reference-conditioned with official GymBeam photos + identity crops |
| Clips S02, S03, S06, S08 | **AI** — fal.ai Kling v4 image-to-video, 3 s, 1080p, start (+end) frame |
| S01, S04, S05, S07a/b, S09 motion | **Local** — Pillow sub-pixel zoom/pan/sway, light sweep (S01) |
| Crossfades, flash on break, speed ease, timeline | **Local** — `assemble_reel.py` |
| Text | **Local** — Pillow overlay, Montserrat |
| Foley + bed | **Local** — numpy synthesis (`foley.py`), no external audio |
| Encode | **Local** — ffmpeg (imageio-ffmpeg), libx264 crf 16 + AAC |

## Spend (Post 3 total)
- Images (actual, from API usage blocks): **1.401013 USD** — 13 successful images + 2 requests rejected by the safety filter (0 USD).
- Kling: **2.820 USD estimated** (4 × 3 s × 0.235 USD/s; billing not confirmed on the fal dashboard).
- **Total ≈ 4.221 USD** of the 4.50 USD cap (image cap 2.00: 1.401 used). No automatic retries.

## Reproduce
`python plans/gymbeam_hr/phase6/reel/gen_keyframe.py <SHOT>` → `run_kling.py <SHOT>` → `assemble_reel.py`.
