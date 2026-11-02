"""Phase 7F: bring the corrected media, new evidence, scripts and documents into submission/ (local copies only; no network, no spend).
Order of the whole 7F packaging run (see FINAL_READINESS_REPORT.md):
  1. python update_7f.py --phase media     moves the superseded 7E files into history folders, copies the new final media + evidence with SHA-256 verification and records them in the manifest
  2. python make_r9_7f.py                  rewrites R9 from the actual media hashes
  3. python update_7f.py --phase docs      copies scripts / documents (also into the repository snapshot mirror, which bootstrap_workspace places at the same paths)
  4. python finalize_submission.py         manifest + SHA256SUMS.txt
Nothing is deleted: superseded files move to phases/05_carousel_post2/superseded_7E/ and phases/06_reel_post3/versions/."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / "submission"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location("bs", ROOT / "plans/gymbeam_hr/phase7/build_submission.py"); bs = importlib.util.module_from_spec(spec); spec.loader.exec_module(bs)
MAN = SUB / "SUBMISSION_MANIFEST.json"
P2, P3 = "posts/post_02_beastpink_carousel/", "posts/post_03_gymbeam_wafer_reel/"
S7E = "phases/05_carousel_post2/superseded_7E/"
VER = "phases/06_reel_post3/versions/"
CP = "runs/colla-pink/"
RW = "runs/gymbeam-wafer-reel/"

MOVES = [  # (old dest, new dest): superseded by 7F, moved not deleted; manifest dest updated, source mapping kept
    (P2 + "slide_3_PRIPREMA_video_v2_1080x1350.mp4", S7E + "slide_3_PRIPREMA_video_v2_1080x1350.mp4"),
    (P2 + "slide_5_napitak_za_ljepotu_video_v3_1080x1350.mp4", S7E + "slide_5_napitak_za_ljepotu_video_v3_1080x1350.mp4"),
    (P2 + "slide_6_odaberi_svoj_okus_FINAL_1080x1350.png", S7E + "slide_6_odaberi_svoj_okus_FINAL_1080x1350.png"),
    (P2 + "BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v3.png", S7E + "BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v3.png"),
    (P3 + "GYMBEAM_WAFER_LIFESTYLE_REEL_V4.mp4", VER + "GYMBEAM_WAFER_LIFESTYLE_REEL_V4_REJECTED.mp4"),
]
ADDS = [  # (source, dest, role, category)
    (CP + "slide3_video/slide3_priprema_FINAL_v3_1080x1350.mp4", P2 + "slide_3_PRIPREMA_video_v3_1080x1350.mp4", "Post 2 slide 3 v3 (video, 7F)", "media"),
    (CP + "slide5_video/slide5_napitak_za_ljepotu_FINAL_v4_1080x1350.mp4", P2 + "slide_5_napitak_za_ljepotu_video_v4_1080x1350.mp4", "Post 2 slide 5 v4 (video, 7F)", "media"),
    (CP + "carousel_final/slide6_odaberi_svoj_okus_FINAL_v2_1080x1350.png", P2 + "slide_6_odaberi_svoj_okus_FINAL_v2_1080x1350.png", "Post 2 slide 6 v2 (7F)", "media"),
    (CP + "carousel_final/BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v4.png", P2 + "BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v4.png", "Post 2 six-slide overview v4", "media"),
    (RW + "final/GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4", P3 + "GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4", "Post 3 Reel FINAL V8", "media"),
    (CP + "slide3_video/slide3_priprema_ALT_trim97f_1080x1350.mp4", "phases/05_carousel_post2/slide3_video/slide3_priprema_ALT_trim97f_1080x1350.mp4", "slide 3 alternative (trimmed before the deepest colour shift; NOT selected)", "phase5"),
    (CP + "slide3_video/text_layer_v3_1080x1350.png", "phases/05_carousel_post2/slide3_video/text_layer_v3_1080x1350.png", "slide 3 v3 text layer", "phase5"),
    (CP + "slide3_video/slide3_v3_QA.json", "phases/05_carousel_post2/slide3_video/slide3_v3_QA.json", "slide 3 v3 per-frame occlusion QA", "phase5"),
    (CP + "slide3_video/REVIEW_slide3_v2_vs_v3_subtitle.png", "phases/05_carousel_post2/slide3_video/REVIEW_slide3_v2_vs_v3_subtitle.png", "slide 3 before/after preview", "phase5"),
    (CP + "slide3_video/REVIEW_slide3_v3_frames_0_60_120.png", "phases/05_carousel_post2/slide3_video/REVIEW_slide3_v3_frames_0_60_120.png", "slide 3 v3 frames 0/60/120", "phase5"),
    (CP + "slide5_video/text_layer_v5_zinc3_1080x1350.png", "phases/05_carousel_post2/slide5_video/text_layer_v5_zinc3_1080x1350.png", "slide 5 v4 text layer", "phase5"),
    (CP + "slide5_video/slide5_v4_QA.json", "phases/05_carousel_post2/slide5_video/slide5_v4_QA.json", "slide 5 v4 per-frame QA", "phase5"),
    (CP + "slide5_video/REVIEW_slide5_v4_frame000.png", "phases/05_carousel_post2/slide5_video/REVIEW_slide5_v4_frame000.png", "slide 5 v4 review frame", "phase5"),
    (CP + "slide5_video/REVIEW_slide5_v4_frame060.png", "phases/05_carousel_post2/slide5_video/REVIEW_slide5_v4_frame060.png", "slide 5 v4 review frame", "phase5"),
    (CP + "slide5_video/REVIEW_slide5_v4_frame120.png", "phases/05_carousel_post2/slide5_video/REVIEW_slide5_v4_frame120.png", "slide 5 v4 review frame", "phase5"),
    (CP + "carousel_final/slide6_cleanup_QA.json", "phases/05_carousel_post2/slide6/slide6_cleanup_QA.json", "slide 6 retouch QA", "phase5"),
    (CP + "carousel_final/REVIEW_slide6_before_after.png", "phases/05_carousel_post2/slide6/REVIEW_slide6_before_after.png", "slide 6 before/after crops", "phase5"),
    ("research/imports/reg_432_2012_hrv_publications_office.xhtml", "phases/01_research/reg_432_2012_hrv_publications_office.xhtml", "official Croatian text of Reg. 432/2012 (EU Publications Office copy)", "compliance"),
    (RW + "final/GYMBEAM_WAFER_LIFESTYLE_REEL_V5_CANDIDATE.mp4", VER + "GYMBEAM_WAFER_LIFESTYLE_REEL_V5_CANDIDATE.mp4", "candidate, not selected", "phase6"),
    (RW + "final/GYMBEAM_WAFER_LIFESTYLE_REEL_V6_CANDIDATE.mp4", VER + "GYMBEAM_WAFER_LIFESTYLE_REEL_V6_CANDIDATE.mp4", "candidate, not selected", "phase6"),
    (RW + "final/GYMBEAM_WAFER_LIFESTYLE_REEL_V7_CANDIDATE.mp4", VER + "GYMBEAM_WAFER_LIFESTYLE_REEL_V7_CANDIDATE.mp4", "candidate, not selected", "phase6"),
    (RW + "final/GYMBEAM_WAFER_LIFESTYLE_REEL_V8_CANDIDATE.mp4", VER + "GYMBEAM_WAFER_LIFESTYLE_REEL_V8_CANDIDATE_source.mp4", "V8 source as reviewed (byte-identical to the final copy)", "phase6"),
    (RW + "keyframes/S03B_raw.png", "phases/06_reel_post3/keyframes/S03B_raw.png", "S03B keyframe as generated (1152x2048)", "phase6"),
    (RW + "keyframes/S03B_keyframe_1080x1920.png", "phases/06_reel_post3/keyframes/S03B_keyframe_1080x1920.png", "S03B keyframe 1080x1920", "phase6"),
    (RW + "video_clips/S03B_kling_raw.mp4", "phases/06_reel_post3/video_clips/S03B_kling_raw.mp4", "S03B Kling clip (raw)", "phase6"),
    (RW + "video_clips/S03B_kling_request.json", "phases/06_reel_post3/video_clips/S03B_kling_request.json", "S03B Kling request record", "phase6"),
    (RW + "logs/api_usage_S03B.jsonl", "phases/06_reel_post3/logs/api_usage_S03B.jsonl", "S03B keyframe usage record (0.115665 USD)", "phase6"),
    (RW + "logs/api_requests_S03B.log", "phases/06_reel_post3/logs/api_requests_S03B.log", "S03B keyframe request log", "phase6"),
    (RW + "prompts/S03B_prompt_SENT.txt", "ai_recipe/prompts/reel/S03B_prompt_SENT.txt", "S03B keyframe prompt as sent", "prompts"),
    (RW + "prompts/KLING_S03B_prompt_SENT.txt", "ai_recipe/prompts/reel/KLING_S03B_prompt_SENT.txt", "S03B Kling prompt as sent", "prompts"),
]
for v in ("V5", "V6", "V7", "V8"):
    ADDS.append((RW + f"logs/assembly_timeline_{v}_candidate.txt", f"phases/06_reel_post3/logs/assembly_timeline_{v}_candidate.txt", f"{v} shot timeline", "phase6"))
    ADDS.append((RW + f"qa/{v}_CANDIDATE_REPORT.md", f"phases/06_reel_post3/qa/{v}_CANDIDATE_REPORT.md", f"{v} QA report", "phase6"))
for q in ("V5_CANDIDATE_CONTACT_SHEET.png", "V5_BEFORE_AFTER.png", "V6_CANDIDATE_CONTACT_SHEET.png", "V7_CANDIDATE_CONTACT_SHEET.png", "V7_BEFORE_AFTER_CUP.png", "V7_BEFORE_AFTER_BAG.png", "V8_CANDIDATE_CONTACT_SHEET.png",
          "V8_CUTS_around_new_shot.png", "HANDLE_EVIDENCE_S03_vs_OFFICIAL.png", "S03B_CROP_handle_attachments.png", "S03B_CROP_hands_wafer.png", "S03B_COMPARE_official_bag.png"):
    ADDS.append((RW + "qa/" + q, "phases/06_reel_post3/qa/" + q, "Reel QA evidence", "phase6"))

SCRIPTS = {  # name -> (code folder under ai_recipe/code, repo folder under ai_recipe/repo/plans/gymbeam_hr, source folder in the project)
    "slide3_final_v3.py": ("phase5", "phase5", "plans/gymbeam_hr/phase5"), "slide5_final_v4.py": ("phase5", "phase5", "plans/gymbeam_hr/phase5"),
    "slide6_cleanup.py": ("phase5", "phase5", "plans/gymbeam_hr/phase5"), "final_contact_sheet_v4.py": ("phase5", "phase5", "plans/gymbeam_hr/phase5"),
    "gen_keyframe_S03B.py": ("phase6_reel", "phase6/reel", "plans/gymbeam_hr/phase6/reel"), "run_kling_S03B.py": ("phase6_reel", "phase6/reel", "plans/gymbeam_hr/phase6/reel"),
    "assemble_reel_v5_candidate.py": ("phase6_reel", "phase6/reel", "plans/gymbeam_hr/phase6/reel"), "assemble_reel_v6_candidate.py": ("phase6_reel", "phase6/reel", "plans/gymbeam_hr/phase6/reel"),
    "assemble_reel_v7_candidate.py": ("phase6_reel", "phase6/reel", "plans/gymbeam_hr/phase6/reel"), "assemble_reel_v8_candidate.py": ("phase6_reel", "phase6/reel", "plans/gymbeam_hr/phase6/reel"),
    "smoke_tests.py": ("phase7", "phase7", "plans/gymbeam_hr/phase7"), "bootstrap_workspace.py": ("phase7", "phase7", "plans/gymbeam_hr/phase7"),
    "make_methodology_pdf.py": ("phase7", "phase7", "plans/gymbeam_hr/phase7"), "make_r9_7f.py": ("phase7", "phase7", "plans/gymbeam_hr/phase7"), "update_7f.py": ("phase7", "phase7", "plans/gymbeam_hr/phase7"),
}
FR_DOCS = ["CONTENT_PLAN_FINAL_REVISION.md", "content_plan_final_revision.json", "SLIDE5_CLAIM_REVIEW.md", "ZINC_CLAIM_432_2012_HR.md", "POST2_FACT_CHECK_7F.md", "HASHTAG_CHECK_7F.md", "ALT_TEXT_HR.md", "CAPTION_CHANGES_7F.md", "FINAL_SCOPE_REVISION_7F.md", "FINAL_SCOPE_REVISION_7F.yaml"]


def put(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.chmod(0o666); dst.unlink()
    shutil.copy2(src, dst); dst.chmod(0o666)


def media():
    man = json.loads(MAN.read_text(encoding="utf-8")); by_dest = {e["dest"]: e for e in man["files"]}
    for old, new in MOVES:
        if (SUB / old).is_file():
            (SUB / new).parent.mkdir(parents=True, exist_ok=True)
            if (SUB / new).exists():
                raise SystemExit(f"{new} already exists")
            shutil.move(str(SUB / old), str(SUB / new)); print("moved", old, "->", new)
        if old in by_dest:
            by_dest[old]["dest"] = new; by_dest[old]["role"] = by_dest[old].get("role", "") + " [superseded in 7F, kept as history]"
    for s, d, r, c in ADDS:
        e = bs.copy_verified(s, d, r, c)
        if e["status"] != "VERIFIED":
            raise SystemExit(f"{s}: {e['status']}")
        man["files"] = [x for x in man["files"] if x["dest"] != d] + [e]
    stale = []
    for e in man["files"]:   # sources that changed on purpose (e.g. fal_usage.jsonl got the S03B entries): re-copy
        if e.get("status") == "VERIFIED" and e.get("source") and (ROOT / e["source"]).is_file() and sha(ROOT / e["source"]) != e["sha256_source_before"]:
            n = bs.copy_verified(e["source"], e["dest"], e["role"], e["category"]); e.update(n); stale.append(e["dest"])
    print("refreshed (source changed since 7E):", stale)
    MAN.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print("media phase done; verified entries:", sum(e["status"] == "VERIFIED" for e in man["files"]))


def docs():
    for name, (code, repo, srcdir) in SCRIPTS.items():
        s = ROOT / srcdir / name
        put(s, SUB / "ai_recipe/code" / code / name)
        if (SUB / "ai_recipe/repo/plans/gymbeam_hr" / repo).is_dir():
            put(s, SUB / "ai_recipe/repo/plans/gymbeam_hr" / repo / name)
    put(ROOT / "plans/gymbeam_hr/phase7/bootstrap_workspace.py", SUB / "tools/bootstrap_workspace.py")   # the runnable tool copy (its EXTRA mapping changed in 7F: V4 now lives in phases/06_reel_post3/versions/)
    for n in FR_DOCS:
        s = ROOT / "plans/gymbeam_hr/final_revision" / n
        put(s, SUB / "ai_recipe/repo/plans/gymbeam_hr/final_revision" / n)
        if n.startswith("CONTENT_PLAN") or n == "content_plan_final_revision.json" or n.startswith("FINAL_SCOPE"):
            put(s, SUB / "phases/02_plan" / n)
        else:
            put(s, SUB / "compliance" / n)
    print("docs phase done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--phase", choices=["media", "docs"], required=True); a = ap.parse_args()
    {"media": media, "docs": docs}[a.phase]()
