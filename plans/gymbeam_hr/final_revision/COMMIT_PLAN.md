# Clean commit plan (NOT executed — nothing was committed, pushed or published)

Base: `main` at `fc38ef0`. 33 entries were uncommitted at the start of Phase 7B (plus this phase's additions). Suggested order of **separate commits**, each reviewed before the next:

| # | Commit message (suggested) | Paths |
|---|---|---|
| 1 | Fix: flush HTML parser at end of input (Python 3.14 title RCDATA) | `studio/tools/extract.py` (1 line; existing test `test_malformed_html_does_not_crash_the_parser` covers it) |
| 2 | Phase 2b–3: live research, strategy planner, spend guards | `studio/` (cli, config, contracts/inputs.py, contracts/strategy.py, graph, ledger, nodes/research.py, nodes/planner_live.py, prompts/content_planner.md, providers/live.py, services, state, strategy/), `config.yaml`, `briefs/gymbeam_hr.yaml`, deletion of `briefs/gymbeam.yaml`, `research/imports/colla_pink_evidence.yaml`, `research/imports/label_crops_gymbeam_hr.yaml`, `.env.example` |
| 3 | Phase 4–5b: image and Kling adapters | `studio/providers/fal_video.py` |
| 4 | Tests for the above | `tests/conftest.py`, `tests/test_spend.py`, `tests/test_units.py`, `tests/strategy_fixtures.py`, `tests/test_edits.py`, `tests/test_image_adapter.py`, `tests/test_phase5.py`, `tests/test_provenance.py`, `tests/test_strategy.py` |
| 5 | Plans, production scripts and decision records | `plans/` (all text/scripts/yaml/json, incl. `final_revision/`) |
| 6 | Docs and packaging metadata | `README.md`, `WORKLOG.md`, `pyproject.toml` (new `media` extra), `submission/README.md` |

## Must stay OUT of every commit
- `.env` (real keys), any file containing keys; `.claude/` (workflow guard rejects it), `.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`.
- `runs/` (all generated media, raw Kling clips, request logs, ledger.db) — git-ignored.
- `submission/*` except `.gitkeep` and `README.md` — git-ignored; the media derive from GymBeam's brand-owned photographs and must not be published without permission. They travel in the ZIP only.
- `plans/gymbeam_hr/art_direction/storyboard_contact_sheet.png` — a contact sheet built from official product photos; keep out unless permission is obtained (the only binary in `plans/`).
- `research/exports/apify_instagram_post_scraper_gymbeamhr_2026-10-27.json` is already tracked (public Instagram data); decide whether to keep it.

## Before committing
1. Re-run the secret scan (`phase7/smoke_tests.py`, test "No API keys…") and `git diff --cached | grep -E "sk-|AIza|_KEY=|TOKEN="`.
2. Run `pytest` on Python 3.12 and 3.14 (249 passed on both on 2026-10-29).
3. Decide with Lara on the open approvals in `FINAL_BLOCKERS_RESOLVED.md`; commit messages end with the usual attribution lines.
4. Push only after review; do not push `submission/` media.
