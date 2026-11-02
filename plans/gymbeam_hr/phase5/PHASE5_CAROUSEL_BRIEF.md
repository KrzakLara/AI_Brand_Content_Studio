# Phase 5: Carousel Post 2 = BeastPink Colla Pink (baby-pink beauty and fitness sub-campaign) - FOR APPROVAL, nothing produced, no paid call

Plan hash **`970975125494d10dda267d86d6ebab7f45ebb4983ae2dfb0444e0304afa01a99`**, approval **NONE**, no tag. Previous: `a923c3229e03...` (Hero V5 selection state). Hero V5 PNG unchanged (sha256 `f05d1f39...`), hero headline unchanged (human-authored), API ledger unchanged (4 requests, 0.281945 USD).
This brief supersedes `colla_pink_brief.md`: the "One jar, five flavours" story is no longer the main concept (it survives only as slide 6).

## 1. What changed in the plan (via `studio plan edit`, 43 edits, `colla_pink_edits.yaml`)
- Carousel (plan id 01, Lara's Post 2) is now **Colla Pink** with a new `carousel.product` block (parent SKU 29715, five flavour packshots with hashes, evidence ids). Hero and reel stay creatine (focal product SKU 3885); only their two "distinct from" sentences changed.
- Six new slides replace the creatine slides; the six creatine pack/page claims were removed from the active claims (history keeps them) and six verified page facts were added; benefit wording is a deferred claim.
- People block: `fictional_model` (new value): a fictional AI-generated woman, never a real or recognisable person.
- Tool extensions needed (small, tested in `tests/test_phase5.py`): edit ops `add_item` (claim / deferred claim) and `set_block` for `product` and `basis`; claim type `page_fact`; a dated page fact may carry its quantity (all other quantity wording stays blocked); the dossier loads `research/imports/colla_pink_evidence.yaml` through the brief (`extra_evidence_paths`). The creatine validations are unchanged.

## 2. Focused research (about 40 minutes), evidence
- **Source:** `https://gymbeam.hr/colla-pinkbeastpink.html`, fetched 2026-10-28, stored with sha256 `79b0bb52...` in `runs/colla-pink/source/`; every quoted page sentence was re-found verbatim in the stored page. Evidence file: `research/imports/colla_pink_evidence.yaml`.
- **Pink campaign fits the brand (existing research, no new scraping):** `E-e73f15ab` (manual): the @gymbeamhr CreaGlow cover post is a pink layout in a decorative serif/script display face with the creator holding the tub; `E-87ecea41` (verified): the brand published a Pink Collagen video on 2026-10-07; the 2026-10-07 caption also uses #pinkoctober. **Your screenshots of the CreaGlow campaign were not visible to me**: they are your human attestation, not machine evidence, and no reference image is reproduced. The creator in that campaign is a real influencer: the carousel never recreates her or implies her endorsement.
- **Packshots:** the five official per-flavour packshots (1200x1200, white background, identical jar geometry) show one dusty-rose jar; only the printed flavour word changes. The label prints **NET WT.: 240 g** although the file names say 340 g. The older white-label design and the HOT SALE graphic in the gallery are excluded.
- **Prices and ratings are not used in any asset.**

## 3. Revised six-slide storyboard and exact Croatian copy
Palette: jar dusty rose (#b98f94, #d6adb3, measured), baby pink #f4c7d0, blush white #fbf3f2, burgundy type #6e1f35. Type is set by code; the jar is always the real packshot, relit and edge-matted like the hero pouch (never redrawn or recoloured); no generated text anywhere.

| # | Type | Packshot | On-frame copy (HR) | Scene |
|---|---|---|---|---|
| 1 | PHOTO cover | jagoda - limunada | **Vaš ružičasti ritual.** / Colla Pink: sve što treba znati u šest kadrova. | Soft pink studio, fictional model in white activewear holding the real jar, fingers below the label, strong editorial headline top third |
| 2 | PHOTO what's inside | grožđe | **Što je unutra?** / Sastojci i količine sa službene stranice. + 3 callouts C1-C3 | Infographic on blush white, real jar centre with green grapes, three burgundy callouts joined by thin lines |
| 3 | VIDEO 3.5 s preparation | none (no jar in footage) | **Priprema.** / Prah, voda, miješanje. | Macro: powder into clear water, swirl while mixing, light from the left through glass; no invented colour |
| 4 | PHOTO how to use | mango - naranča | **Kako se priprema?** / Odmjerite prah, dolijte vodu i promiješajte. + callouts C4, C5 | Baby-pink board, three pictogram steps, real jar with sliced mango and orange |
| 5 | VIDEO 3.5 s pink ritual | malina (code overlay, last 1 s only) | **Mali ritual.** / Kad Vam odgovara. + callout C6 | The same fictional model (same face, outfit, room, light) stirs a drink and raises the glass |
| 6 | PHOTO choose your flavour | all five | **Odaberite svoj okus.** / Jagoda - limunada, grožđe, mango - naranča, malina i šumsko voće. | Five real jars in a row, same pink design, each with its own fruit |
Caption: "Vaš ružičasti ritual uz Colla Pink. 💗 Što je unutra, kako se priprema i koji okus odabrati: prelistajte do kraja." CTA (unchanged plan text): "Spremite objavu, a više pogledajte na linku u opisu profila." Hashtags: #gymbeamhr #gbfit (existing brand tags).
Fruit rules: strawberries + lemons, green grapes, mango + oranges, raspberries, mixed berries, each only with its own jar except slide 6. Alt texts are in the plan (`carousel.slide*.alt`).

## 4. Verified claims (all `page_fact`, rendered as separate code-set callouts, dated 2026-10-28, source = stored official page)
| id | Callout text | Evidence |
|---|---|---|
| C1 | Na stranici proizvoda piše: u 8 g (1 mjerica): hidrolizirani peptidi goveđeg kolagena 6300 mg, ekstrakt sjemenki grožđa 20:1 400 mg, hijaluronska kiselina 40 mg. | E-colla-nutrition |
| C2 | Na stranici proizvoda piše: u 8 g: cink 10 mg, selen 89 μg, vitamin C 500 mg. | E-colla-nutrition |
| C3 | Na stranici proizvoda piše: u 8 g: niacin 32 mg, vitamin B2 2,8 mg, vitamin A 800 μg, biotin 50 μg. | E-colla-nutrition |
| C4 | Na stranici proizvoda piše: preporučena dnevna doza je 1 mjerica (8 g), pomiješana s 200 do 300 ml vode. | E-colla-dosage |
| C5 | Na stranici proizvoda piše: nemojte prekoračiti preporučeni dnevni unos; proizvod nije zamjena za raznoliku i uravnoteženu prehranu. | E-colla-warning |
| C6 | Na stranici proizvoda piše: napitak možete konzumirati u bilo koje doba dana. | E-colla-dosage |
**Deferred, not used (compliance review with conditions of use):** all statements on hair, nails, skin, collagen formation and skin hydration, including the page's authorised-wording sentences and the meta-analysis (`E-colla-health-wording`).
**Page inconsistency (open):** the spec table says "recommended daily dose 2" and "30 days per pack", the text says 1 scoop of 8 g and "maximum 18 g". Only "1 mjerica (8 g) in 200-300 ml" (stated twice consistently) is used. Sucralose is listed as a sweetener; no "no sweetener" statement is made.
**Drink colour is not verified**: videos show powder and water only, a neutral clear-to-cloudy liquid. If your screenshots show a tinted drink, tell me; I cannot see them.

## 5. Costs (estimates, nothing spent)
**Stills (OpenAI `gpt-image-2.5-sunburst`, xhigh, 1600x2000 mask edit; measured 0.141 USD each, a second input image adds about 0.01):**
| Item | Attempts | Estimate |
|---|---|---|
| Fictional-model reference (one approved identity, reused as input) | 2 | 0.30 |
| Slide 1 (model + jar, hardest: fingers vs label) | 3 | 0.45 |
| Slide 2 | 2 | 0.30 |
| Slide 4 | 2 | 0.30 |
| Slide 6 | 3 | 0.45 |
| Key frames for videos (slide 3: 2; slide 5: 3) | 5 | 0.75 |
| **Total** | 17 | **about 2.55 USD**; allowed cap 3.00 USD (about 0.45 margin, about 3 extra attempts) |
The existing guard assumes a 2.12 USD worst case for the very first request; it needs the new cap and the request cap (currently 4/4) reset by you.
**Video (Gemini Omni 1.1 Flash, model id `gemini-omni-1.1-flash`, checked on Google's pricing page 2026-10-28):** generally available on the **paid tier only** (no free tier); input 1.50 USD per 1M tokens, video output 17.50 USD per 1M tokens, which the page states as about **0.10 USD per second at 720p** (5,792 tokens per second). Per 3.5 s clip about **0.36 USD**; two clips with 2 attempts each about **1.4 USD**, with 3 attempts each about 2.1 USD. Not stated on the page: per-resolution prices above 720p, whether audio is included, and whether 4:5 is supported (so a 720p vertical or square crop may be needed). Google billing is separate from the OpenAI credits; the repository `.env` has no Google key, so access and balance are **unverified**. No video request without your separate cap. I recommend a Google cap of 2.00 USD for four clips.

## 6. Risks
1. **Face consistency** across two photos and two videos is not guaranteed: one approved reference identity is reused as input; videos animate approved key frames; drifting clips are rejected. May cost extra attempts.
2. **Jar in hands (slide 1)**: the real jar is a flat packshot composited over generated hands; fingers must not cover the label. Fallback: the model rests her hand beside the jar or holds it low.
3. **Pale jar on pale scenes**: slides 2 and 6 use deeper pink/burgundy contrast so the dusty-rose jar does not vanish.
4. **White-background cut-outs**: soft lid and highlight edges need the same matting check at 6x as the hero.
5. **Video physics** (powder, water) can look unreal or tint the liquid: reject on first artefact.
6. Any generated text, label, jar or logo in a plate, or a recognisable person: reject.

## 7. Dependencies and open decisions
1. Approve or amend the storyboard and the Croatian copy above.
2. Typeface: your CreaGlow reference uses a decorative serif/script display face. Proposal: a licensed open serif (for example Playfair Display, SIL OFL; licence to be recorded) for headlines and Inter for small text. Needs your choice.
3. Stills cap (3.00 USD) and request cap; Google video cap and an API key with billing (separate); the 4:5 / 720p question.
4. Logo: the BeastPink mark is printed on the jar; no separate logo asset is overlaid.
5. Native-speaker Croatian check; legal review of the deferred benefit wording and of public use of GymBeam photographs.
6. Fictional-model disclosure wording for the caption or profile (suggested: "model generiran umjetnom inteligencijom").
