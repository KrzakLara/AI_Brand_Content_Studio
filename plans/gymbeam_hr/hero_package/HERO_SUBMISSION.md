# Hero submission package (post id 02 in the plan; "Post 01" in Lara's numbering)

**Status: SELECTED and FROZEN by Lara (Hero V5). Not approved for publication; the three-post plan is NOT approved (plan hash a923c3229e03..., approval NONE).**
**Asset:** `runs/hero-proof/hero_package/hero_FINAL_v5_1080x1350.png` (read-only copy of `hero_v5_closer_glass_edit_1080x1350.png`), 1080x1350 RGB PNG, sha256 `f05d1f3983f99981b452f33b4a469b7df9ea70e5b4c636dfca079c259d0161ba`. The image is derived from brand-owned photographs and lives in git-ignored `runs/`; it must not be published or redistributed.

| Field | Value |
|---|---|
| Objective | Prepoznatljivost i poželjnost: pakiranje samo, bez dodataka. |
| Headline (on image, code-rendered) | SVAKA SERIJA / POČINJE ODLUKOM. (Lara's selection; Inter Medium 50 px, tracked, orange accent line and full stop) |
| Caption (plan, Lara's wording) | Bez buke, bez ukrasa. 🧡 U fokusu je GymBeam kreatin monohidrat. |
| CTA | Pogledajte na linku u opisu profila. |
| Hashtags | #gymbeamhr #gbig |
| Alt text | Vrećica kreatin monohidrata GymBeam na mokroj tamnoj podlozi uz čašu vode prekrivenu kondenzacijom, osvijetljena toplim svjetlom slijeva, uz naslov Svaka serija počinje odlukom. |

**Creative rationale.** The real pouch is the only hero: a dark wet-slate commercial still with warm key light from the upper left, one narrow orange rim light, a condensation-covered glass as an intentionally cropped foreground element, and a calm imperative headline about the decision that starts a training block (no health or performance claim). The wet, cold look follows the real pouch photograph, whose droplets are real.

## Evidence / provenance
- Product layer: official GymBeam studio photograph `creatine-monohydrate-unflavoured-lifestyle.png` (gymbeam.com/.hr/.sk/.cz/.de/.pl galleries, sha256 `cc19b0cd800d...`), cut out by edge matting (`hero_proof/cutout.py`, `hero_v2.py`). The badge packshot was retired.
- Scene, glass, reflections: AI-generated with `gpt-image-2.5-sunburst` (xhigh, mask edits): candidate A (scene) and candidate G (glass only). The model's own pouch is never used.
- Typography: code-rendered Inter (SIL OFL, licence text in `runs/hero-proof/font/`).
- Plan evidence: plan `a923c3229e03...`, `evidence_map.json`; headline edit recorded as human-authored (plan edit 7).
- Cost: 4 logged requests (HTTP 401, HTTP 429, 2 paid images), 0.281945 USD of the 2.50 USD cap. Audit: `runs/hero-proof/api_requests.log`, `api_usage.jsonl`, `ledger.db`.
- Disclosure wording to use: scene and glass AI-generated, product from a real photograph.

## Fidelity, stated accurately
The pouch is **source-authentic but photographically relit, not pixel-identical**. All print (wordmark, label text, badges, "Made in Germany", (R)), print colours, silhouette, tear notches and corner radii come from the real photograph at one uniform 0.868 scale (no stretch). Changed values: a smooth lighting gain (mean 0.88, bounded 0.75-1.05), a whole-frame finishing grade, 3 px of edge light wrap. Measured against the source: CIE76 dE median 6.4, p95 15.5, label detail correlation 0.993. The label band is pixel-identical to V2; other print regions differ from V2 by at most 1.2/255 mean luminance.

**Repairs on the real pouch (disclosed):**
1. Shaker handle on the right seal: real seal rows cloned from 51 source px above (about 1,180 px at final scale); only about 437 px (~0.1%) of plain orange cloth beside it takes the model's colour (generated texture).
2. Second shaker contact (translucent lug) on the seal beside the white band: real seal rows tiled in 3-dot periods (source-derived; no printed content involved).
3. The repairs are slightly smoother than the real dot pattern (visible only at about 8x).

## Human review history
See WORKLOG.md. Key finding: moving the glass so that it overlapped the pouch produced a ghost rim, a hard edge and wrong refraction. A block move left the thin rim arc behind, and no stored image shows what a glass would refract. Resolution: one paid, mask-limited edit rebuilt only the glass beside the pouch with a gap; a free per-row shift then moved it 12 px closer. Lara accepted the partial crop of the glass as intentional.

## QA (deterministic, `hero_qa.json`)
1080x1350 OK. Headline occupies x 95-672, y 116-220, 30 px clear of the pouch top. Headline and left scene unchanged since V4. No footer and no separate logo (by decision). File hash recorded; the copy is read-only.

## Known limitations to disclose
- No separate official GymBeam logo asset (the real wordmark is on the pouch). Permission to use the brand-owned photographs publicly has not been obtained.
- The pouch prints Lab tested / Quality guaranteed, Fast absorption, IFS and HPLC badges: compliance not reviewed; the campaign makes no claim from them.
- The plan's hero `big_idea` and `concept` still mention "grafitni beton" while the produced scene is wet slate (headline, layout, alt text and art direction are already aligned). Fixable with `studio plan edit` on request.
- Croatian copy not proofread by a native speaker; Inter licence recorded, not legally reviewed.
- Approval of the whole plan and the Phase 3 tag remain with Lara.

## Remaining work
- **Post 02 (plan id 01), carousel "Kreatin izbliza":** 4 photos + 2 videos. Storyboard and briefs exist; nothing produced. Needs the next creative brief and a budget decision (hero edits cost about 0.14 USD each; video prices are unverified).
- **Post 03, reel "Klik prije izlaska", 14 s:** 6 shots; nothing produced. Audio licence and logo asset still pending.
