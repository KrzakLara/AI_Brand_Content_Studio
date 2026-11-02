"""Phase 7A: build the REAL submission package under submission/ (local only; no API, no network).
Copies exact existing source files, verifies SHA-256 (source before == source after == destination) and writes SUBMISSION_MANIFEST.json + SHA256SUMS.txt.
Missing sources are REPORTED (never replaced by placeholders)."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / "submission"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
CF = "runs/colla-pink/carousel_final/"
# (source relative to ROOT, destination relative to submission/, role)
MEDIA = [
    ("runs/hero-proof/hero_package/hero_FINAL_v5_1080x1350.png", "posts/post_01_creatine_hero/hero_FINAL_v5_1080x1350.png", "Post 1 hero (frozen V5)"),
    (CF + "slide1_cover_FROZEN_1080x1350.png", "posts/post_02_beastpink_carousel/slide_1_cover_FROZEN_1080x1350.png", "Post 2 slide 1"),
    (CF + "slide2_sto_je_unutra_NO_FOOTER_1080x1350.png", "posts/post_02_beastpink_carousel/slide_2_sto_je_unutra_NO_FOOTER_1080x1350.png", "Post 2 slide 2"),
    ("runs/colla-pink/slide3_video/slide3_priprema_FINAL_v2_1080x1350.mp4", "posts/post_02_beastpink_carousel/slide_3_PRIPREMA_video_v2_1080x1350.mp4", "Post 2 slide 3 (video)"),
    (CF + "slide4_kako_pripremiti_1080x1350.png", "posts/post_02_beastpink_carousel/slide_4_kako_pripremiti_1080x1350.png", "Post 2 slide 4"),
    ("runs/colla-pink/slide5_video/slide5_napitak_za_ljepotu_FINAL_v2_1080x1350.mp4", "posts/post_02_beastpink_carousel/slide_5_napitak_za_ljepotu_video_v2_1080x1350.mp4", "Post 2 slide 5 (video)"),
    (CF + "slide6_odaberi_svoj_okus_FINAL.png", "posts/post_02_beastpink_carousel/slide_6_odaberi_svoj_okus_FINAL_1080x1350.png", "Post 2 slide 6"),
    (CF + "BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v2.png", "posts/post_02_beastpink_carousel/BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v2.png", "Post 2 six-slide overview"),
    ("runs/gymbeam-wafer-reel/review_package/GYMBEAM_WAFER_LIFESTYLE_REEL_V4.mp4", "posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_LIFESTYLE_REEL_V4.mp4", "Post 3 Reel V4"),
    ("runs/gymbeam-wafer-reel/review_package/GYMBEAM_WAFER_REEL_SELECTED_COVER_B_1080x1920.png", "posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_REEL_SELECTED_COVER_B_1080x1920.png", "Post 3 selected cover B"),
    ("runs/gymbeam-wafer-reel/review_package/GYMBEAM_WAFER_REEL_SELECTED_COVER_B_4x5_grid_preview_1080x1350.png", "posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_REEL_SELECTED_COVER_B_4x5_grid_preview_1080x1350.png", "Post 3 cover 4:5 grid preview"),
]


def copy_verified(src_rel, dst_rel, role, cat):
    src = ROOT / src_rel; dst = SUB / dst_rel
    if not src.is_file():
        return {"source": src_rel, "dest": dst_rel, "role": role, "category": cat, "status": "MISSING_SOURCE"}
    h0 = sha(src); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)
    h1 = sha(dst); h2 = sha(src)
    ok = h0 == h1 == h2
    return {"source": src_rel, "dest": dst_rel, "role": role, "category": cat, "bytes": dst.stat().st_size, "sha256_source_before": h0, "sha256_dest": h1,
            "sha256_source_after": h2, "status": "VERIFIED" if ok else "HASH_MISMATCH"}


def main():
    # 1. mock placeholders: preserved outside the package (git-ignored), not deleted
    mock_dst = ROOT / "runs/_phase1_mock_submission_placeholders"; mock_dst.mkdir(exist_ok=True)
    for name in ("demo-main", "demo-esc"):
        if (SUB / name).exists():
            shutil.move(str(SUB / name), str(mock_dst / name))
    entries = []
    for s, d, r in MEDIA:
        entries.append(copy_verified(s, d, r, "media"))
    extra = json.loads((ROOT / "plans/gymbeam_hr/phase7/extra_copies.json").read_text(encoding="utf-8"))
    for s, d, r, c in extra:
        if s.endswith("/"):                                          # directory: copy every file, verified
            base = ROOT / s
            if not base.is_dir():
                entries.append({"source": s, "dest": d, "role": r, "category": c, "status": "MISSING_SOURCE"}); continue
            for f in sorted(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
                entries.append(copy_verified(f.relative_to(ROOT).as_posix(), d + f.relative_to(base).as_posix(), r, c))
        else:
            entries.append(copy_verified(s, d, r, c))
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip().count("\n") + 1
    man = {"schema": "submission-manifest/1", "package": "GymBeam HR - three Instagram posts (AI Brand Content Studio)", "built_by": "plans/gymbeam_hr/phase7/build_submission.py",
           "git_head": head, "git_working_tree_dirty_entries": dirty, "files": entries,
           "summary": {"verified": sum(e["status"] == "VERIFIED" for e in entries), "missing": [e["source"] for e in entries if e["status"] == "MISSING_SOURCE"],
                       "mismatch": [e["source"] for e in entries if e["status"] == "HASH_MISMATCH"]}}
    (SUB / "SUBMISSION_MANIFEST.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(man["summary"], indent=1)); return 0 if not man["summary"]["mismatch"] else 1


if __name__ == "__main__":
    sys.exit(main())
