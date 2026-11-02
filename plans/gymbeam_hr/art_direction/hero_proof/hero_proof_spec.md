# Hero proof: source finding, two directions, production spec and pre-flight (NO paid call has been made)

Plan hash unchanged: `ac58dcac...` (unapproved). No tag. Nothing under `.claude/`. Brand images live only in `runs/hero-proof/` (git-ignored, not redistributed).

## 1. The product asset problem
**Searched (about 25 min):** the product page of SKU 3885 in 6 country shops (hr, sk, cz, com, de, pl; hreflang lists 20 more with the same gallery). robots.txt allows media paths. 14 gallery images downloaded, 2 requests per second at most.

| Finding | Result |
|---|---|
| Studio packshots of the new orange design (`...-unflavoured-01*.jpg`, 1080 px) | **All carry the same 4 badges** in every shop. No clean packshot exists. |
| White/grey pouches (`...-1000-g`, `-1500g`, `-750g`, bezlabel images) | Old design. Not the selected design. |
| **Official studio photograph of the exact pouch** (`creatine-monohydrate-unflavoured-lifestyle.png`, 1200x1200, sha256 `cc19b0cd...`, byte-identical in all shops) | **No badges. Whole pouch visible, sharp, frontal, eye-level.** Pouch 588 x 935 px (the badge packshot gives 493 x 897). |
| Other official lifestyle photos (pool 1800 px, gym floor 1800 px) | Pool: pouch at an angle. Gym floor: the label text looks distorted (e.g. "Labtested"), so it is not trustworthy. Not used. |

**Limits of the clean photo (measured, not guessed):**
1. A shaker overlaps the pouch's right seal strip in two small places: the black lid handle (about 25 px wide, y 280-320) and a glass lug (about 12 px, y 450-520). Everything else on the pouch is intact; no printed content is hidden.
2. Real water droplets cover the pouch (baked in). So the scene must be wet/cold to be coherent; a dry gym scene would be a lie.
3. Studio light is soft, from upper left; the scene must match it.
4. It is a brand-owned photograph (same status as the packshot). Public use needs GymBeam's permission. For this assignment I treat it as the protected layer, recorded with URL, time and hash.

**Verdict: not a blocker, and no product change is needed.** The protected layer is the cut-out of this official photo (`runs/hero-proof/pouch_layer_official_photo.png`, 588x935, sha256 `5a23dc62...`; rectangular mask with rounded corners, nothing painted). The two shaker spots on the seal are hidden by a foreground scene object (your fallback rule) and NEVER by shadow-narrowing. Packshot with badges is retired as the hero layer.

## 2. Two hero art directions
**A. Premium studio commercial (SELECTED).** Honed dark slate slab with a thin film of water, warm graphite backdrop with a soft gradient, one large softbox from upper left (matches the layer), narrow orange rim-light far left, a tall glass of water with condensation in front-right overlapping the pouch's right edge (this hides the two shaker spots), a few droplets and 2 ice cubes on the slab. Camera at mid-height of the pouch, 85 mm look, f/4, real contact shadow and a soft blurred reflection on the wet slab. Headline top-left, logo bottom-left by code.
**B. Realistic athletic lifestyle.** Post-workout gym bench with cotton towel, chalk, window light, wet water bottle, faceless forearm with a water bottle in the soft foreground. More story, but the real layer's droplets and studio light fight a dry gym; the perspective must match a straight-on pouch; risk of the "AI fitness poster" look is much higher. Kept as the second proof if A fails.
**Why A:** same light and wetness as the real layer, simplest perspective, fewest things the generator can get wrong, so the real pouch stays the only authority on the product.

## 3. Production spec (one 1080x1350 PNG)
1. **Layout canvas (code, free):** neutral dark canvas 4:5; the pouch layer placed where the final pouch will be: height 810 px (scale 0.866 of the source, downscale only), pouch centre x = 640, bottom edge y = 1060 of 1350. Margins >= 90 px, bottom 150 px reserved for logo, headline zone top-left kept empty.
2. **Generate (the only paid step):** send the layout canvas as the reference image plus the prompt below, aspect 4:5 if accepted, else 1:1 and crop to 4:5. The prompt tells the model to keep the pouch exactly where it is and to build the scene, shadow and reflection around it.
3. **Select:** you choose the winner from 8 candidates.
4. **Overlay (code, free):** downscale the winner to 1080x1350, then overlay the real pouch pixels at the same coordinates (mask eroded 1 px, feathered 1 px), EXCLUDING the foreground-object region in front of the right seal (polygon drawn by us on the winner). Keep the generated shadow and reflection. Headline "Samo bitno." (Inter Bold), orange underline, official logo (still pending) set by code.
5. **QA:** pouch region must equal the source layer at scale 0.866 except where the foreground object covers it (pixel-diff + hashes written to the run folder); 100% zoom review of edges, halo, shadow contact, reflection, glass.
**Prompt (draft):** "The reference image shows a product pouch already placed on a neutral background. Do NOT change, move, resize, recolor, redraw or add text to the pouch. Build a premium commercial product photograph around it: honed dark slate surface with a thin film of water and a few droplets, warm graphite backdrop with soft gradient, one large soft key light from the upper left, a narrow orange rim light far left in the background, a tall plain glass of water with condensation in the right foreground overlapping the pouch's right edge, two ice cubes, realistic contact shadow under the pouch and a soft blurred reflection in the wet slab, camera at mid-height of the pouch, 85 mm, f/4, fine film grain. No text, no logos, no labels anywhere in the scene. Leave the upper-left area empty."
**Negative / constraints:** text, letters, logos, brand names on any object, extra packaging, hands, people, steam, neon.

## 4. Pre-flight for the paid call (needs your go)
| Item | Value |
|---|---|
| Provider / model | Google Gemini API, `gemini-nano-banana-2.1` (id and prices confirmed on Google's pricing and image-generation docs pages, read 2026-10-28) |
| Price | per generated image **$0.0336 (1K), $0.0504 (2K), $0.113 (4K)**; input $1.50 per 1M tokens; text/thinking output $7.50 per 1M tokens |
| Resolutions | 1K, 2K, 4K (512 px is NOT supported). Up to 14 reference images. Aspect ratio **4:5 is NOT confirmed** in the docs, so the first attempt tests it and falls back to 1:1 + crop |
| Quality choice | **2K**: final is 1080 wide, so 2K gives enough headroom; 4K only for a final re-render of the winner if needed |
| Estimated cost per attempt | about **$0.07** at 2K (image $0.0504 + reference image/prompt tokens + some thinking tokens); 4K about $0.13 |
| 8 candidates | about **$0.55 at 2K** (upper bound $0.8). Your cap is $5; I propose a hard stop at **$1.50** and 8 requests, via the existing budget guard pattern |
| Preservation | pouch is never regenerated: the model only sees it as a reference; the final pouch pixels are the official photo's, overlaid by code; generated pouch pixels are discarded |
| Provenance | every output carries Google's invisible SynthID watermark (documented); I will disclose that the scene is AI-generated and the product layer is a real photo |
**Missing for the call:** `.env` has only `ANTHROPIC_API_KEY`; there is **no Gemini key** and the repo has no Gemini adapter. I need (a) a `GEMINI_API_KEY` in `.env`, (b) your OK to add one thin provider adapter (about 60 lines, same budget guard and ledger pattern as the Anthropic one; no new infrastructure) plus the small free compositing script.

## 5. Reject and regenerate if any of these happens
- the pouch is moved, resized, re-lit or redrawn by the model by more than 2 px in the overlay registration (ghost edges, double outline, visible halo);
- the generated shadow or reflection does not touch the real pouch base, or the reflection shows readable text or a wrong label;
- any generated text, logo, brand mark or label anywhere (including on the glass);
- the foreground object fails to cover BOTH shaker spots on the right seal after the overlay, or looks cut out;
- light direction contradicts the layer (key not from upper left), the scene is dry while the pouch is wet, or colour cast clashes with the pouch;
- AI artefacts at 100%: warped glass, impossible ice, melted textures; poor depth or a flat, poster-like look;
- headline zone not empty, pouch below the margins, or resolution below 1080x1350.
After 8 candidates without a winner I stop and report; no further spend without your approval.

## 6. Acceptance
Side by side with 3 real @gymbeamhr posts, judged by you. The three posts' references are yours to choose; I will build a comparison image from the winner and the 3 post thumbnails you name only after you pick (their images are not downloaded by me).
