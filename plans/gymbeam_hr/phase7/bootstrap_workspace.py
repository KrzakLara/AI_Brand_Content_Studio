"""Rebuild a runnable project workspace from the extracted submission package (Phase 7D). Standard library only; no network, no downloads, no API keys.

The package keeps the scripts and assets under ai_recipe/ and phases/, but the scripts were written for the original project layout
(plans/gymbeam_hr/..., runs/..., studio/...). This tool copies the included files back to those layout paths so the scripts run unchanged:

  python tools/bootstrap_workspace.py --target C:\\work\\ws            (run from the extracted package folder, or pass --package <folder>)

Placement rules (every copy is SHA-256 checked against the package manifest/checksums where a hash is recorded):
  1. ai_recipe/repo/**                         -> <target>/**                       (source snapshot: studio/, tests/, briefs/, pyproject.toml ...)
  2. ai_recipe/code/{hero_proof,art_direction,phase5,phase6_reel,phase7} -> <target>/plans/gymbeam_hr/{art_direction/hero_proof,art_direction,phase5,phase6/reel,phase7}
  3. every manifest entry with a recorded original path under runs/, research/ or plans/ -> <target>/<original path>
  4. assets/fonts/*  -> <target>/runs/colla-pink/font/ ;  git init (empty repo, no commit) for the repo-hygiene tests ;  phases/02_plan/{history,...} and compliance docs -> <target>/plans/gymbeam_hr/...
Nothing that is not in the package is created or downloaded. Inputs that are NOT included (official GymBeam photographs, API keys) are listed in
<target>/BOOTSTRAP_REPORT.json and described in REFERENCE_ASSETS.md.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

CODE_MAP = {"hero_proof": "plans/gymbeam_hr/art_direction/hero_proof", "art_direction": "plans/gymbeam_hr/art_direction", "phase5": "plans/gymbeam_hr/phase5",
            "phase6_reel": "plans/gymbeam_hr/phase6/reel", "phase7": "plans/gymbeam_hr/phase7"}
EXTRA = [  # (package path or folder, workspace path)
    ("assets/fonts", "runs/colla-pink/font"),
    ("phases/05_carousel_post2/slide3_video/start_frame_clean_1080x1350.png", "runs/colla-pink/carousel/s3_nolettering_1080x1350.png"),   # byte-identical alias (slide3_video_prep.py copies this file to start_frame_clean_*): input of the stand-alone slide3_title_v2.py preview
    ("phases/06_reel_post3/versions/GYMBEAM_WAFER_LIFESTYLE_REEL_V4_REJECTED.mp4", "runs/gymbeam-wafer-reel/final/GYMBEAM_WAFER_LIFESTYLE_REEL_V4.mp4"),   # byte-identical alias of Reel V4 (kept as history, rejected in 7F; the V4 smoke test compares against it)
    ("posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_REEL_SELECTED_COVER_B_1080x1920.png", "runs/gymbeam-wafer-reel/cover_options/COVER_B_corrected_wrapper_1080x1920.png"),   # byte-identical alias of the selected cover B
    ("phases/02_plan/history", "plans/gymbeam_hr/history"),
    ("phases/02_plan/CONTENT_PLAN_FINAL_REVISION.md", "plans/gymbeam_hr/final_revision/CONTENT_PLAN_FINAL_REVISION.md"),
    ("phases/02_plan/content_plan_final_revision.json", "plans/gymbeam_hr/final_revision/content_plan_final_revision.json"),
    ("compliance/SLIDE5_CLAIM_REVIEW.md", "plans/gymbeam_hr/final_revision/SLIDE5_CLAIM_REVIEW.md"),
    ("COMMIT_PLAN.md", "plans/gymbeam_hr/final_revision/COMMIT_PLAN.md"),
    ("setup/constraints_media_7G.txt", "constraints-media-7G.txt"),   # 7G: pins imageio-ffmpeg 0.7.0 (ffmpeg 7.1) etc. so rebuilt videos are byte-identical
]
SKIP_PARTS = {"__pycache__", ".pytest_cache"}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def place(src: Path, dst: Path, placed: dict, expect: str | None = None):
    if expect and sha(src) != expect:
        raise SystemExit(f"HASH MISMATCH in package: {src}")
    if len(str(dst)) > 240:
        raise SystemExit("destination path too long for Windows (%d characters): %s -- choose a shorter --target, e.g. C:/work/ws" % (len(str(dst)), dst))
    if dst.exists():
        if sha(dst) == sha(src):
            return
        raise SystemExit(f"refusing to overwrite a different file: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst); dst.chmod(0o666)
    placed[dst.as_posix()] = sha(dst)


def walk(folder: Path):
    for p in sorted(folder.rglob("*")):
        if p.is_file() and not (set(p.parts) & SKIP_PARTS) and p.suffix != ".pyc":
            yield p


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--package", type=Path, default=Path.cwd(), help="the extracted 'submission' folder (default: current directory)")
    ap.add_argument("--target", type=Path, required=True, help="NEW or empty folder for the workspace")
    a = ap.parse_args()
    P, T = a.package.resolve(), a.target.resolve()
    if not (P / "SUBMISSION_MANIFEST.json").is_file():
        sys.exit(f"{P} does not look like the extracted package (no SUBMISSION_MANIFEST.json); use --package")
    if T.exists() and any(T.iterdir()):
        sys.exit(f"target {T} is not empty; choose a new folder")
    if P in T.parents or T == P:
        sys.exit("target must be outside the package folder")
    T.mkdir(parents=True, exist_ok=True)
    man = json.loads((P / "SUBMISSION_MANIFEST.json").read_text(encoding="utf-8"))
    placed: dict = {}
    for p in walk(P / "ai_recipe/repo"):
        place(p, T / p.relative_to(P / "ai_recipe/repo"), placed)
    for sub, dst in CODE_MAP.items():
        d = P / "ai_recipe/code" / sub
        for p in (walk(d) if d.is_dir() else []):
            place(p, T / dst / p.relative_to(d), placed)
    n_manifest = 0
    for e in man["files"]:
        s = e.get("source")
        if s and s.split("/")[0] in {"runs", "research", "plans"} and e.get("status") == "VERIFIED" and (P / e["dest"]).is_file():
            place(P / e["dest"], T / s, placed, e["sha256_dest"]); n_manifest += 1
    for s, d in EXTRA:
        src = P / s
        if src.is_dir():
            for p in walk(src):
                place(p, T / d / p.relative_to(src), placed)
        elif src.is_file():
            place(src, T / d, placed)
    (T / "runs/gymbeam-wafer-reel/audio").mkdir(parents=True, exist_ok=True)   # output folder of the Reel assembly scripts (empty; the scripts write their foley WAV there)
    git = "not available"
    if shutil.which("git"):   # the repo-hygiene tests need a git repository; empty local repo, nothing is committed
        r = subprocess.run(["git", "init", "-q", str(T)], capture_output=True, text=True)
        git = "initialised (empty, no commits)" if r.returncode == 0 else "git init failed"
    missing = []
    for rel in ("runs/colla-pink/font/Montserrat.ttf", "runs/colla-pink/slide5_video/kling_raw_v2.mp4", "runs/colla-pink/slide3_video/kling_raw.mp4",
                "runs/gymbeam-wafer-reel/video_clips/S02_kling_raw.mp4", "runs/gymbeam-wafer-reel/video_clips/S03B_kling_raw.mp4", "plans/gymbeam_hr/phase7/smoke_tests.py", "pyproject.toml"):
        if not (T / rel).is_file():
            missing.append(rel)
    report = {"package": P.as_posix(), "workspace": T.as_posix(), "files_placed": len(placed), "from_manifest_original_paths": n_manifest,
              "required_inputs_missing": missing, "local_git_repository": git,
              "expected_test_result_without_official_photos": "247 passed, 2 skipped (two tests need the stored official packshot, see REFERENCE_ASSETS.md); the full project gives 249 passed",
              "not_included_by_design": ["official GymBeam reference photographs (see REFERENCE_ASSETS.md)", ".env / API keys", "runs/ of rejected attempts and large review aids"],
              "paid_steps_need_keys_and_new_API_calls": ["gen_keyframe.py", "run_kling.py", "slide3_video_generate.py", "slide5_video_generate*.py", "hero_proof make_hero/glass_edit/refine (image edits)", "studio research/plan with live providers"]}
    (T / "BOOTSTRAP_REPORT.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "not_included_by_design"}, indent=1))
    print("\nNext (from", T, "):")
    print('  py -3.12 -m venv .venv ; .\\.venv\\Scripts\\python.exe -m pip install -e ".[dev,media]" -c constraints-media-7G.txt')
    print("  .\\.venv\\Scripts\\python.exe -m pytest")
    print("  $env:STUDIO_NO_DOTENV='1' ; .\\.venv\\Scripts\\studio.exe run --mock --run demo --export-dir $env:TEMP\\mock_out")
    print(f"  $env:SUBMISSION_DIR='{P}' ; .\\.venv\\Scripts\\python.exe plans\\gymbeam_hr\\phase7\\smoke_tests.py")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
