"""Phase 7F: rewrite R9 (plans/gymbeam_hr/final_revision/content_plan_final_revision.json + CONTENT_PLAN_FINAL_REVISION.md) for the delivered content.
Hashes are computed from the actual files in submission/posts/ (run AFTER update_7f.py has placed the media). The original plan files and their hashes are not touched.
No approval is recorded here: approval fields stay 'pending'."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / "submission"
FR = ROOT / "plans/gymbeam_hr/final_revision"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
P2 = "posts/post_02_beastpink_carousel/"
SLIDES = [P2 + "slide_1_cover_FROZEN_1080x1350.png", P2 + "slide_2_sto_je_unutra_NO_FOOTER_1080x1350.png", P2 + "slide_3_PRIPREMA_video_v3_1080x1350.mp4",
          P2 + "slide_4_kako_pripremiti_1080x1350.png", P2 + "slide_5_napitak_za_ljepotu_video_v4_1080x1350.mp4", P2 + "slide_6_odaberi_svoj_okus_FINAL_v2_1080x1350.png"]
SHEET = P2 + "BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v4.png"
HERO = "posts/post_01_creatine_hero/hero_FINAL_v5_1080x1350.png"
REEL = "posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4"
COVER = "posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_REEL_SELECTED_COVER_B_1080x1920.png"
CAP1 = ("Bez buke, bez ukrasa. 🧡 U fokusu je GymBeam kreatin monohidrat. Pogledajte poveznicu u opisu profila. "
        "Zamišljeni portfolio oglas: scena i čaša generirane su umjetnom inteligencijom, a pakiranje potječe sa službene fotografije. Nije službena suradnja s GymBeamom. #gymbeamhr #gbig")
CAP2 = ("Vaš ružičasti ritual uz Colla Pink. 💗 Što je unutra, kako se priprema i koji okus odabrati: prelistajte do kraja. Spremite objavu, a više pogledajte putem poveznice u opisu profila. "
        "Dodatak prehrani nije zamjena za raznoliku i uravnoteženu prehranu i zdrav način života. Preporučena dnevna doza: 1 mjerica (8 g) u 200–300 ml vode; ne prekoračujte preporučeni dnevni unos. "
        "Proizvod nije namijenjen djeci, trudnicama i dojiljama. Zamišljeni portfolio oglas: osoba i prizori u objavi generirani su umjetnom inteligencijom. Nije službena suradnja s GymBeamom ni BeastPinkom. #gymbeamhr #gbfit #beastpink")
CAP3 = ("Od jutarnjih obveza do treninga — neke sitnice jednostavno uvijek idu sa mnom. 🤎 GymBeam 32% Protein Wafer. "
        "Zamišljeni portfolio oglas (AI-generirani sadržaj) — nije službena suradnja s GymBeamom ni stvarna preporuka influencera. #gymbeamhr #gbfit #ProteinWafer")
RATIONALE = ("Za treću objavu namjerno sam odabrala rough-cut stil montaže, inspiriran aktualnom TikTok i UGC estetikom. Izraženiji rezovi između kadrova kreativna su odluka kojom se nastoji postići spontaniji, autentičniji dojam sadržaja, uz jasnu priču i vidljivost proizvoda.")

old = json.loads((FR / "content_plan_final_revision.json").read_text(encoding="utf-8"))
r = {
    "revision": "R9",
    "date": "2026-10-29",
    "updated": "2026-11-01 (Phase 7F)",
    "kind": "final_delivery_revision_documentation",
    "is_approval": False,
    "supersedes_plan_hash": old["supersedes_plan_hash"],
    "preserved_originals": old["preserved_originals"],
    "human_decision": {
        "decided_by": "Lara",
        "decision": "Third post is the GymBeam 32% Protein Wafer Lifestyle Reel (final version V8) instead of the plan reel 'Klik prije izlaska'; final direction = Post 1 Creatine Hero V5, Post 2 Colla Pink six-slide carousel, Post 3 Wafer Lifestyle Reel V8",
        "source": "Phase 6 direction (phases/06_reel_post3/REEL_PRODUCTION_PLAN_v3.md: wafer Reel concept approved by Lara; V1-V3 rejected, V4 requested, cover B selected), Lara's Phase 7C instruction ('final creative direction is approved in principle'), and her visual selection of V8 over V4-V7 in the Phase 7F instruction",
        "verbatim_phase6_archived": False,
        "human_confirmation": "direction approved in principle (phase7c); V8 and the final deliverables (Posts 1-3, R9) reviewed and accepted by the author, including the Reel audio, confirmed in writing on 2026-11-01 (FINAL_SIGNOFF_7F.md)",
        "workflow_plan_approval": "NONE (plan hash 970975125494 unchanged)",
        "reel_editing_style_rationale": RATIONALE,
        "reel_editing_style_note": "Human creative decision, stated by the author in the first person. It is not a justification for visual defects of the AI material; those are listed in posts/post_03_gymbeam_wafer_reel/POST.md.",
    },
    "approval_status": {
        "A_take_home_demonstration": "Author-reviewed and accepted for the Sekvenca private take-home demonstration, including visual content, captions and Reel audio. Confirmed in writing by the author (Lara) on 2026-11-01.",
        "B_public_commercial_advertising": "Portfolio demonstration only; not approved for public commercial advertising. Not authorized for public commercial advertising without additional rights and compliance review; no brand or legal approval is claimed.",
        "audio_review": "Reel V8 audio (synthetic foley) reviewed and accepted by the author on 2026-11-01",
    },
    "author_confirmation": {"date": "2026-11-01", "statement": "Author-reviewed and accepted for the Sekvenca private take-home demonstration, including visual content, captions and Reel audio.", "limitation": "Portfolio demonstration only; not approved for public commercial advertising.", "scope": "Posts 1-3 final media, BeastPink videos, Wafer Reel V8 incl. audio, captions, R9", "brand_or_legal_approval": "none claimed"},
    "posts": [
        {"order": 1, "plan_post_id": "02", "format": "hero_image", "title": "GymBeam 100% Creatine Monohydrate hero", "deliverable": HERO, "size": "1080x1350",
         "objective": "Prepoznatljivost i poželjnost: pakiranje samo, bez dodataka.", "changed_from_plan": False, "hashtags": ["#gymbeamhr", "#gbig"],
         "deliverable_sha256": {HERO: sha(SUB / HERO)}, "caption_final": CAP1, "final_hashtags": ["#gymbeamhr", "#gbig"], "caption_status": "final text of record (compliance/CAPTION_CHANGES_7F.md), selected with R9"},
        {"order": 2, "plan_post_id": "01", "format": "carousel", "title": "BeastPink Colla Pink 'Ružičasti ritual'", "deliverable": "posts/post_02_beastpink_carousel/", "size": "1080x1350", "slides": 6,
         "slide_media": ["png", "png", "mp4", "png", "mp4", "png"], "objective": "Informiranje i spremanje: što je u napitku Colla Pink, kako se priprema i koji okus odabrati.", "changed_from_plan": False,
         "hashtags": ["#gymbeamhr", "#gbfit", "#beastpink"], "slide_files": SLIDES,
         "deliverable_sha256": {**{s: sha(SUB / s) for s in SLIDES}, SHEET: sha(SUB / SHEET)},
         "slide3_text": ["PRIPREMA:", "Prah. Voda. Gotovo."],
         "slide5_text": ["NAPITAK ZA LJEPOTU", "Ljepota počinje iznutra.", "Cink doprinosi održavanju normalne kože i kose te normalnih noktiju."],
         "slide6_text_unchanged": "ODABERI SVOJ OKUS.",
         "versions_7f": {"slide3": "v3 (subtitle 51 -> 37 px; footage identical to v2)", "slide5": "v4 (zinc wording per official Croatian Reg. 432/2012)", "slide6": "v2 (3 local retouches; frozen original kept)"},
         "caption_final": CAP2, "caption_note": "accompanying statement for Reg. (EC) 1924/2006 Art. 10(2) from the product page; page discrepancies (18 g FAQ maximum; pregnant/breastfeeding wording) flagged in compliance/POST2_FACT_CHECK_7F.md, not resolved",
         "final_hashtags": ["#gymbeamhr", "#gbfit", "#beastpink"], "caption_status": "final text of record, selected with R9",
         "compliance_status": "NOT CLEARED, legal review not done: slide 5 uses the three authorised zinc claims (official Croatian text of Reg. 432/2012, compliance/ZINC_CLAIM_432_2012_HR.md); this is a supported zinc statement, NOT a clearance of the complete advertisement"},
        {"order": 3, "plan_post_id": "03", "format": "reel", "title": "GymBeam 32% Protein Wafer Lifestyle Reel FINAL V8 'Moj mali gym essential'", "deliverable": REEL, "cover": "selected cover B", "size": "1080x1920",
         "duration_s": 8.833, "frames": 212, "fps": 24, "objective": "Angažman i storytelling: kuhinja - torba - auto - teretana s vafelom i torbom, u rough-cut / UGC-inspiriranom stilu montaže.", "changed_from_plan": True,
         "replaced_plan_concept": "Klik prije izlaska (creatine, 14 s, 6 shots, faceless hands/silhouette)", "hashtags": ["#gymbeamhr", "#gbfit", "#ProteinWafer"], "hashtags_differ_from_plan": True,
         "deliverable_sha256": {REEL: sha(SUB / REEL), COVER: sha(SUB / COVER)}, "caption_final": CAP3, "final_hashtags": ["#gymbeamhr", "#gbfit", "#ProteinWafer"],
         "hashtags_note": "#gymbeamhr and #gbfit are brand tags (compliance/HASHTAG_CHECK_7F.md); #ProteinWafer is descriptive; plan reel tags were #gymbeamhr #gbfit",
         "caption_status": "final text of record, selected with R9", "audio": "synthetic foley; reviewed and accepted by the author on 2026-11-01",
         "history": "V4 rejected (malformed bag handle); V5, V6, V7 candidates not selected; V8 selected by Lara; all kept in phases/06_reel_post3/versions/",
         "new_generation_7f": {"keyframe_S03B_usd": 0.115665, "kling_S03B_usd_logged_rate": 0.705, "kling_billing_verified": False}},
    ],
    "captions_status": "Phase 7F final texts of record (compliance/CAPTION_CHANGES_7F.md)",
    "signoff_text": "Author-reviewed and accepted for the Sekvenca private take-home demonstration, including visual content, captions and Reel audio. Portfolio demonstration only; not approved for public commercial advertising.",
    "signoff_status": "RECORDED 2026-11-01: confirmed in writing by the author (FINAL_SIGNOFF_7F.md); no brand or legal approval claimed",
    "final_scope_revision": "phases/02_plan/FINAL_SCOPE_REVISION_7F.md (+ .yaml); original brief ai_recipe/repo/briefs/gymbeam_hr.yaml preserved unchanged",
}
(FR / "content_plan_final_revision.json").write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
H = lambda rel: sha(SUB / rel)[:16] + "…"
md = f"""# Content plan — final delivery revision (R9), updated 2026-11-01 (Phase 7F)

**Status: documents exactly what is delivered.** Author-reviewed and accepted for the Sekvenca private take-home demonstration, including visual content, captions and Reel audio. Confirmed in writing by the author (Lara) on 2026-11-01 for Posts 1–3 (final 7F versions), the Reel audio, the captions and this plan R9. R9 is documentation, not a workflow-tool approval: the tool's approval status of plan hash `970975125494…` is NONE (historical, unchanged). **Portfolio demonstration only; not approved for public commercial advertising.**

Final scope and the evolution from the original creatine-only brief: `FINAL_SCOPE_REVISION_7F.md` (+ `.yaml`); the original brief `ai_recipe/repo/briefs/gymbeam_hr.yaml` is preserved unchanged.

## 1. The original plan is preserved, unchanged
| Item | Value |
|---|---|
| Last tool-produced plan (`CampaignPlan/2`) | plan hash `970975125494d10dda267d86d6ebab7f45ebb4983ae2dfb0444e0304afa01a99` (edit 8 of `edit_history.json`), approval status **NONE** |
| `plans/gymbeam_hr/content_plan.json` | SHA-256 `0edacd907fc75f354b7b34ab03bb8e26b64f89115ef282aa0dba3ff31d6b6097` |
| `plans/gymbeam_hr/history/plan_versions/plan_970975125494.json` | SHA-256 `6f2a00f8e3cc9fb8d43dba1198fe1cbf5f7d9b0228262d9198fa20a691875a8c` |
| Earlier versions | `history/plan_versions/` (10 files), `history/v1_7952850b09ab/`, `edit_history.json`, `revision_history.json` |

None of these files was edited. This revision is a **separate document** (`content_plan_final_revision.json` is its machine-readable form) and describes only what was delivered. SHA-256 of every delivered file: `content_plan_final_revision.json` and `SHA256SUMS.txt`.

## 2. What changed relative to plan 970975125494
| Post | Plan 970975125494 | Delivered | Changed? |
|---|---|---|---|
| Post 1 = plan id 02, hero | Creatine pouch alone, "SVAKA SERIJA POČINJE ODLUKOM." | Hero V5, same concept (frozen) | no |
| Post 2 = plan id 01, carousel | BeastPink Colla Pink, six slides (4 photos + 2 videos) "Vaš ružičasti ritual." | same concept; **7F corrections:** slide 3 v3, slide 5 v4, slide 6 v2 | no (concept), corrections only |
| Post 3 = plan id 03, reel | **"Klik prije izlaska"**: creatine, 14 s, 6 shots, faceless hands/silhouette, hook "Sve je na svom mjestu." | **GymBeam 32% Protein Wafer Lifestyle Reel FINAL V8 "Moj mali gym essential"**: 8.83 s, AI-generated fictional model, wafer + Urban Duffle Bag, rough-cut/UGC-inspired editing | **yes — different concept, product, length and people treatment** |

Evolution of the scope (original creatine-only brief → three-product demonstration), the dated decisions and how the brief's rules "no quantity" and "never generate packaging" apply: `FINAL_SCOPE_REVISION_7F.md`.

## 3. The three delivered posts
### Post 1 — Hero: GymBeam 100% Creatine Monohydrate (plan id 02)
- **Format:** single image, 4:5, 1080 × 1350 px, PNG. `{HERO}` (SHA-256 `{H(HERO)}`). **Goal/audience (plan):** recognisability and desirability for Croatian fitness-interested people (assumption from research; no audience analytics). Real pouch pixels from an official photograph, AI scene, code-rendered headline.
- **Caption/CTA/hashtags (final text of record, 7F):** "{CAP1}"

### Post 2 — Carousel: BeastPink Colla Pink "Ružičasti ritual" (plan id 01)
- **Format:** six slides, 1080 × 1350 px, in order: 1 cover PNG · 2 "Što je unutra" PNG · 3 "PRIPREMA:" MP4 **v3** (5.04 s) · 4 "Kako pripremiti" PNG · 5 "Napitak za ljepotu" MP4 **v4** (5.04 s) · 6 "Odaberi svoj okus" PNG **v2**. Overview `{SHEET}`.
- **Goal:** inform and save — what is in the drink, how it is prepared, which flavour to choose; educational lifestyle carousel (second product family, light pink world).
- **7F corrections:** slide 5 → "Cink doprinosi održavanju normalne kože i kose te normalnih noktiju." (three separate authorised claims; `compliance/ZINC_CLAIM_432_2012_HR.md`); slide 3 → subtitle smaller so the spoon does not cover it, drink colour kept (documented); slide 6 → stray dash, rectangular patch and grey streak retouched locally. Superseded 7E files are in `phases/05_carousel_post2/superseded_7E/`.
- **Caption/CTA/hashtags (final text of record, 7F):** "{CAP2}"
- **Compliance:** legal review not done; the zinc wording is supported, **not** a clearance of the advertisement.

### Post 3 — Reel: GymBeam 32% Protein Wafer Lifestyle Reel FINAL V8 "Moj mali gym essential" (replaces plan reel "Klik prije izlaska")
- **Format:** Instagram Reel, 9:16, 1080 × 1920 px, MP4 H.264 + AAC, 24 fps, **8.833 s (212 frames)**; selected cover **B** (with 4:5 grid preview); on-screen text "MALI RITUALI U POKRETU."; no music; quiet synthesised foley (**reviewed and accepted by the author on 2026-11-01**). `{REEL}` (SHA-256 `{H(REEL)}`).
- **Objective / audience:** engagement and storytelling for the same Croatian fitness audience: a daily routine "kitchen → gym bag → parked car → gym" in which the wafer (hero) and the Urban Duffle Bag Black appear naturally; three formats, three product categories (creatine, collagen drink, snack), three moods.
- **Creative decision — editing style (human):** "{RATIONALE}" This is the author's creative decision (stated in the first person); it is **not** a justification for visual defects of the AI material — those are listed in `posts/post_03_gymbeam_wafer_reel/POST.md`.
- **Production:** 13 keyframes, 5 Kling clips (4 in Phase 6 + **S03B** in 7F: new keyframe 0.115665 USD, Kling 3 s 0.705 USD at the logged rate, billing not verified); V1–V3 rejected; V4 rejected for a malformed bag handle; V5–V7 candidates not selected; **V8 selected by Lara**; cover B selected by Lara. The Reel is assembled locally from existing clips (`ai_recipe/code/phase6_reel/assemble_reel_v8_candidate.py`).
- **Caption/hashtags (final text of record, 7F):** "{CAP3}" Final hashtags replace the plan reel's #gymbeamhr #gbfit #… (now #gymbeamhr #gbfit #ProteinWafer).
- **Cover B:** shows the same kitchen, woman, outfit, cup, keys and bag as V8's kitchen scene and her holding the wafer; it is a separate still, not a frame of V8; the wrapper correction was made on the cover only.

## 4. Reason for the creative revision and the human decision
- **Reason:** in Phase 6 the third post was re-conceived as a new, product-led lifestyle Reel (wafer + duffle bag). The plan reel (creatine, faceless hands/silhouette, packshot reveal) was never produced; no keyframe, clip or cost exists for it.
- **Human decision (as recorded in the project):** Lara directed the wafer Reel in Phase 6, approved its storyboard and the gym-entrance shot, rejected V1–V3, requested V4 from existing assets, selected cover B; in Phase 7F she rejected V4 (malformed handle) and V5–V7 and **selected V8**. Her verbatim Phase 6 instruction is not archived in the repository; the Phase 6 production plan is `phases/06_reel_post3/REEL_PRODUCTION_PLAN_v3.md` (an earlier `…_v2.md` is also kept in the working project; R9 (7E) cited the v2 file, which is not in the package).
- **Why not `studio plan edit`:** replacing a whole reel with another product would have produced a new plan hash that no workflow gate has seen; the honest record is a separate, clearly labelled document.

## 5. Status — two different categories (do not confuse them)
| Category | Status |
|---|---|
| **A. Author-reviewed and accepted for the Sekvenca private take-home demonstration, including visual content, captions and Reel audio.** | Confirmed in writing by the author (Lara) on 2026-11-01: Post 1 Creatine Hero V5, Post 2 Colla Pink carousel (7F corrections), Post 3 Wafer Reel V8 incl. its audio, the captions, R9. |
| **B. Portfolio demonstration only; not approved for public commercial advertising.** | Not authorized for public commercial advertising without additional rights and compliance review: brand/trademark and photo permission not obtained, legal review of claims not done, native-speaker proofreading not done; no brand or legal approval is claimed. The workflow tool's approval status of the original plan hash is NONE (historical). |

**Author approval statement (recorded 2026-11-01, `FINAL_SIGNOFF_7F.md`):** "Author-reviewed and accepted for the Sekvenca private take-home demonstration, including visual content, captions and Reel audio. Portfolio demonstration only; not approved for public commercial advertising."

## 6. Verification and open limitations
- R9 lists each deliverable with its SHA-256; `phase7/smoke_tests.py` re-checks that the files in `submission/posts/` match them and that the original plan files are unchanged.
- Open limitations: the Post 2 legal review items (`compliance/SLIDE5_CLAIM_REVIEW.md`, `ZINC_CLAIM_432_2012_HR.md`, `POST2_FACT_CHECK_7F.md`); brand permission; the original plan's workflow-tool approval status is NONE (historical).
"""
(FR / "CONTENT_PLAN_FINAL_REVISION.md").write_text(md, encoding="utf-8")
print("R9 written; reel", sha(SUB / REEL)[:12], "slides", [sha(SUB / s)[:8] for s in SLIDES])
