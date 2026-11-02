"""Phase 7A: write extra_copies.json (the list of documentation / prompt / intermediate / code files that go into the package)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
L = []


def add(s, d, r, c):
    L.append([s, d, r, c])


# phase 1-3: research + plan
for f in ("brand_profile.json", "evidence_registry.json", "run_summary.json", "comparison_vs_manual.md", "source_index.json"):
    add(f"research/gymbeam_hr_agent/{f}", f"phases/01_research/{f}", "Haiku research agent output", "phase1-2")
add("research/gymbeam_hr_agent_attempt1_failed/run_summary.json", "phases/01_research/attempt1_FAILED_run_summary.json", "first real agent run (failed, kept as evidence)", "phase1-2")
add("research/imports/colla_pink_evidence.yaml", "phases/05_carousel_post2/colla_pink_evidence.yaml", "Colla Pink verified page facts", "phase5")
add("briefs/gymbeam_hr.yaml", "phases/02_plan/gymbeam_hr_canonical_brief.yaml", "canonical brief", "phase3")
for f in ("content_plan.json", "plan_metadata.json", "evidence_map.json", "edit_history.json", "revision_history.json"):
    add(f"plans/gymbeam_hr/{f}", f"phases/02_plan/{f}", "Sonnet 5.5 plan + human edit history (plan NOT approved)", "phase3")
add("plans/gymbeam_hr/art_direction/production_briefs.md", "phases/02_plan/production_briefs.md", "production briefs", "phase3")
# phase 4: hero
add("plans/gymbeam_hr/hero_package/", "phases/03_hero_post1/package/", "hero status / QA / submission notes", "phase4")
for f in ("hero_A_1080x1350.png", "hero_v2_corrected_1080x1350.png", "hero_v4_glass_edit_1080x1350.png", "hero_v5_closer_nolettering_1080x1350.png", "prompt_A.txt", "prompt_B.txt",
          "glass_edit_prompt.txt", "api_requests.log", "api_usage.jsonl", "hero_v2_fidelity.json"):
    add(f"runs/hero-proof/{f}", f"phases/03_hero_post1/{f}", "hero intermediate / log", "phase4")
# phase 5: carousel
for f in ("PHASE5_CAROUSEL_BRIEF.md", "colla_pink_brief.md", "colla_pink_assets.yaml", "colla_pink_edits.yaml"):
    add(f"plans/gymbeam_hr/phase5/{f}", f"phases/05_carousel_post2/{f}", "carousel brief / assets", "phase5")
add("plans/gymbeam_hr/phase5/carousel_package/", "phases/05_carousel_post2/carousel_package/", "carousel package notes / status", "phase5")
add("runs/colla-pink/cover2_raw.png", "phases/05_carousel_post2/raw/cover2_raw.png", "cover raw (accepted attempt 2)", "phase5")
add("runs/colla-pink/cover2_prompt.txt", "ai_recipe/prompts/carousel/cover2_prompt.txt", "cover prompt (used)", "prompt")
add("runs/colla-pink/cover_prompt.txt", "ai_recipe/prompts/carousel/cover_attempt1_REJECTED_prompt.txt", "rejected cover prompt", "prompt")
for n in (2, 3, 4, 5, 6):
    add(f"runs/colla-pink/carousel/s{n}_raw.png", f"phases/05_carousel_post2/raw/s{n}_raw.png", f"slide {n} raw generation", "phase5")
    add(f"runs/colla-pink/carousel/s{n}_prompt.txt", f"ai_recipe/prompts/carousel/s{n}_prompt.txt", f"slide {n} prompt", "prompt")
add("runs/colla-pink/SLIDE6_APPROVED_PINK_FRUIT_DESIGN_1092x1440.png", "phases/05_carousel_post2/raw/SLIDE6_human_approved_design_1092x1440.png", "Lara's approved slide-6 design (input)", "phase5")
add("runs/colla-pink/carousel_final/slide2_footer_before_after_REVIEW.png", "phases/05_carousel_post2/slide2_footer_removal_before_after.png", "slide 2 footer removal evidence", "phase5")
for f in ("kling_raw.mp4", "kling_prompt.txt", "kling_request.json", "fal_usage.jsonl", "start_frame_clean_1080x1350.png", "text_layer_v2_1080x1350.png", "preview_frame_with_text_v2.png",
          "slide3_priprema_FINAL_1080x1350.mp4", "qa/slide3_v2_QA_first_mid_last.png"):
    add(f"runs/colla-pink/slide3_video/{f}", f"phases/05_carousel_post2/slide3_video/{f}", "slide 3 video material (FINAL_1080x1350 = superseded v1 with title 'Priprema.')", "phase5b")
for f in ("kling_raw.mp4", "kling_raw_v2.mp4", "kling_prompt.txt", "kling_prompt_v2.txt", "kling_request.json", "kling_request_v2.json", "fal_usage.jsonl", "start_frame_clean_1080x1350.png",
          "start_frame_hair_calmed_1080x1350.png", "text_layer_v3_1080x1350.png", "hair_before_after_REVIEW.png", "preview_v3_final_typography.png", "slide5_mali_ritual_FINAL_1080x1350.mp4"):
    add(f"runs/colla-pink/slide5_video/{f}", f"phases/05_carousel_post2/slide5_video/{f}", "slide 5 video material (v1 files = rejected first attempt)", "phase5b")
add("runs/colla-pink/slide3_video/kling_prompt.txt", "ai_recipe/prompts/kling/slide3_kling_prompt.txt", "Kling prompt slide 3 (used)", "prompt")
add("runs/colla-pink/slide5_video/kling_prompt.txt", "ai_recipe/prompts/kling/slide5_attempt1_REJECTED_kling_prompt.txt", "Kling prompt slide 5 v1 (rejected)", "prompt")
add("runs/colla-pink/slide5_video/kling_prompt_v2.txt", "ai_recipe/prompts/kling/slide5_v2_kling_prompt.txt", "Kling prompt slide 5 v2 (used)", "prompt")
add("runs/hero-proof/prompt_A.txt", "ai_recipe/prompts/hero/prompt_A.txt", "hero scene prompt (used)", "prompt")
add("runs/hero-proof/prompt_B.txt", "ai_recipe/prompts/hero/prompt_B.txt", "hero prompt B", "prompt")
add("runs/hero-proof/glass_edit_prompt.txt", "ai_recipe/prompts/hero/glass_edit_prompt.txt", "hero glass edit prompt (used)", "prompt")
for f in sorted((ROOT / "studio/prompts").glob("*.md")):
    add(f"studio/prompts/{f.name}", f"ai_recipe/prompts/agents/{f.name}", "LLM system prompts (research / plan / QA agents)", "prompt")
# phase 6: reel
RW = "runs/gymbeam-wafer-reel/"
for f in sorted((ROOT / RW / "prompts").glob("*_prompt_SENT.txt")):
    add(RW + f"prompts/{f.name}", f"ai_recipe/prompts/reel/{f.name}", "reel prompt as sent", "prompt")
add(RW + "prompts/MODEL_SETTINGS.md", "ai_recipe/prompts/reel/MODEL_SETTINGS.md", "reel model settings", "prompt")
for f in sorted((ROOT / RW / "keyframes").glob("S*_keyframe_1080x1920.png")):
    add(RW + f"keyframes/{f.name}", f"phases/06_reel_post3/keyframes/{f.name}", "reel keyframe 1080x1920", "phase6")
add(RW + "keyframes/S01_raw.png", "phases/06_reel_post3/keyframes/S01_raw.png", "opening still used by V4 (raw 1152x2048)", "phase6")
for f in sorted((ROOT / RW / "video_clips").glob("*")):
    add(RW + f"video_clips/{f.name}", f"phases/06_reel_post3/video_clips/{f.name}", "Kling raw clip / request", "phase6")
for f in ("api_usage.jsonl", "api_requests.log", "fal_usage.jsonl", "assembly_timeline_V4.txt"):
    add(RW + "logs/" + f, f"phases/06_reel_post3/logs/{f}", "reel logs", "phase6")
for f in ("REEL_WORKLOG.md", "REEL_PRODUCTION_PLAN_v3.md"):
    add(RW + f, f"phases/06_reel_post3/{f}", "reel documentation", "phase6")
for f in ("V4_EDIT_REPORT.md", "V5_SNAP_PROTOTYPE_REPORT.md", "V4_CONTACT_SHEET.png", "V4_CUT_INSPECTION.png", "V5_SOURCE_COMPARISON.png", "CONTINUITY_CHECKLIST.md"):
    add(RW + "qa/" + f, f"phases/06_reel_post3/qa/{f}", "reel QA", "phase6")
for f in ("CAPTION.md", "PRODUCT_REFERENCE_LEDGER.md", "COSTS_ACTUAL_VS_ESTIMATED.md", "VERSIONS_AND_REJECTIONS.md", "LIMITATIONS.md", "REPRODUCE.md", "SHA256_MANIFEST.txt"):
    add(RW + "review_package/" + f, f"phases/06_reel_post3/review_package/{f}", "reel review package", "phase6")
add(RW + "references/official_v2/OFFICIAL_WAFER_PHOTOS.md", "phases/06_reel_post3/references/OFFICIAL_WAFER_PHOTOS.md", "official wafer photos ledger", "phase6")
add(RW + "references/official_v2/official_wafer_photos_ledger.json", "phases/06_reel_post3/references/official_wafer_photos_ledger.json", "official photos URL + SHA-256", "phase6")
add(RW + "references/reference_ledger.json", "phases/06_reel_post3/references/reference_ledger.json", "product photo ledger", "phase6")
add(RW + "cover_options/COVER_OPTIONS_SIDE_BY_SIDE.png", "posts/post_03_gymbeam_wafer_reel/alternatives/COVER_OPTIONS_A_B_C_SIDE_BY_SIDE.png", "cover options overview", "phase6")
add(RW + "review_package/GYMBEAM_WAFER_REEL_V4_COVER_ALT_clean_wrapper_1080x1920.png", "posts/post_03_gymbeam_wafer_reel/alternatives/COVER_C_clean_wrapper_1080x1920.png", "cover alternative C", "phase6")
add(RW + "review_package/GYMBEAM_WAFER_REEL_V4_COVER_1080x1920.png", "posts/post_03_gymbeam_wafer_reel/alternatives/COVER_A_original_1080x1920.png", "cover alternative A", "phase6")
# code snapshot (the code that was actually run)
add("plans/gymbeam_hr/art_direction/hero_proof/", "ai_recipe/code/hero_proof/", "hero scripts", "code")
add("plans/gymbeam_hr/phase5/", "ai_recipe/code/phase5/", "carousel + slide 2/3/5 scripts", "code")
add("plans/gymbeam_hr/phase6/reel/", "ai_recipe/code/phase6_reel/", "reel scripts", "code")
for f in ("studio/providers/live.py", "studio/providers/fal_video.py", "studio/providers/base.py", "studio/tools/transport.py", "studio/cost.py", "studio/ledger.py"):
    add(f, f"ai_recipe/code/studio/{Path(f).name}", "spend-guarded provider code", "code")
add("plans/gymbeam_hr/phase7/", "ai_recipe/code/phase7/", "packaging, smoke-test and PDF scripts", "code")
add("config.yaml", "ai_recipe/code/config.yaml", "pricing / model config", "code")
add("pyproject.toml", "setup/pyproject.toml", "package definition", "setup")
add("WORKLOG.md", "phases/WORKLOG_root.md", "project worklog (ends at Phase 5; later phases are in PHASES.md)", "phases")
(ROOT / "plans/gymbeam_hr/phase7/extra_copies.json").write_text(json.dumps(L, indent=0), encoding="utf-8")
print(len(L))
