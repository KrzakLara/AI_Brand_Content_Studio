# CLI reference and phase notes (Phases 1-3)

> **Current state (2026-10-29):** this README describes the Phase 1 mock skeleton. Phases 2-7 (live research agent, plan, hero, Colla Pink carousel, wafer Reel, submission package)
> are documented in `WORKLOG.md`, `plans/gymbeam_hr/` and `submission/README.md`. Supported Python: **3.12 and 3.14** (full suite: 249 passed on 3.12.7 and on 3.14.0).
> Local post-production scripts need `pip install -e ".[dev,media]"`. No paid API is called without keys and the spend guards.

Take-home project for Sekvenca (Full-Stack Developer – AI Products).
Phase 1 runs the **complete workflow from brand brief to exported deliverables with
deterministic mock providers only**. No AI API, network call, FFmpeg or paid service is
used. Everything produced is labelled MOCK. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Install (Windows, PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Python 3.12; dependencies: pydantic, langgraph, langgraph-checkpoint-sqlite, pyyaml
(pytest for dev). The `studio` command is then at `.\.venv\Scripts\studio.exe`
(or activate the venv and type `studio`).

## Run the mock workflow

```powershell
studio run --mock                                   # default brief briefs/gymbeam_hr.yaml
studio run --brief briefs/gymbeam_hr.yaml --mock
```

Output goes to `submission/<run_id>/` (`manifest.json`, `MOCK_NOTICE.txt`,
`post_01_carousel/`, `post_02_hero/`, `post_03_reel/`). Run state, checkpoints, ledger
and artifacts live in `runs/<run_id>/` (git-ignored).

| Command | What it does |
|---|---|
| `studio run --mock --run ID` | resume an interrupted/crashed run (no completed operation repeats) |
| `studio run --mock --run ID --from plan` | force redo from a stage: `research analyst plan produce qa export` |
| `studio run --mock --run ID --post 03` | redo only post 03; posts 01/02 are untouched |
| `studio run --mock --approvals FILE` | replay approvals; honoured only when the fingerprint matches |
| `studio run --mock --manual-approval` | pause at the plan and final gates instead of mock auto-approval |
| `studio approve --run ID --gate plan\|final [--reject]` | record the human decision for the artifact now awaiting approval |
| `studio export-approvals --run ID --out FILE` | write a run's approvals to a replay file |
| `studio status --run ID` | status, post states, ledger summary, estimated cost |
| `studio brief --out briefs/x.yaml` | interactive brief, validated before writing |

Mock-only switches for demonstrating behaviour: `--mock-fail 03=1` (QA rejects post 03
for its first N rounds → targeted repair, `=9` → escalation) and `--mock-crash 03`
(simulate a killed process during post 03's video call; then resume).

Without `--mock` the CLI exits with an explicit error: live providers arrive in Phase 2.
Plain `--mock` auto-approves the gates and records those approvals as `mock_auto`;
that path is refused for non-mock providers.

Exit codes: 0 ok, 2 error, 3 paused for approval, 4 simulated crash.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Tests block all sockets, so any network use fails the suite.

## What the mock outputs are

* Images: solid-colour 1080×1350 PNGs with a yellow/black MOCK banner and a PNG text chunk.
* Reel: a JSON placeholder (`reel.mock.json`), **not** a video. No FFmpeg in Phase 1.
* Research: fake `https://mock.invalid/...` sources and `[MOCK]` evidence.

## Layout

```
studio/  contracts/ nodes/ providers/ tools/ prompts/  graph.py state.py store.py
         ledger.py cost.py cli.py orchestrator.py services.py
api/ web/        placeholders (Phase 3)       briefs/ evals/ submission/ docs/ tests/
```

## Known Phase 1 limits

See the end of WORKLOG.md. Short version: no real providers, research, FFmpeg, API or UI;
`studio/tools/` is an empty package for Phase 2 research tools.

## Phase 2 — real research (GymBeam Croatia)

```powershell
# real HTTP to gymbeam.hr; Instagram posts from a labelled manual import; NON-autonomous scripted plan
studio research --mode live --policy scripted --instagram import `
  --instagram-import research/imports/instagram_gymbeamhr.yaml --run research-gymbeam-hr-live --out research/gymbeam_hr
```

* `--policy anthropic` (default) is the autonomous LLM agent. It needs `ANTHROPIC_API_KEY` and **exits with
  an error if it is missing**; it never falls back to a script or a mock. `--policy scripted` must be chosen
  explicitly and is reported as `autonomous: False`.
* `--instagram apify` needs `APIFY_TOKEN` (paid per post). Without it the source is recorded as failed.
* `--mode fixture --fixtures DIR` replays recorded responses (used by the tests).
* Results: `research/gymbeam_hr/{brand_profile,evidence_registry,source_index,run_summary}.json`.
  Read `research/README.md` for what is real, manual, fixture or mock.

Phase 1 commands (`studio run --mock ...`) are unchanged.

### Phase 2b additions
* `studio compare-research --a DIR --b DIR` diffs two research outputs (sources, products, evidence, cost).
* `brand_profile.json` now also contains `selected_packshot` (source, retrieval date, server `Last-Modified`,
  resolution/alpha checks, recorded cut-out), `selected_font`, per-post visual conclusions and per-format post lists.
* Optional extra for image checks and cut-outs: `pip install -e ".[images]"` (Pillow). Without it these steps are
  skipped **explicitly** and reported in `limitations`.
* Instagram collection details: [docs/instagram_collection.md](docs/instagram_collection.md).
* The whole `.claude/` directory is git-ignored and a CI check fails if any file under it is tracked.

### Running the real autonomous agent (needs your key and prices)
```powershell
$env:ANTHROPIC_API_KEY = "..."      # never commit it; the code never prints or logs it
# 1. config.yaml anthropic_pricing needs an entry for the model (claude-haiku-5-5 is filled in, verified 2026-10-27)
# 2. free preflight: key valid + model accessible, no tokens spent
studio research --mode live --policy anthropic --model claude-haiku-5-5 --run RUN_ID --max-api-spend-usd 0.10 --max-requests 5 --preflight-only
# 3. the run (refused unless a spend cap is given; the cap is checked before EVERY request, retries included)
studio research --mode live --policy anthropic --instagram import --instagram-import research/imports/instagram_gymbeamhr.yaml `
  --model claude-haiku-5-5 --max-api-spend-usd 0.10 --max-requests 5 --max-steps 5 --run research-agent-live --out research/gymbeam_hr_agent
studio compare-research --a research/gymbeam_hr_agent --b research/gymbeam_hr --label-a agent --label-b scripted --out docs/agent_vs_scripted.md
```
`run_summary.json` then contains the tool sequence, the model's stated reasons, request ids and token usage/cost.

Note: `--max-requests` counts the preflight and retries too, and is cumulative per run id (`runs/<id>/api_usage.jsonl`).
The `.env` file (git-ignored) is read by the CLI for variables not already set; it is never printed or committed.


## Phase 3 - content strategy and human approval

A real model (config `models.planner_llm`, default `claude-sonnet-5-5`) plans three Instagram posts from the verified research
(`research/gymbeam_hr/`). Every paid run needs explicit caps; the plan then **waits for you**. Nothing is approved automatically.

```powershell
# 1. generate (preflight + draft + at most one automatic repair = up to 3 requests)
studio plan generate --run plan-gymbeam-hr-1 --max-requests 3 --max-api-spend-usd 0.50
# 2. read everything: three concepts, exact evidence behind each claim, approval state for THIS hash
studio plan review --run plan-gymbeam-hr-1
# 3a. decide (you type the first 12 characters of the hash shown; refused without a terminal or --confirm)
studio plan approve --run plan-gymbeam-hr-1 --comment "ok"
studio plan reject  --run plan-gymbeam-hr-1 --comment "why"
# 3b. or ask for changes: re-runs only the planner on the same research; the old approval stops counting
studio plan revise  --run plan-gymbeam-hr-1 --feedback "add a person to the reel" --max-requests 2 --max-api-spend-usd 0.40
#    (give the paid step its own allowance with --usage-tag rev1; --feedback-file stores your words verbatim in revision_history.json)
studio plan revise  --run plan-gymbeam-hr-1 --feedback-file feedback.md --max-requests 2 --max-api-spend-usd 0.40 --usage-tag rev1
#    a blocked step (validator error, refused budget) can be continued WITHOUT repeating paid calls recorded in the ledger:
studio plan resume  --run plan-gymbeam-hr-1 --max-requests 2 --max-api-spend-usd 0.40 --usage-tag rev1
# 4. write deliverables (content_plan.json, briefs/, evidence_map.json, plan_metadata.json, usage logs) - re-run after deciding
studio plan export  --run plan-gymbeam-hr-1 --out plans/gymbeam_hr
```

Canonical brief: `briefs/gymbeam_hr.yaml` (the human's decisions are recorded there: focal product sku 3885, locked hero headline, constraints).
Earlier plan versions stay under `plans/gymbeam_hr/history/`; the current plan is the top level of `plans/gymbeam_hr/`.

### Human copy edits (`studio plan edit`)
Edits are field-level, exact-match, atomic and audited; AI wording is never recorded as human-authored. Nothing is applied until a human has confirmed it.
```powershell
studio plan edit --run plan-gymbeam-hr-1 --edits edits.yaml --reason "Human copy review" --dry-run   # preview + validate, writes nothing
studio plan edit --run plan-gymbeam-hr-1 --edits edits.yaml --reason "Human copy review"             # apply (every edit needs confirmed_by + confirmation_source)
studio plan review --run plan-gymbeam-hr-1                                                            # then decide on the NEW hash
```
`edits.yaml`: `base_plan_hash` plus `edits[]` with `id, op (replace|remove), post (campaign|01|02|03), slide|shot, path, expected, replacement, reason,
proposed_by (ai:<who>|human:<who>), requested_by, confirmed_by, confirmation_source`. The proposal for the current plan is
`plans/gymbeam_hr/proposed_edits_for_lara.yaml` (all unconfirmed).
