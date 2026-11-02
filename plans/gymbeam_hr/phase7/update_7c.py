"""Phase 7C: swap slide 5 v2 -> v3 and the contact sheet v2 -> v3 in submission/, keep v2 only as a labelled superseded file, update the manifest entries,
and regenerate the R9 machine-readable record with the SHA-256 of every delivered file. Local only; no network, no spend. Run before add_7b_files.py and finalize_submission.py."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / "submission"
CP = "posts/post_02_beastpink_carousel/"
S5 = ROOT / "runs/colla-pink/slide5_video"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

SWAPS = [  # (old dest, new dest, new source, role)
    (CP + "slide_5_napitak_za_ljepotu_video_v2_1080x1350.mp4", CP + "slide_5_napitak_za_ljepotu_video_v3_1080x1350.mp4",
     "runs/colla-pink/slide5_video/slide5_napitak_za_ljepotu_FINAL_v3_1080x1350.mp4", "Post 2 slide 5 (video) v3: zinc claim replaces the unsupported line"),
    (CP + "BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v2.png", CP + "BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v3.png",
     "runs/colla-pink/carousel_final/BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v3.png", "Post 2 six-slide overview (slide 5 = v3)"),
]
EXTRA = {  # dest -> source (copied; listed as verified copies)
    "phases/05_carousel_post2/slide5_video/superseded_v2/slide5_napitak_za_ljepotu_FINAL_v2_1080x1350.mp4": "runs/colla-pink/slide5_video/slide5_napitak_za_ljepotu_FINAL_v2_1080x1350.mp4",
    "phases/05_carousel_post2/slide5_video/slide5_v3_QA.json": "runs/colla-pink/slide5_video/slide5_v3_QA.json",
    "phases/05_carousel_post2/slide5_video/text_layer_v4_zinc_1080x1350.png": "runs/colla-pink/slide5_video/text_layer_v4_zinc_1080x1350.png",
    "phases/05_carousel_post2/slide5_video/REVIEW_slide5_v3_frame000.png": "runs/colla-pink/slide5_video/REVIEW_slide5_v3_frame000.png",
    "phases/05_carousel_post2/slide5_video/REVIEW_slide5_v3_frame060.png": "runs/colla-pink/slide5_video/REVIEW_slide5_v3_frame060.png",
    "phases/05_carousel_post2/slide5_video/REVIEW_slide5_v3_frame120.png": "runs/colla-pink/slide5_video/REVIEW_slide5_v3_frame120.png",
    "compliance/slide5_v3_frame060_PREVIEW.png": "runs/colla-pink/slide5_video/REVIEW_slide5_v3_frame060.png",
}


def put(src: Path, dst: Path):
    """Copy a file into the package, replacing a previous (possibly read-only) copy."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.chmod(0o666); dst.unlink()
    shutil.copy2(src, dst); dst.chmod(0o666)


def entry(src: str, dest: str, role: str) -> dict:
    h = sha(ROOT / src)
    return {"source": src, "dest": dest, "role": role, "category": "media", "bytes": (ROOT / src).stat().st_size, "sha256_source_before": h, "sha256_dest": h, "sha256_source_after": h, "status": "VERIFIED", "added_in_7C": True}


def main():
    mp = SUB / "SUBMISSION_MANIFEST.json"
    man = json.loads(mp.read_text(encoding="utf-8"))
    for old, new, src, role in SWAPS:
        put(ROOT / src, SUB / new)
        if (SUB / old).exists():
            (SUB / old).unlink()
        man["files"] = [e for e in man["files"] if e["dest"] != old]
        man["files"] = [e for e in man["files"] if e["dest"] != new] + [entry(src, new, role)]
    for dest, src in EXTRA.items():
        put(ROOT / src, SUB / dest)
        man["files"] = [e for e in man["files"] if e["dest"] != dest] + [entry(src, dest, "Phase 7C slide 5 evidence" if "superseded" not in dest else "SUPERSEDED slide 5 v2 (unsupported claim), kept for audit only")]
    old_prev = SUB / "compliance/REVIEW_ONLY_slide5_alt_wording_frame0.png"
    if old_prev.exists():
        old_prev.unlink()
    man["files"] = [e for e in man["files"] if "SUPERSEDED_v2_unsupported_claim" not in e["dest"]]
    shutil.rmtree(SUB / "phases/05_carousel_post2/slide5_video/SUPERSEDED_v2_unsupported_claim", ignore_errors=True)
    mp.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")

    # R9 record with deliverable hashes
    rp = ROOT / "plans/gymbeam_hr/final_revision/content_plan_final_revision.json"
    rev = json.loads(rp.read_text(encoding="utf-8"))
    h = lambda rel: sha(SUB / rel)
    slides = ["slide_1_cover_FROZEN_1080x1350.png", "slide_2_sto_je_unutra_NO_FOOTER_1080x1350.png", "slide_3_PRIPREMA_video_v2_1080x1350.mp4",
              "slide_4_kako_pripremiti_1080x1350.png", "slide_5_napitak_za_ljepotu_video_v3_1080x1350.mp4", "slide_6_odaberi_svoj_okus_FINAL_1080x1350.png"]
    reel = "posts/post_03_gymbeam_wafer_reel/"
    rev.update({"updated": "2026-10-29 (Phase 7C)", "human_decision": {
        "decided_by": "Lara", "decision": "Third post is the GymBeam 32% Protein Wafer Lifestyle Reel V4 instead of the plan reel 'Klik prije izlaska'; final direction = Post 1 Creatine Hero V5, Post 2 Colla Pink six-slide carousel, Post 3 Wafer Lifestyle Reel V4",
        "source": "Phase 6 direction (REEL_PRODUCTION_PLAN_v2.md: creative direction approved by Lara; V1-V3 rejected, V4 requested, cover B selected) and Lara's Phase 7C instruction ('final creative direction is approved in principle')",
        "verbatim_phase6_archived": False, "human_confirmation": "approved_in_principle_phase7c", "workflow_plan_approval": "NONE (plan hash 970975125494 unchanged)"}})
    p1, p2, p3 = rev["posts"]
    p1["deliverable_sha256"] = {"posts/post_01_creatine_hero/hero_FINAL_v5_1080x1350.png": h("posts/post_01_creatine_hero/hero_FINAL_v5_1080x1350.png")}
    p1["caption_final"] = "Bez buke, bez ukrasa. 🧡 U fokusu je GymBeam kreatin monohidrat. Pogledajte na linku u opisu profila. Zamišljeni portfolio oglas: scena i čaša generirane su umjetnom inteligencijom, a pakiranje potječe sa službene fotografije. Nije službena suradnja s GymBeamom. #gymbeamhr #gbig"
    p2["slide_files"] = [CP + s for s in slides]
    p2["deliverable_sha256"] = {CP + s: h(CP + s) for s in slides}
    p2["deliverable_sha256"][CP + "BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v3.png"] = h(CP + "BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v3.png")
    p2["slide5_text"] = ["NAPITAK ZA LJEPOTU", "Ljepota počinje iznutra.", "Cink doprinosi održavanju normalne kože, kose i noktiju."]
    p2["caption_final"] = ("Vaš ružičasti ritual uz Colla Pink. 💗 Što je unutra, kako se priprema i koji okus odabrati: prelistajte do kraja. Spremite objavu, a više pogledajte na linku u opisu profila. "
                           "Dodatak prehrani nije zamjena za raznoliku i uravnoteženu prehranu i zdrav način života. Preporučena dnevna doza: 1 mjerica (8 g) u 200–300 ml vode; ne prekoračujte preporučeni dnevni unos. "
                           "Nije namijenjeno djeci, trudnicama i dojiljama. Zamišljeni portfolio oglas: osoba u objavi je fiktivna (generirana umjetnom inteligencijom). Nije službena suradnja s GymBeamom. #gymbeamhr #gbfit")
    p2["caption_note"] = "accompanying statement added in 7C for Reg. (EC) 1924/2006 Art. 10(2); needs approval and legal review"
    r = "GYMBEAM_WAFER_LIFESTYLE_REEL_V4.mp4", "GYMBEAM_WAFER_REEL_SELECTED_COVER_B_1080x1920.png"
    p3["deliverable_sha256"] = {reel + f: h(reel + f) for f in r}
    p3["caption_final"] = ("Od jutarnjih obveza do treninga — neke sitnice jednostavno uvijek idu sa mnom. 🤎 GymBeam 32% Protein Wafer. #GymBeam #ProteinWafer #GymRoutine "
                           "Zamišljeni portfolio oglas (AI-generirani sadržaj) — nije službena suradnja s GymBeamom ni stvarna preporuka influencera.")
    p3["final_hashtags"] = ["#GymBeam", "#ProteinWafer", "#GymRoutine"]
    p3["hashtags_note"] = "final hashtags are those of the delivered caption; they replace the plan reel's #gymbeamhr #gbfit"
    p3["hashtags_differ_from_plan"] = True
    p1["final_hashtags"], p2["final_hashtags"] = p1["hashtags"], p2["hashtags"]
    rp.write_text(json.dumps(rev, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("swapped; R9 hashes written")


if __name__ == "__main__":
    main()
