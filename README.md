# AI Brand Content Studio — Phase 1 (walking skeleton, mock providers)

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
studio run --mock                                   # default brief briefs/gymbeam.yaml
studio run --brief briefs/gymbeam.yaml --mock
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
# 1. fill anthropic_pricing in config.yaml (USD per million tokens, from Anthropic's official pricing page)
# 2. free preflight: key valid + model accessible, no tokens spent
studio research --mode live --policy anthropic --max-api-spend-usd 1 --max-steps 5 --preflight-only
# 3. the run (refused unless a spend cap is given; the cap is checked before EVERY request, retries included)
studio research --mode live --policy anthropic --instagram import --instagram-import research/imports/instagram_gymbeamhr.yaml `
  --max-api-spend-usd 1 --max-steps 5 --run research-agent-live --out research/gymbeam_hr_agent
studio compare-research --a research/gymbeam_hr_agent --b research/gymbeam_hr --label-a agent --label-b scripted --out docs/agent_vs_scripted.md
```
`run_summary.json` then contains the tool sequence, the model's stated reasons, request ids and token usage/cost.
