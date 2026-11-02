# UPDATE Phase 7F (2026-11-01): slide 5 is now v4 — see `ZINC_CLAIM_432_2012_HR.md`

The official Croatian text of Reg. 432/2012 was read (EU Publications Office copy; EUR-Lex itself blocks automated access) and lists three separate zinc claims (kose / noktiju / kože). Slide 5 **v4** now reads **"Cink doprinosi održavanju normalne kože i kose te normalnih noktiju."** (v3 text "…normalne kože, kose i noktiju." is superseded and kept for audit). The sections below describe v3 (Phase 7C) and are historical; open legal items 1 (Croatian wording) is now partly answered by `ZINC_CLAIM_432_2012_HR.md`, the others remain open. This is a supported zinc statement, **not** a clearance of the advertisement.

---

# Slide 5 claim review — decision applied in Phase 7C (2026-10-29)

**Status: the unsupported line has been replaced in `slide5_…_FINAL_v3` (local rebuild, no new footage). Remaining legal review is listed in section 6. This is a working check, not legal advice.**

## 1. The change
| | Text |
|---|---|
| Kept | NAPITAK ZA LJEPOTU · Ljepota počinje iznutra. |
| Removed (v2, unsupported) | Njeguj svoju kožu, kosu i nokte. |
| Added (v3, chosen by Lara in the Phase 7C instruction) | **Cink doprinosi održavanju normalne kože, kose i noktiju.** (two lines, 36 px bold, same colour and panel style) |

The v2 video is preserved unchanged (`runs/colla-pink/slide5_video/…FINAL_v2…`, copy in `phases/05_carousel_post2/slide5_video/superseded_v2/`).

## 2. Why the old line failed
An imperative to "care for" skin, hair and nails on a product slide reads as an effect of the product. Health claims may only use authorised wording (Reg. (EC) 1924/2006 Art. 10(1)). The page's collagen (6300 mg), hyaluronic acid (40 mg) and grape seed extract (400 mg) have no authorised claim for skin, hair or nails, and the product is the "Colla" collagen drink, so viewers attribute the effect to collagen.

## 3. What supports the new line
Product (official page gymbeam.hr/colla-pinkbeastpink.html, read 2026-10-28; `research/imports/colla_pink_evidence.yaml` `E-colla-nutrition`): **zinc 10 mg per 8 g serving = 100 % of the nutrient reference value**.

Regulation text, read in this phase (2026-10-29):
- **Reg. (EU) 432/2012, Annex, zinc rows** — authorised wordings "Zinc contributes to the maintenance of normal **hair**", "…normal **nails**", "…normal **skin**". Condition of use for every zinc row: the claim may be used only for food that is at least a **source of zinc** (≥ 15 % of the reference value per portion; 100 % here, so met).
- **Reg. (EC) 1924/2006 Art. 10(1)–(3)** — claims need authorisation; Art. 10(2) requires accompanying information; Art. 10(3) allows general, non-specific benefit statements only together with a specific authorised claim.
- **How it was read:** `eur-lex.europa.eu` blocks automated access (HTTP 202 challenge page, empty content), so the text was read from the **UK government's `legislation.gov.uk` copy of the EU regulation (retained EU law)**, whose zinc rows and Art. 10 are the same text. The EU Register of nutrition and health claims was **not** consulted and amendments made after the 2020 retention were **not** checked. Lara's cited source `eur-lex.europa.eu/eli/reg/2012/432` should be opened by a human to confirm.

## 4. Full marketing context (Art. 10(2) accompanying information)
| Required | Where it is covered | Status |
|---|---|---|
| Statement on the importance of a varied, balanced diet and healthy lifestyle | **Not on the slides.** Product page: "Ovaj proizvod nije zamjena za raznoliku i uravnoteženu prehranu i zdrav način života." | **Added to the Post 2 caption in 7C** (proposal, needs approval) |
| Quantity and pattern of consumption needed for the effect | Slide 4: 1 mjerica (8 g) praha, 200–300 ml vode; page: recommended daily dose 1 scoop | on slide 4; repeated in the caption |
| Statement for people who should avoid the food | Page: "Proizvod nije namijenjen djeci, trudnicama i dojiljama." | caption |
| Warning against excessive intake | Page: "Nemojte prekoračiti preporučeni dnevni unos." | caption |
| Art. 10(3) general benefit statements ("NAPITAK ZA LJEPOTU", "Ljepota počinje iznutra.") | now sit on the same slide as the specific authorised zinc claim | acceptable in principle; legal review recommended |

Caption wording added (taken from the product page, not invented): *"Dodatak prehrani nije zamjena za raznoliku i uravnoteženu prehranu i zdrav način života. Preporučena dnevna doza: 1 mjerica (8 g) u 200–300 ml vode; ne prekoračujte preporučeni dnevni unos. Nije namijenjeno djeci, trudnicama i dojiljama."* A caption is text the viewer may not open; if a regulator or lawyer wants the information on the creative itself, it would have to go on a slide.

## 5. Technical QA of v3 (`phases/05_carousel_post2/slide5_video/slide5_v3_QA.json`)
121 frames, 1080 × 1350, 24 fps, 5.04 s. The new claim text is burgundy on every frame (max mean error 3.5/255); the headline likewise (1.1). Layer pixels above y = 1130 are identical to v2's layer; the rest of the picture differs from v2 only by H.264 re-encode noise (mean abs diff 0.27/255). No Kling footage was regenerated; woman, face, hair, glass, colours and animation come from the same `kling_raw_v2.mp4`. Rebuild is deterministic (byte-identical on repeat).

## 6. Remaining legal review (human)
1. Compare the Croatian wording with the **official Croatian-language text of Reg. 432/2012**; ours is a direct rendering of the English wording and the official Croatian phrase may differ slightly. Authorised wording may be used only in the same meaning, but a lawyer should confirm.
2. Confirm the Art. 10(2) caption text above, or whether the information must also appear on the creative.
3. Assess the overall impression: the claim names zinc, but the product is promoted as a collagen "beauty" drink; a reviewer may still read the post as implying collagen benefits. Consider whether "NAPITAK ZA LJEPOTU / Ljepota počinje iznutra." should stay.
4. Check the EU Register for any change to the zinc claims after the retained text, and any national supplement-marketing rules.
5. Native-speaker proofreading of all Croatian copy.
