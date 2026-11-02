# Final scope revision (Phase 7F) — from the creatine-only brief to the three-product demonstration

**The original brief is preserved unchanged** as `ai_recipe/repo/briefs/gymbeam_hr.yaml` (SHA-256 `e4e6572ec2c39227c57fbce3b60e980246b0e9449cfb998bdc99d3e147bb32d2`; also `phases/02_plan/gymbeam_hr_canonical_brief.yaml`). It is a historical record and is not edited. This document sits beside it; the machine-readable form is `FINAL_SCOPE_REVISION_7F.yaml`. Decisions below were **not** part of the initial brief and are dated where the project records them; history is not rewritten.

## 1. How the scope evolved
| When | What the project records |
|---|---|
| 2026-10-27/28, initial brief | `campaign_goal`: "Instagram mini-campaign of three posts (educational carousel, product hero, cinematic reel) for 100% Kreatin Monohidrat"; the focal product confirmed by the human on 2026-10-28 is creatine (SKU 3885). |
| 2026-10-28, Phase 5 (recorded inside the brief itself) | "Lara chose Colla Pink (BeastPink, parent SKU 29715) as the carousel product; hero and reel focal product stays creatine SKU 3885." The plan (hash `970975125494…`) therefore contains: Colla Pink carousel, creatine hero, creatine reel "Klik prije izlaska". |
| 2026-10-29, Phase 6 | The creatine reel was never produced. Lara directed a new lifestyle Reel for the GymBeam 32% Protein Wafer (with the Urban Duffle Bag) instead; documented in R9 as a human decision, with the original plan preserved. |
| 2026-11-01, Phase 7F | Editing style of the Reel chosen deliberately (rough-cut, TikTok/UGC-inspired); Reel V8 selected; final corrections to the carousel. |

## 2. Final scope (as delivered)
```yaml
final_scope:
  - post: 1
    product: GymBeam 100% Creatine Monohydrate (SKU 3885)
    format: static hero image, 4:5
    direction: premium advertising of the product
  - post: 2
    product: BeastPink Colla Pink
    format: educational six-slide carousel (4 images + 2 videos), 4:5
    direction: informative lifestyle content (what is inside, how to prepare, which flavour)
  - post: 3
    product: GymBeam 32% Protein Wafer (+ Urban Duffle Bag Black)
    format: lifestyle Reel 9:16, 8.83 s
    direction: organic, rough-cut, TikTok/UGC-inspired montage
```
Why three products: three categories (creatine, collagen drink, snack), three formats and three moods demonstrate that the same AI procedure (research → plan → generation → QA) applies to different products and creative approaches. All three remain a speculative portfolio demonstration, not an official GymBeam/BeastPink collaboration.

## 3. The original constraints and how they apply to the final scope
The original `campaign_constraints` are kept as written; this section states how each one was read for the final scope. It does **not** loosen the intent of any rule.

**A. "No quantity (grams, servings, doses) because the selected packshot does not print a size."** The rule was written for the creatine hero, whose selected packshot prints no size. Its purpose is to forbid **invented or unsupported numerical claims**. It still holds for Post 1 (no quantity anywhere). For Post 2, quantities that are **printed on the authentic packaging and confirmed in the official product documentation** may be displayed, each sourced and dated (product page gymbeam.hr/colla-pinkbeastpink.html read 2026-10-28; `research/imports/colla_pink_evidence.yaml`; jar label "NET WT.: 240 g"): the ingredient amounts on slide 2 and the serving on slide 4 (1 mjerica (8 g), 200–300 ml). This does **not** permit any other or new quantity. Post 3 puts no quantity claim in its text.

**B. "Show the product only as the selected original packshot or unaltered crops of it; never redraw or generate packaging."** Post 1 keeps the real pouch pixels from an official photograph (edge-matted and relit, not pixel-identical) and Post 2 keeps the real packshot jars placed by code (flavour word and label verified 1:1; on the cover a masked image edit plus deterministic jar-edge retouch), so the rule was kept there. **Post 3 deviates, and this is a documented production deviation:** the wafer pack and the bag appear as **AI-rendered packaging in moving video scenes**, because the official photographs cannot provide the required moving interaction (hand, pack, bag, car, gym). This deviation is **not evidence that the generated packaging is accurate.** Reference validation and visual QA were kept and the limitations are stated: AI renderings from 700 px references (`phases/06_reel_post3/references/`, `review_package/PRODUCT_REFERENCE_LEDGER.md`), soft wrapper print in motion, chain-like bag hardware in the car shot, an unconfirmed back handle in the new bag shot, rejected earlier versions V4–V7 (`phases/06_reel_post3/versions/`, `qa/`). No unwrapped or broken wafer is shown because no source photo supports a generated one.

**C. Health or performance claims.** Unchanged: no claim without a claim-specific review. Slide 5 uses the three separately authorised zinc claims (official Croatian text of Reg. 432/2012, `compliance/ZINC_CLAIM_432_2012_HR.md`); this is a supported statement, **not** a clearance of the advertisement.

## 4. Final creative direction (deliberate choices, made after the initial brief)
- **Creatine:** premium product advertising — the pack alone, no additions (static hero).
- **Colla Pink:** educational lifestyle carousel — saveable, informative, light-pink world.
- **Wafer Reel:** organic, rough-cut, TikTok/UGC-inspired montage, chosen for a more spontaneous, authentic impression than a classic produced advertisement. No claim is made that this is currently the most popular format.

## 5. Status
**A. Author-reviewed and accepted for the Sekvenca private take-home demonstration, including visual content, captions and Reel audio.** (confirmed in writing by the author on 2026-11-01). **B. Portfolio demonstration only; not approved for public commercial advertising.** Not authorized for public commercial advertising without additional rights and compliance review. Consistent with R9 (`CONTENT_PLAN_FINAL_REVISION.md`), `AI_RECIPE.md`, `README.md` and the methodology PDF.
