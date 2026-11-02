# Colla Pink carousel (Carousel Post 2): production package (UNAPPROVED; plan hash 970975125494 unchanged, approval NONE; no tag)

Files (git-ignored, derived from brand-owned images, not for publication): `runs/colla-pink/carousel_final/`
| # | File | Type | Status |
|---|---|---|---|
| 1 | slide1_cover_FROZEN_1080x1350.png (sha256 b925b8b3...) | PHOTO | approved by Lara, frozen, read-only |
| 2 | slide2_sto_je_unutra_1080x1350.png | PHOTO | produced |
| 3 | slide3_priprema_VIDEO_SLOT_KEYFRAME_ONLY_1080x1350.png | **VIDEO SLOT: keyframe only, NOT a video** | open |
| 4 | slide4_kako_pripremiti_1080x1350.png | PHOTO | produced |
| 5 | slide5_mali_ritual_VIDEO_SLOT_KEYFRAME_ONLY_1080x1350.png | **VIDEO SLOT: keyframe only, NOT a video** | open |
| 6 | slide6_odaberi_svoj_okus_FINAL.png | PHOTO | corrected: approved design + real jar (see slide6_before_after_REVIEW.png) |
Review aids (not deliverables): `carousel_contact_sheet_REVIEW.png`, `carousel_feed_size_strip_REVIEW.png`, `carousel/identity_compare.png`.

## Croatian caption (draft for Lara's wording)
Vaš ružičasti ritual uz Colla Pink. 💗 Što je unutra, kako se priprema i koji okus odabrati: prelistajte do kraja. Spremite objavu, a više pogledajte na linku u opisu profila.
Osoba na fotografijama je fiktivna (generirana umjetnom inteligencijom). #gymbeamhr #gbfit

## Objective and rationale
Inform and be saved: what is in a scoop (verified page quantities), how to prepare it (1 scoop = 8 g in 200-300 ml water), which flavours exist; baby-pink beauty-and-fitness sub-campaign in the spirit of the brand's pink CreaGlow posts. Claims: only dated page facts as separate callouts ("Na stranici proizvoda piše", source gymbeam.hr, 28. 10. 2026); no benefit, price or rating wording.

## Sources and product references
Official page https://gymbeam.hr/colla-pinkbeastpink.html (stored, sha256 79b0bb52...); five official packshots (sha256 in `plans/gymbeam_hr/phase5/colla_pink_assets.yaml`); evidence `research/imports/colla_pink_evidence.yaml`; reference direction from Lara's screenshots in `runs/colla-pink/instagram_pink/` and `approved_visual_direction/` (inspiration only; the influencer is neither reproduced nor implied). Fonts Montserrat (SIL OFL), licence stored in `runs/colla-pink/font/`.

## Production method
Scene, props, light, fruit and the woman: `gpt-image-2.5-sunburst`, xhigh, 1600x2000, mask edits around fixed real jars (slides 2, 4, 6); slides 3 and 5 are plain generations (slide 5 conditioned on TWO real images: the approved cover and its raw render, as supported reference images). Real jar pixels are placed back by code: edge-cleaned matte, luminance-only bounded relight, 6% edge shading, fruit in front of the jars restored from the render only in the bottom 8% of each jar (never over printed text). All text is deterministic Montserrat. Jars are source-authentic but relit/downscaled, not pixel-identical; the printed label text is the real packshot text.

## Costs (actual, one ledger, audit log 11 requests)
Slide 2 0.140525, slide 4 0.14051, slide 6 0.14089, slide 3 keyframe 0.140335, slide 5 keyframe 0.152316 (two input images) = **0.714 USD this session (0.714411)**; Phase 5 total 0.997086 of 3.00, **remaining 2.002914**; whole ledger 1.279031 USD (401, 429 and the hero requests included). No retries. Video: 0 USD.

## Video status (slides 3 and 5)
No video provider is usable: `.env` has no Google key (GEMINI_API_KEY / GOOGLE_API_KEY not set), Google billing is separate and not activated, and no separate video budget has been approved. The OpenAI image model does not make video, and FFmpeg is not installed, so even a deterministic pan on the keyframe was not produced. Keyframes were generated so the clips can be made from them later: Gemini Omni 1.1 Flash (about 0.10 USD/s at 720p, about 0.36 USD per 3.5 s clip; aspect ratios unverified) needs your explicit cap and key. Slide 5 should then use the keyframe plus the cover as image references; identity must be re-checked on the clip.

## QA (inspected at full size and at 390 px feed size; machine metrics are NOT a pass)
- Slide 2: readable at feed size (panel behind the numbers); the jar is small and pale; the label is readable at full size only; the grape is a green grape; no health claim.
- Slide 4: steps readable; the jar is slightly flat/pale next to the glass; water is clear (no invented colour); strawberries + lemons.
- Slide 6: five real jars, same dusty rose, each flavour word legible at full size (strawberry lemonade, grape, mango orange, raspberry, wild berries) with its own fruit; jars sit slightly "in front of" the fruit and look flatter than the fruit; a few tiny mismatches where fruit restored over the jar base (not over text).
- Slide 5 keyframe: identity compared visually with the cover (`identity_compare.png`): same hair, skin tone, face shape, smile and outfit; the eyes are closed in the keyframe, so identity of the eyes is not comparable; the likeness is close but NOT guaranteed, no pixel-level check. Headline overlaps her hair slightly at "RITUAL."
- Slide 3 keyframe: no jar, no packaging, glass unmarked; the "video" shows a frozen pour.
Known defects: jars look flatter than the generated scene (flat packshot), slide 6 jars are small, a faint seam can appear at jar edges at 300%, no annotated 300% review was made for slides 2-6 (only slide 1 has one), the G logo is not used, Croatian not proofread by a native speaker.

Hero V5 unchanged (sha256 f05d1f39...).

## Slide 6 correction (Lara's approved design, zero cost)
Base: `runs/colla-pink/SLIDE6_APPROVED_PINK_FRUIT_DESIGN_1092x1440.png` (her approved AI design: one central jar, ice, strawberries, lemons, five fruit circles). Only the AI-drawn jar was replaced by the real Strawberry Lemonade packshot (sha256 1fa5e11d...; clean matte, luminance-only relight from the AI jar's own shading, soft contact shadow); strawberry half and two ice cubes that stood in front of the jar were restored from the design. The subtitle was replaced by "PET OKUSA. JEDAN RITUAL." (the equivalence claim "Ista snaga, drugo voće" is not verified). Scaled 0.989 and cropped 30 px top / 44 px bottom to 1080x1350 (headline and flavour labels intact). Script `plans/gymbeam_hr/phase5/slide6_final.py`; no API call; ledger unchanged (11 requests, 1.279031 USD).
Remaining Slide 6 defects: the jar is paler and greyer than the glossy AI scene (real packshot colour, dry: the AI jar had water droplets, none were added to the packaging); a thin grey sliver and small notch where the restored strawberry meets the jar; the wild-berries circle contains a strawberry besides raspberries, blueberries and blackberries (baked into the approved design: not changed); flavour labels and headline are the design's own AI-rendered text (legible, spelled correctly: JAGODA – LIMUNADA, GROŽDE, MANGO – NARANČA, MALINA, ŠUMSKO VOĆE).

## Slide 6 final colour correction (zero cost)
Only the jar's pink label region changed (`plans/gymbeam_hr/phase5/slide6_color_fix.py`): one per-channel gain (R 1.048, G 1.014, B 1.019) moves the label median from (186,148,154) to the official packshot's plain-label colour (195,150,157); shading is preserved. Result in the final: (193,146,154), H350 S0.24 V0.76 against the packshot's H351 S0.23 V0.76 (mango orange and strawberry lemonade packshots have identical label colour). Mask = real jar footprint x pink-chroma weight; white print, lid, base, strawberry, ice and lemon are excluded. Verified: 0 changed pixels outside the mask (max difference 0). Previous version kept as `slide6_odaberi_svoj_okus_FINAL_before_color.png`. Review: `slide6_color_before_after_vs_packshot_REVIEW.png`, `slide6_color_full_before_after_REVIEW.png`, report `slide6_color_fix_report.json`. Finding: hue and saturation were already within 1 degree / 0.02 of the packshot; the grey impression came from the label being about 5% darker and 4% less red than the packshot (relighting gain) plus the vivid AI jar it replaced.

## Slide 6 approved and frozen (Lara, 2026-10-28)
Promoted `slide6_HARMONIZED_CANDIDATE.png` to `slide6_odaberi_svoj_okus_FINAL.png` (read-only). Backup of the previous final: `slide6_BACKUP_pre_harmonization_FINAL.png`; the pre-colour-fix version is kept as `slide6_odaberi_svoj_okus_FINAL_before_color.png`. Hashes and statuses of all six slides: `carousel_status.yaml`. Plan approval remains NONE. Next session: slides 3 and 5 become real videos from their keyframes and the model references.
