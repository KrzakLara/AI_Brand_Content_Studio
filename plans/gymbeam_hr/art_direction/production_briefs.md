# Production briefs: Phase 3 art-direction revision (FOR HUMAN REVIEW, nothing here is produced yet)

Plan hash: `ac58dcacad86fe4f90206ba9a594a9398dfbb9f579abd88672d223d9a20ab97a` (UNAPPROVED). Previous: `58d044c1255139ecee257c07eb16422e3b33ffb32fd3ab8acd0931a522ac7e40`.
Preview: `storyboard_contact_sheet.png` (local mockups, NOT generated images).

**Numbering:** the schema fixes post ids (`01` = carousel, `02` = hero, `03` = reel). In your numbering Post 01 = hero = plan id 02, Post 02 = carousel = plan id 01. Renumbering would be a schema change, so I did not do it.

**Reference:** the GymBeam Instagram carousel you linked was reviewed by you; I did not view, download or reproduce it. Only your description of its principles is used (premium product photography, natural texture, cinematic light, lifestyle, careful type, photo+video mix).

## 0. Shared look (all three posts)
- **Light:** one large soft key from the left at ~45 degrees, warm (about 3200-3800 K), weak fill, one narrow orange rim-light (#ff8c32) as the only saturated accent. Light falls off to deep shadow on the right.
- **Surfaces:** honed graphite concrete (#2d2a2b), rough cotton towel (#f2ede8 warm), glass and water, dark nylon. Not all-black: studio scenes alternate with warm daylight scenes.
- **Lens language:** 50-85 mm equivalent, f/2.8-f/4, camera at mid-height of the product, subtle film grain, no HDR look, no neon glow, no lens flares.
- **Type:** Inter Bold / Regular (licence still unverified), set by code only. **Logo:** official asset only (not yet retrieved, see `asset_manifest.yaml`). Generators never produce text, logos or packaging.
- **Negative prompt for every image/video model:** text, letters, logos, brand names, packaging, pouch, bottle labels, watermarks, faces, extra fingers, jewellery, tattoos, supplement claims, steam/fire/lightning, neon.

## 1. Preserving the authentic packaging (the practical plan)
Findings from pixel inspection of the selected packshot (1080x1080, sha256 `99543edf...`) and the other stored images:
1. The real pouch occupies about 493 x 897 px at x 273-765 (clean) plus ~45 px more at the right edge. **Four round webshop badges overlap that right strip along most of its height.** The pixels behind them exist in no stored image.
2. Alternatives checked: the "socks" bundle image (same pouch, but socks cover the right edge in the same strip, so the union still has a hole); the 250 g image is the OLD design; the mango pack is a different variant; the 1 kg back view is a different face. **No stored image gives a complete clean pouch.**
3. The existing `..._cutout.png` is NOT a real cut-out (it keeps background and badges). It must not be used for premium composites.

Plan, in order of preference:
- **A. Get a clean official asset** (badge-free front packshot, ideally >= 2000 px) from GymBeam (media kit / contact). Best for fidelity and resolution; costs nothing. **Needs your decision/contact.**
- **B. Until then, mask by code:** polygon mask of the pouch (x 273-765, rounded bottom corners by edge detection, verified by eye at 400%), badges excluded. The ~45 px right strip is NOT reconstructed (that would be redrawing the product). The right edge goes into low-key fall-off (lighting only: multiply by shadow) or out of the frame. Effect: in lit scenes the pouch looks ~8% narrower. This is a visible limitation and I flag it.
- **C. Close-ups (reel shot 5, carousel 5) stay <= 1.0x of the source.** Max pouch height ~897 px. No AI upscaling, ever, on the pouch or label text. Carousel slide 5 shows the label crops at 1:1 and sets the verified words again in sharp code type beside them (separate, labelled "Na pakiranju piše").
- Verified printed text only: "Creatine Monohydrate", "100% Pure micronised", "Unflavoured" (claims C1, C2). The webshop badges (Lab tested, IFS, Fast absorption, HPLC) are not used anywhere (they are web graphics; their compliance is still open).
- QA gate per composite: pixel-diff the pouch region against the source (must equal the source inside the mask except scale, translate and the shadow multiply); stored in the run folder with hashes.

## 2. POST 01 (plan id 02): Premium product hero, 1080x1350 PNG
**Concept:** "Samo bitno." (approved) as a studio portrait. **Method:** (1) image model generates an EMPTY background plate only (concrete plinth, graded warm backdrop, no object), 4 candidates; (2) you choose; (3) code composites the real masked pouch with a contact shadow (blurred multiply from the pouch's bottom silhouette), a faint concrete reflection and matched colour grade of the shadows only; (4) code sets headline, orange underline and logo; (5) QA.
**Plate prompt:** "Empty honed dark graphite concrete surface in the lower fifth, large soft warm light from the left, deep warm-black backdrop with a gentle gradient, one narrow orange rim-light glow on the far left background, eye-level camera, 85 mm, shallow depth of field, fine film grain, photorealistic commercial product photography, no objects, no text."
**Layout:** pouch height <= 780-800 px, right of centre, base at 78% height; headline top left (Inter Bold, 118 px, "bitno" underlined orange); logo bottom left; bottom 150 px clear. Caption (Lara's): "Bez buke, bez ukrasa." CTA: "Pogledajte na linku u opisu profila."

## 3. POST 02 (plan id 01): Mixed-media carousel "Kreatin izbliza" (4 photos + 2 videos)
Educational objective: understand the product up close (what the powder looks like, how it mixes, what the pack actually prints). Only verified pack text is claimed. No dosage, benefit or solubility statements.

| # | Type | Role | On-frame copy (HR) | Source / production method |
|---|---|---|---|---|
| 1 | PHOTO | Opening | "Kreatin izbliza." / "Šest kadrova, zrno po zrno." | Background plate (AI) + real pouch composite + sparse powder grains (AI plate or macro layer) + code type, logo |
| 2 | VIDEO 3.5 s | Powder in motion | "Prah u pokretu." / "Zrno po zrno." | Approved key frame (AI image) animated by image-to-video; NO pack, no text in the footage; text by code |
| 3 | PHOTO | Routine | "Prije treninga." / "Shaker, voda, ručnik." | AI photoreal key frame: faceless hands, plain unbranded clear shaker, bench, cotton towel; no pack; code type |
| 4 | VIDEO 3.5 s | Water + mixing | "Voda i prah." / "Miješanje u pokretu." | AI key frame then image-to-video: cloudy swirl that does NOT clear instantly; no pack; no solubility claim |
| 5 | PHOTO | Verified label | "Što piše na pakiranju" / callouts C1, C2 | Real label crops (`label_name`, `label_purity`) at 1:1 on a plate + code type. Fully deterministic |
| 6 | PHOTO | Closing + CTA | "Pogledajte izbliza." / "Više na linku u opisu profila." | Plate (towel, glass in soft focus, concrete) + real pouch composite + logo + code type |

Caption: "Kreatin izbliza: prah, voda i ono što piše na pakiranju. 🧡 Prelistajte do kraja." CTA: "Spremite objavu, a više pogledajte na linku u opisu profila."
**Key-frame prompts (add the shared negative prompt):**
- 2: "Macro photograph of fine white powder falling from a dark spatula blade into a clear glass, warm side light from the left with a thin orange rim light, shallow depth of field, dark warm background, photorealistic, no text."
- 3: "Faceless close shot of two bare hands (no rings) holding a plain clear plastic shaker with no printing above a wooden gym bench, rough cotton towel, soft blurred weights, warm window light from the left, photorealistic, 85 mm."
- 4: "Macro of a glass of water with white powder swirling and clouding, natural uneven mixing, dark warm background, side light, photorealistic."
- Motion prompts: "slow macro push-in, natural powder physics, no camera shake, 3.5 seconds." Reject any clip with warped glass, impossible physics, text, or a product-like object.

## 4. POST 03 (plan id 03): Cinematic reel "Klik prije izlaska", 14 s, 1080x1920
Reliable path: photoreal key frames -> your selection -> selective animation (2.5D parallax or short image-to-video for shots 1-3 only) -> code-composited pouch for shots 4-6 -> FFmpeg edit with sound-driven hard cuts. Any generated shot that distorts anything product-like is dropped.

| Shot | Time | Visual | Camera | Sound / cut | Copy (Lara's, unchanged) | Product |
|---|---|---|---|---|---|---|
| 1 | 1.5 s | Dark hallway, warm window rim on black nylon bag; faceless hands zip it, macro | short fast dolly in | sharp zip on the first pulse; hard cut on the sound | "Sve je na svom mjestu." | none |
| 2 | 1.5 s | Faceless silhouette behind milky glass, warm light rectangle on concrete wall | static | steps + door handle on the pulse | none | none |
| 3 | 1.5 s | Macro: hands tie a shoelace on dark concrete floor | low, slight left drift | lace pull on the pulse, music rises | none | none |
| 4 | 3 s | Concrete shelf in shadow; orange rim-light sweeps across and reveals the real pouch (code composite) | gentle 10-degree orbit simulated by parallax | music surges, short light-sweep sound | none | real pack |
| 5 | 4 s | Slow clean close-up of the pouch on a warm concrete shelf | slow push-in, <= 1.0x source, right edge in shadow | music drops to a quiet pulse | none | real pack |
| 6 | 2.5 s | End card: pouch lower third, official logo above, orange line | static | last musical tone, then silence | "Spremno za izlazak." | real pack |

Caption (Lara's): "Patent, kvaka, vezice. 🎧 Tri sitna zvuka prije izlaska. A koji je vaš mali ritual prije treninga?" Audio: only licensed audio with recorded licence data (none selected). Hands: no rings, tattoos, logos.

## 5. Known quality risks and mitigations
| Risk | Mitigation |
|---|---|
| Pouch looks pasted on | AI plates only (no pouch); code contact shadow + reflection; matched light direction (key from the left); QA at 100% |
| Pouch ~8% narrower and edge in shadow (badge-hidden strip) | Prefer a clean official asset (plan A); else low-key fall-off or frame crop |
| Packshot resolution (~897 px) limits close-ups and large hero | Hero <= 800 px; reel shot 5 push-in <= 1.0x; request higher-res asset; no AI upscale |
| AI plate looks "generic AI fitness poster" | Real material references, restrained palette, human selection of 1 of 4 plates, film-grain, no neon, no clutter |
| Video model hallucinates text, packs or logos | Videos only for no-product shots; negative prompt; reject on first artefact; no product shot is animated by a model |
| Powder/water physics look fake or imply instant dissolving | Approve key frame first; 3.5 s max; no solubility copy; reject clean-clear results |
| Faceless hands uncanny (fingers) | Generate 4 candidates, human pick; ring-free; silhouette fallback for shots 1 and 3 |
| Unverified claims creep in | Only C1/C2 pack-text callouts; health claims deferred; validator still applies; Croatian reviewed by a native speaker |
| Logo, font, audio rights unverified | Manifest fields stay PENDING until you approve; no use before |

## 6. Estimated paid generation budget for Phase 4 (NOT spent, NOT authorised)
No image or video model has been chosen and no prices are verified in this repo, so these are planning ranges with assumptions, to be replaced by verified prices before you approve a cap.
| Item | Quantity | Assumed unit | Range |
|---|---|---|---|
| Hero plate candidates | 4 + 4 re-rolls | 0.04-0.20 USD / image | 0.3-1.6 |
| Carousel key frames (photos 1, 3, 6 plates; video frames 2, 4) | 5 x 4 candidates | 0.04-0.20 | 0.8-4 |
| Image-to-video clips (carousel 2, 4; reel 1-3) | 5 clips x 2 attempts, 3-4 s | 0.3-1.5 USD / clip | 3-15 |
| Reel key frames (shots 1-6) | 6 x 3 candidates | 0.04-0.20 | 0.7-3.6 |
| **Total** | | | **about 5-25 USD**, recommended cap **30 USD**, per-model hard cap and request cap set in config like Phase 2 |
Suggested order: hero plate first (cheapest, unblocks the first premium PNG), then videos only after their key frames are approved.
Decisions needed from you: (1) contact GymBeam for a clean packshot, or accept plan B; (2) the image model and the video model (separate choice, verified prices); (3) the budget cap; (4) the 3 open questions already in the plan (logo, audio, font licence).
