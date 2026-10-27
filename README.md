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
