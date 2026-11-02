# POST 3 — "MOJ MALI GYM ESSENTIAL" — GymBeam lifestyle Reel (9:16)

Status: **PLANNING ONLY — free preflight complete. No paid image/video request has been made. Nothing is approved yet.**
Disclaimer (keep in every deliverable): *speculative portfolio advertisement — not an official GymBeam collaboration and not a real influencer endorsement. Fictional AI-generated model.*

Folder: `runs/gymbeam-wafer-reel/` · Planning copy: `plans/gymbeam_hr/phase6/reel/` · Posts 1 and 2 are untouched.

---

## 1. Verified product facts (sources: `SOURCE_LEDGER.md`)

**Primary — GymBeam 32% Protein Wafer 25 g** — https://gymbeam.hr/32-protein-wafer-gymbeam.html (read 2026-10-29)
- Pack: flat horizontal pillow wrapper, **chocolate-brown** with "GymBeam" logo top-left, "32% PROTEIN WAFER" in bold white/cream, three **green pills** (WITH HAZELNUTS · LOW SUGAR · CRISPY TEXTURE), "NET WT. 25 g" top-right, an illustration of the layered wafer with hazelnuts at the bottom.
- Product: layered wafer — three crispy wafers, milk and chocolate-nougat filling with pieces of nuts.
- Nutrition (parsed from page): per 100 g — 2308 kJ / 550 kcal, fat 39 g (sat. 20 g), carbs 20 g (sugars 1.8 g), **protein 32 g**, salt 0.52 g; **per 25 g wafer — 577 kJ / 138 kcal, fat 9.7 g, protein 7.9 g**, sugars 0.5 g, salt 0.13 g.
- **Never write "32 g protein per bar".** Correct framing: "32% protein", **7.9 g protein per 25 g wafer**.
- Allergens on page: gluten, egg, soy, milk, tree nuts (hazelnut). Storage: dry place, room temperature.

**Secondary — GymBeam Urban Duffle Bag Black** — https://gymbeam.hr/urban-duffle-bag-black-gymbeam.html
- Black, grained (leather-look) barrel duffle; two rolled top handles; two-way zip; **rectangular black "GymBeam" logo patch** on the front; small leather-look luggage tag with embossed GymBeam logo hanging from a handle ring; detachable adjustable shoulder strap with swivel clips; zipped end pocket.
- Source inconsistencies to resolve before using any spec on screen: material listed as "Koža" (leather) while photos look like grained faux leather; dimensions row reads "45 × 40 × 3 cm" (height 3 cm is clearly not the bag). **No bag material/size claim goes into any on-screen copy or caption.**

**Reference imagery**: 12 official GymBeam photos downloaded (`references/`, hashes in `references/reference_ledger.json`). **Largest official size is 700×700 px** — enough for identity/shape reference, **not** enough to composite crisp logos at 1080×1920 close-up. See risk R2.

**Instagram inspiration reel** (`DeZnX1dAPid`): only page metadata (caption) was reachable; the video itself was **not viewed or analyzed**. The caption returned is about a different GymBeam product (a "LOCK IN" gaming supplement), so it cannot be used as a stylistic reference. No claim is made about its look; this plan is original.

---

## 2. Actress identity strategy (same woman, calm hair)

Identity anchors (in `references/`, copies — originals untouched):
- `actress_ref_slide1_cover_FROZEN.png` (face, hair, skin, athletic build)
- `actress_ref_slide5_hair_calmed_startframe.png` (calm hair, smile, outfit)
- `actress_ref_slide5_video_frame0.png`

Lessons from Post 2 videos, applied here:
1. **Face drift** appeared in Kling clips longer than ~3 s and when she turns / looks up. → Keep face visible only where needed; most shots use **hands, back or three-quarter angle**; every clip ≤ 3–4 s; start every clip from a keyframe that already contains the approved face.
2. **Kling re-framed (zoomed out) despite "locked camera"**. → Plan for it: compose keyframes slightly tighter than the final crop and crop/scale in post; verify framing before accepting a clip.
3. **Wind/fan hair**. → Keyframes must show hair *already hanging calmly over the shoulders/tied back*; prompt explicitly: "no wind, no fan, hair stays in place". Prefer a **low ponytail or hair over one shoulder** for the walking shot (the only shot with real body motion).
4. Outfit: coordinated **white/cream gym set + neutral jacket** — consistent across shots; no logos on clothing.
5. Each keyframe is checked against the three anchors (face crop side-by-side) **before** it is used for video. Fail → regenerate keyframe (approval needed if over budget), never "fix in Kling".

---

## 3. Eight-shot storyboard (target 18.0 s, 1080×1920, 24 fps)

| # | Time | Shot | How it is made | Face on screen |
|---|---|---|---|---|
| 01 | 0–2 s | **Morning counter** — real wafer pack on cream stone counter, morning light, keys + minimal coffee cup, slow push-in; opening text | Keyframe (image gen with official pack reference) → **local push-in (Ken Burns/parallax), no Kling** | none |
| 02 | 2–4 s | **Pickup** — her hand (and forearm) reaches in and lifts the pack | **Kling 3 s** from keyframe (hand + pack in frame) | none/partial |
| 03 | 4–6 s | **Gym bag** — close-up of the Urban Duffle; wafer goes in, zip adjusted | Keyframe(s) of open bag + closed bag; **local push-in + cross-dissolve/match cut**; wafer entering = hand-in-frame keyframe pair | none |
| 04 | 6–8 s | **Heading out** — she walks with the bag toward her parked car; calm hair | **Kling 3 s** (the only real body motion) from a back/three-quarter keyframe | profile/back |
| 05 | 8–10 s | **Parked car** — seated in a parked car, bag on passenger seat, engine off, no phone/driving | Keyframe → **local slow drift** | three-quarter |
| 06 | 10–12 s | **The snack** — takes wafer from bag, opens wrapper (tactile close-up) | Keyframe pair (closed → torn open) → **local cut/zoom** + wrapper SFX | none |
| 07 | 12–15 s | **Crunch hero** — macro, wafer broken in half | **Primary plan: controlled cut** — keyframe A (intact, held between fingertips) → hard cut with crunch SFX + 2-frame flash → keyframe B (two clean halves, layers visible). **Optional Kling 4 s** only if keyframes pass QA and you approve the extra spend | hands only |
| 08 | 15–18 s | **End frame** — pack + broken piece, bag softly out of focus behind; end copy | Keyframe → local slow push-in; text composited | none |

Transitions: simple match cuts + short dissolves (4–6 frames). Colour grade: warm cream/beige/white/black, gentle contrast, light grain — applied once to the whole timeline for continuity.

### On-screen text (deterministic overlay in post, never generated)
- **0–2 s:** `MALI RITUALI U POKRETU.` (static, no fade tricks beyond a 6-frame dissolve at cut)
- 2–15 s: **no text** (clean imagery)
- **15–18 s:** `TVOJ SNACK. TVOJ RITAM.` + small label `GymBeam 32% Protein Wafer`
- Typography: clean bold sans-serif (Montserrat, as in the project); colour: espresso/dark chocolate on light grounds, white on dark — chosen per shot for legibility. Safe zone: keep text inside the central 1080×1420 area (Reel UI overlaps top ~250 px and bottom ~340 px).

### Audio
- **Version A (preferred): music + foley.** Foley cues: pack pickup (≈2.4 s), bag zip (≈5.0 s), car door (≈8.0 s), wrapper tear (≈10.5 s), **wafer crunch (≈13.2 s, hero)**. *No audio assets exist locally yet.* Options for approval: (a) royalty-free tracks/SFX from a licensed source (Pixabay/Freesound CC0 — licence recorded per file); (b) synthesized foley (free, lower realism). Music: soft, minimal, warm lo-fi/acoustic ~90–100 BPM, licence-checked.
- **Version B (optional): Croatian voiceover** — *"Mobitel, ključevi, torba… i nešto slatko za put. GymBeam Protein Wafer — mali predah u danu."* ≈ 9–10 s read. **No TTS will be generated or paid for without approval.**

### Caption (draft)
> Od jutarnjih obaveza do treninga — neke sitnice jednostavno uvijek idu sa mnom. 🤎
>
> GymBeam 32% Protein Wafer.
>
> #GymBeam #ProteinWafer #GymRoutine

Add (proposed): *"Zamišljeni portfolio oglas — nije službena suradnja s GymBeamom."* Any nutrition claim in the caption must use "32% proteina" or "7,9 g proteina po vafelu (25 g)" — nothing else.

---

## 4. Keyframes, composition strategy and risk register

Keyframe plan (draft prompts in `prompts/keyframe_prompts_DRAFT.md` — **not sent**): 8–10 images at 1080×1920. The existing `OpenAIImageEdit` adapter takes multiple reference images; each package/bag shot gets the official photos as references.

| Risk | Why | Mitigation |
|---|---|---|
| R1 Package text/logo drift | generative models mangle small print | Reference-conditioned edit; **QA = side-by-side vs official photo**; fallback: **composite the real wrapper PNG (cut-out of official photo)** onto the keyframe with perspective/shadow, and for shots with no readable text (hand, far shots) accept stylised accuracy |
| R2 Official images only 700 px | blurry if enlarged for close-ups | Close-ups use generated keyframe (logo checked) or a composite at ≤ ~40% of frame width; ask GymBeam for hi-res assets only if this became a real collaboration (not needed for portfolio) |
| R3 Wafer break realism | deformable food + fingers | Controlled cut (two QA'd keyframes), not continuous motion; reference = layered wafer illustration on the wrapper + product description; reject melting/warped geometry |
| R4 Face drift between shots | seen in Post 2 videos | tight clips, minimal face time, anchor comparison per keyframe/clip |
| R5 Wind-blown hair | seen in Post 2 | calm-hair keyframes, explicit negative prompt, hair tied/over shoulder in walking shot |
| R6 Safety | food + car | **Car parked, engine off, no driving, no phone use; eating happens while parked** |
| R7 Misleading claims | "32%" vs "32 g" | Wording locked above; QA checks every string |
| R8 Kling re-frames | seen twice | keep composition margin; verify before accepting |

---

## 5. Video generation vs local editing

Only **2–3 shots justify paid Kling**; everything else is deterministic (Pillow/ffmpeg: push-ins, drifts, cuts, dissolves, text, audio mix).

| Clip | Duration | Est. price @ 1080p (0.235 USD/s) |
|---|---|---|
| S02 pickup | 3 s | 0.705 |
| S04 walk to car | 3 s | 0.705 |
| S07 crunch (optional) | 4 s | 0.940 |

Kling is billed **per second**, so short clips are cheaper; Kling's minimum is 3 s.
Rate used: 0.235 USD/s for 1080p (your figure; fal's price endpoint only shows 0.157 USD/s without a resolution tier, so the higher figure is used for safety). **Billing is an estimate until confirmed on the fal.ai dashboard.**

---

## 6. Budget (estimates — not billed amounts)

| Item | Low | High | Basis |
|---|---|---|---|
| Image keyframes (8–10 images + ~4 retakes) | 1.10 | 1.80 | Post 2 averaged ≈ 0.09 USD/request in the ledger (11 requests = 0.997 USD); higher end allows larger 1080×1920 / multi-reference edits. **Assumption.** |
| Kling S02 + S04 (3 s each) | 1.41 | 1.41 | 2 × 0.705 |
| Kling S07 (optional, 4 s) | 0.00 | 0.94 | only if cut-based plan is rejected |
| Audio (music/foley/TTS) | 0.00 | 0.00 | free licensed/synthesized; **no paid TTS** |
| **Total** | **≈ 2.5** | **≈ 4.2** | |

Proposed hard cap for approval: **4.50 USD** total for Post 3 (images + video), enforced by the existing guards (`OpenAIImageEdit` budget/request limits, `FalKlingVideo` 1-request-per-run). **No automatic retries.** Any retake beyond the cap needs a new approval. Nothing is spent until you approve the cap.

---

## 7. Human approval checkpoints

1. ☐ **This storyboard & creative direction** (shot list, text, caption, disclaimer).
2. ☐ **Audio direction** (A: music+foley, source of licensed audio; B: voiceover yes/no).
3. ☐ **Total API budget cap** (proposed 4.50 USD) and which Kling clips (S02, S04; S07 optional).
4. ☐ **Keyframe batch 1** (S01, S02, S03) — shown at full resolution *before any video*; pack/bag fidelity + face anchor check.
5. ☐ **Keyframe batch 2** (S04–S08), including the broken-wafer keyframe pair.
6. ☐ **Each Kling clip request** (separate go, 1 request, no retry) → review the raw clip.
7. ☐ **Rough cut (silent)** → ☐ **Final cut with text + sound** → ☐ **Compliance read** of all copy and caption.

---

## 8. Files in this step

- `references/` — official product photos, saved product pages/text, `reference_ledger.json`, identity anchors
- `storyboard/STORYBOARD_CONTACT_SHEET_MOCKUP.png` — local mockup from official photos + existing model reference (no AI, no spend)
- `prompts/keyframe_prompts_DRAFT.md` — draft keyframe + Kling prompts (unsent)
- `REEL_WORKLOG.md`, this plan; planning copies under `plans/gymbeam_hr/phase6/reel/`
