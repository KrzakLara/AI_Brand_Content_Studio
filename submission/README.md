# Submission package — GymBeam HR, three Instagram posts (AI Brand Content Studio)

*Speculative portfolio work. People shown are fictional (AI-generated). Not an official GymBeam collaboration.*

**Status (Phase 7F, 2026-11-01): final submission package, technically complete and tested.** **A. Author-reviewed and accepted for the Sekvenca private take-home demonstration, including visual content, captions and Reel audio.** Confirmed in writing by the author (Lara) on 2026-11-01: she personally reviewed and accepted the three final posts, the BeastPink videos, the Wafer Reel V8 including its audio, the captions and content plan R9. **B. Portfolio demonstration only; not approved for public commercial advertising.** Not authorized for public commercial advertising without additional rights and compliance review; no brand or legal approval of the advertisement is claimed. Details: `FINAL_SIGNOFF_7F.md`. The media are git-ignored on purpose (`submission/*` except this README): they derive from brand-owned photographs and must not be published or pushed without permission.

**Entry point: [`START_HERE.md`](START_HERE.md).**

| Where | What |
|---|---|
| `START_HERE.md` | what to open, how to run, how the folders relate |
| `FINAL_SIGNOFF_7F.md` | **author sign-off record**: confirmation statement and date, covered deliverables, remaining limitations |
| `FINAL_READINESS_REPORT.md` | **current status**, tests, open items (previous: `FINAL_READINESS_REPORT_7E.md`) |
| `posts/` | the three finished posts + `POST.md` each (captions, hashtags, formats, status) |
| `methodology/METODOLOGIJA_HR.pdf` | 2-page methodology (Croatian) |
| `ai_recipe/` | `AI_RECIPE.md`, `prompts/`, `code/` (production scripts), `repo/` (source repository snapshot) |
| `phases/02_plan/FINAL_SCOPE_REVISION_7F.md` (+ `.yaml`) | **final scope** (creatine hero, Colla Pink carousel, wafer Reel), evolution from the original creatine-only brief, how the brief's rules apply |
| `phases/` | per-phase evidence incl. R9 (`02_plan/`), superseded 7E media (`05_carousel_post2/superseded_7E/`) and Reel versions V4–V8 (`06_reel_post3/versions/`) |
| `setup/SETUP.md`, `tools/`, `assets/`, `REFERENCE_ASSETS.md` | setup, bootstrap and verification tools, font, reference-photo URLs and hashes |
| `compliance/` | claim review, zinc wording check (official Croatian text), fact check against the product page, hashtag check, **`CAPTION_CHANGES_7F.md`** (before/after), alt text |
| `smoke_tests/` | test logs and results |
| `SUBMISSION_MANIFEST.json`, `SHA256SUMS.txt` | every file with source path and SHA-256 |
| `COMMIT_PLAN.md` | clean commit plan and exclusion list (nothing committed or pushed) |

The original brief is preserved unchanged: `ai_recipe/repo/briefs/gymbeam_hr.yaml`.

**Superseded (kept as history):** `READINESS_REPORT.md` (7A), `FINAL_BLOCKERS_RESOLVED.md` (7B), `FINAL_RESULTS_7C.txt` (7C), `FINAL_READINESS_REPORT_7E.md` (7E), `FINAL_CREATIVE_QA_REPORT.md` (pre-7F review; its Reel V4 findings are historical).

Reproduction: `py tools\verify_hashes.py`, `py tools\bootstrap_workspace.py --target C:\work\ws`, then the commands in `START_HERE.md`. No API key is needed; paid steps are documented in `setup/SETUP.md`.
