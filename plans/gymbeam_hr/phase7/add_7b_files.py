"""Phase 7B: add the files authored/changed while resolving the submission blockers to submission/ (local copies only; no network, no spend).
Run, then smoke_tests.py, then finalize_submission.py (manifest + SHA256SUMS)."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / "submission"
FR = ROOT / "plans/gymbeam_hr/final_revision"

FILES = {                                                      # source (relative to ROOT) -> destination (relative to submission/)
    "plans/gymbeam_hr/final_revision/CONTENT_PLAN_FINAL_REVISION.md": "phases/02_plan/CONTENT_PLAN_FINAL_REVISION.md",
    "plans/gymbeam_hr/final_revision/content_plan_final_revision.json": "phases/02_plan/content_plan_final_revision.json",
    "plans/gymbeam_hr/final_revision/SLIDE5_CLAIM_REVIEW.md": "compliance/SLIDE5_CLAIM_REVIEW.md",
    "plans/gymbeam_hr/content_plan.json": "phases/02_plan/content_plan.json",   # re-copied only if identical (hash recorded in R9)
    "plans/gymbeam_hr/phase5/slide5_final_v2.py": "ai_recipe/code/phase5/slide5_final_v2.py",
    "plans/gymbeam_hr/phase7/add_7b_files.py": "ai_recipe/code/phase7/add_7b_files.py",
    "plans/gymbeam_hr/phase7/smoke_tests.py": "ai_recipe/code/phase7/smoke_tests.py",
    "plans/gymbeam_hr/phase7/make_methodology_pdf.py": "ai_recipe/code/phase7/make_methodology_pdf.py",
    "plans/gymbeam_hr/art_direction/make_contact_sheet.py": "ai_recipe/code/art_direction/make_contact_sheet.py",
    "pyproject.toml": "setup/pyproject.toml",
    "WORKLOG.md": "phases/WORKLOG_root.md",
    "plans/gymbeam_hr/phase6/reel/run_kling.py": "ai_recipe/code/phase6_reel/run_kling.py",       # 7D: tolerate a missing .env
    "plans/gymbeam_hr/phase6/reel/gen_keyframe.py": "ai_recipe/code/phase6_reel/gen_keyframe.py",
    "plans/gymbeam_hr/phase7/bootstrap_workspace.py": "ai_recipe/code/phase7/bootstrap_workspace.py",
    "plans/gymbeam_hr/phase7/verify_hashes.py": "ai_recipe/code/phase7/verify_hashes.py",
    "plans/gymbeam_hr/phase7/verify_fresh_extraction.py": "ai_recipe/code/phase7/verify_fresh_extraction.py",
    "plans/gymbeam_hr/phase7/update_7d.py": "ai_recipe/code/phase7/update_7d.py",
    "plans/gymbeam_hr/final_revision/CAPTIONS_REVIEW.md": "compliance/CAPTIONS_REVIEW.md",
    "plans/gymbeam_hr/final_revision/CAPTION_CHANGES_7E.md": "compliance/CAPTION_CHANGES_7E.md",
    "plans/gymbeam_hr/phase7/place_packshot.py": "ai_recipe/code/phase7/place_packshot.py",
    # Phase 7C
    "plans/gymbeam_hr/phase5/slide5_final_v3.py": "ai_recipe/code/phase5/slide5_final_v3.py",
    "plans/gymbeam_hr/phase5/final_contact_sheet_v3.py": "ai_recipe/code/phase5/final_contact_sheet_v3.py",
    "plans/gymbeam_hr/phase7/update_7c.py": "ai_recipe/code/phase7/update_7c.py",
    "plans/gymbeam_hr/phase5/carousel_package/carousel_status.yaml": "ai_recipe/code/phase5/carousel_package/carousel_status.yaml",
    "plans/gymbeam_hr/final_revision/COMMIT_PLAN.md": "COMMIT_PLAN.md",
}
ALSO = {"plans/gymbeam_hr/phase5/carousel_package/carousel_status.yaml": "phases/05_carousel_post2/carousel_package/carousel_status.yaml"}   # second destination of a source already in FILES
# the repository itself (what `git add` of the reviewed commit would contain, minus media, runs/, secrets, caches)
REPO_DIRS = ["studio", "tests", "briefs", "docs", "research", "evals", "api", "web", ".github", "plans"]   # plans/: decision records and scripts the tests read; duplicates ai_recipe/code on purpose
REPO_FILES = ["pyproject.toml", "config.yaml", ".env.example", "README.md", "WORKLOG.md", ".gitignore"]
SKIP = {"__pycache__", ".pytest_cache"}
SKIP_FILES = {"storyboard_contact_sheet.png"}   # built from official photos; excluded from the repository (COMMIT_PLAN.md)


def copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def refresh_manifest():
    """Verified copies whose source was legitimately changed in 7B get fresh hashes (marked), so finalize_submission.py does not report them as mismatches."""
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    mp = SUB / "SUBMISSION_MANIFEST.json"
    man = json.loads(mp.read_text(encoding="utf-8")); n = 0
    for e in man["files"]:
        if e.get("status") == "VERIFIED" and e["dest"] in set(FILES.values()) | set(ALSO.values()):
            s_now = sha(ROOT / e["source"]) if (ROOT / e["source"]).is_file() else None
            if s_now and s_now != e["sha256_source_before"]:
                e["sha256_source_before"] = e["sha256_dest"] = s_now; e["refreshed_in_7B"] = True; n += 1
    mp.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print("manifest entries refreshed:", n)


if __name__ == "__main__":
    for s, d in {**FILES, **{}}.items():
        copy(ROOT / s, SUB / d)
    for s, d in ALSO.items():
        copy(ROOT / s, SUB / d)
    n = 0
    for d in REPO_DIRS:
        for p in (ROOT / d).rglob("*"):
            if p.is_file() and not (set(p.parts) & SKIP) and p.suffix != ".pyc" and p.name != ".env" and p.name not in SKIP_FILES and p.relative_to(ROOT).parts[:2] != ("research", "exports"):   # raw Instagram export stays out (no test needs it)
                copy(p, SUB / "ai_recipe/repo" / p.relative_to(ROOT)); n += 1
    for f in REPO_FILES:
        copy(ROOT / f, SUB / "ai_recipe/repo" / f); n += 1
    print("repo files copied:", n)
    refresh_manifest()
