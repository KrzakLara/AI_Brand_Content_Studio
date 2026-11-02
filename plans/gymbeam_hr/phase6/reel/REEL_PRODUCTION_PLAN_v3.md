# POST 3 — Production plan v3 (9 shots; supersedes v2 §1–§2)

Status: keyframes S01, S02, S03, S06, **S08 (new gym entrance)** generated (0.5320 USD). **No Kling request has been made.** Budget ceiling of 4.50 USD for Post 3 is still the *proposed* cap.

## 1. Storyboard — 9 shots, 19.5 s

| # | Time | Shot | Method | Paid video? |
|---|---|---|---|---|
| 01 | 0–1.5 | Morning counter | LOCAL: S01 keyframe + push-in, light sweep, steam | no |
| 02 | 1.5–4 | **Pickup** | **Kling 3 s** | 0.705 |
| 03 | 4–6.5 | **Wafer into the gym bag, zip** | **Kling 3 s** | 0.705 |
| 04 | 6.5–8 | Heading out | LOCAL: 2 stills + cut + door foley | no |
| 05 | 8–9.25 | Parked car | LOCAL: slow drift | no |
| 06 | 9.25–12.25 | **Take out + unwrap in parked car** | **Kling 3 s** | 0.705 |
| 07 | 12.25–14.5 | Crunch hero | MATCH CUT (intact → cut + crunch → broken) | no |
| 08 | 14.5–17 | **NEW — Entering the gym** | **MATCH CUT of 2 keyframes** (recommended) — optional Kling 3 s | 0 (or 0.705) |
| 09 | 17–19.5 | End frame (was S08) | LOCAL: push-in + `TVOJ SNACK. TVOJ RITAM.` + label | no |

Narrative: kitchen → pickup → bag → leave home → parked car → take out wafer → crunch → **enter gym** → final product shot.
Note on order: the crunch (S07) happens in the car (it continues S06), then S08 shows her arriving at the gym.

## 2. S08 — motion concept (approach → open door → walk in)

Generated keyframe **S08** (approach/door-handle moment): `keyframes/S08_keyframe_1080x1920.png`, cost 0.1171 USD (req_d57c8cf4…).

**Recommended: no Kling for S08. Two keyframes + a designed match cut.**
1. **S08a (generated):** she reaches the door; local 1.2 s push-in/parallax (glass reflections slide), subtle bag sway (local warp optional).
2. **Cut on the door push** (door foley + whoosh, 6-frame motion-blur dissolve).
3. **S08b (to generate, ≈ 0.11 USD):** same gym lobby seen from inside, she is a step beyond the door, back to camera, door closing behind — local drift. Match: same outfit, same bag in same hand, same light direction.
Why not Kling: a walk through a glass door with a swinging bag is the motion most prone to morphing (door geometry, bag, legs); the cut reads cinematic and costs 0.
**Option B (only if you want continuous motion):** Kling 3 s with S08a as start and S08b as end frame = **+0.705 USD** (needs the end-frame parameter added to the adapter; free code change).

## 3. Continuity assessment of S02 and S06 (not modified)

- **S02 (current):** she already holds the wafer up to camera → it cannot show a "pickup from the counter" when used as a *start* frame (nothing left to pick up).
  → Use current S02 as the **END frame** of the pickup clip. Needs a new **S02a start frame**: same kitchen/outfit, wafer lying on the counter, her hand reaching toward it (≈ 0.11 USD).
- **S03 (current):** wafer is halfway into the bag → works as the **START** frame for "places it in, zips the bag". End frame optional (S03b: zipped bag; ≈ 0.11 USD, skip unless the first clip fails).
- **S06 (current):** the wrapper is already open with the wafer peeking out → cannot support "take out and open".
  → Use current S06 as the **END frame**; generate **S06a start**: closed pack held in her hand, bag open on the seat (≈ 0.11 USD).
- Kling v4 accepts `end_image_url`; the adapter `FalKlingVideo` currently sends only the start image — a small free code change is required before any clip is submitted.

## 4. Cost update (estimates; billed amounts only where stated)

**Spent so far (actual, from API usage blocks):** 5 images = **0.5320 USD** (S01 0.0855, S02 0.1089, S03 0.1143, S06 0.1061, S08 0.1171; avg 0.1064). Image stage budget 2.00 → **1.468 left**.

**Images still needed (9):** S02a, S06a, S04-A, S04-B, S05, S07-intact, S07-broken, S08b, S09. At ≈ 0.11 each ≈ **0.99 USD**. Retake allowance 4 × 0.11 = **0.44 USD** (every retake needs your approval).

**Kling (estimated at 0.235 USD/s, 1080p):**
- Option A (recommended): S02, S03, S06 → 3 × 0.705 = **2.115 USD**
- Option B (+ S08 clip): 4 × 0.705 = **2.820 USD**

| | Images (spent + needed + retakes) | Kling | **Total** |
|---|---|---|---|
| Option A, no retakes | 0.532 + 0.99 = 1.52 | 2.115 | **≈ 3.64** |
| **Option A, with 4 retakes** | 1.96 | 2.115 | **≈ 4.08** |
| Option B, no retakes | 1.52 | 2.820 | ≈ 4.34 |
| Option B, with 4 retakes | 1.96 | 2.820 | ≈ 4.78 (**exceeds 4.50**) |

→ The **4.50 USD ceiling holds for Option A in every case**. Option B fits only if retakes are limited to ≈ 1 (4.45). **No new spending is authorized until you approve a ceiling and each stage.**
Kling price remains an estimate (0.235 USD/s from your pricing note; fal's API shows 0.157 USD/s without a tier). Image prices are real (usage blocks).

## 5. Open checkpoints
1 ☐ S08 keyframe approval (face is in profile; composition is rear-view — see QA notes in the report) · 2 ☐ Option A or B for S08 · 3 ☐ ceiling 4.50 USD and generate S02a/S06a/S08b + remaining keyframes · 4 ☐ audio candidates · 5 ☐ each Kling clip, one at a time · 6 ☐ rough cut · 7 ☐ final with sound + copy/compliance read.
