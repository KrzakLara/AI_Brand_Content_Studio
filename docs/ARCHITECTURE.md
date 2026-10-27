# AI Brand Content Studio — Architecture

Take-home for Sekvenca (Full-Stack Developer – AI Products). This document is the
primary architecture specification; it was created at the start of Phase 1 from the
agreed requirements (no prior file existed).

## Teams

| Team | Components | Kind |
|------|-----------|------|
| 1 Research | `research_agent` (autonomous tool-calling), `brand_product_analyst` (structured LLM + vision) | agent + step |
| 2 Strategy | `content_planner` (structured LLM) | step |
| 3 Production | `carousel_producer`, `hero_producer`, `reel_producer` | steps |
| 4 QA | `brand_guardian`, `creative_critic`, `video_critic`, `qa_judge` | steps |

Deterministic workflow steps (no AI): technical validation, evidence/compliance
validation, human approval, artifact export.

Only the research agent is an autonomous loop. Everything else is a structured
workflow step.

## Workflow

```
brief -> research_agent -> brand_product_analyst -> content_planner -> approve_plan
      -> [Send x3] post_workflow (one per post, independent PostState)
            producer -> technical_validation -> evidence_validation
                     -> reviewers (parallel) -> qa_judge
                     -> PASS | REPAIR (targeted, max 2) | ESCALATE
      -> approve_final -> exporter
```

Posts: `01` carousel, `02` hero image, `03` reel.

## State rules

* LangGraph state holds only small JSON: contracts dumped to dicts, artifact
  *references* (relative path, sha256, size), fingerprints. No media bytes.
* `posts` uses a dict-merge reducer; each parallel branch writes only its own key, so
  there are no concurrent-overwrite errors and a repair in one post cannot touch
  another.
* Each post runs as a compiled subgraph with its own state (`PostWF`).
* Checkpoints: `SqliteSaver`, `thread_id == run_id` (stable across resumes).

## Fingerprints and stage cache

Every stage computes `fingerprint(inputs it depends on, prompt version, provider
identity)`. The `stage_cache` table stores `(run, scope, stage) -> fingerprint, output`.
A stage is reused only if the stored fingerprint equals the freshly computed one and
the entry has not been invalidated. Fingerprints only include the inputs a stage really
reads, so changing e.g. `campaign_goal` keeps research and brand analysis cached but
invalidates planning and production.

`--from STAGE` / `--post NN` force invalidation by bumping a per-stage *generation*
that is part of every operation idempotency key (a forced redo is a deliberate new
operation, never a silent ledger replay).

## Operation ledger

`operations` table: operation_id, run_id, node, scope, provider, status
(`pending|done|failed|unknown`), timestamps, estimated cost, artifact reference,
idempotency key, small JSON result.

* A checkpoint does **not** guarantee exactly-once external calls. The ledger is
  written `pending` *before* a provider call and `done` after.
* A `done` op with the same idempotency key is reused (no second call).
* A `pending` op found on resume means the process died mid-call: it becomes
  `unknown`. Providers declare `safe_to_retry`; mock providers do, paid providers
  (Phase 2) will not, and `unknown` ops will require explicit reconciliation.
* Cost is estimated per op from config pricing; a budget guard runs before each call.

## Approvals

`ApprovalRecord(gate, artifact_fingerprint, decision, approver, source)`. Gates:
`plan`, `final`. An approval counts only if its fingerprint equals the fingerprint of
the artifact currently awaiting approval. Sources: `human_cli`, `fixture_file`
(replay), `mock_auto` (only allowed with mock providers, explicitly labelled).
Without a matching approval the graph calls `interrupt()` and pauses.

## Providers

Protocols for LLM, Vision, Image, Video, ResearchTools, injected via `Services`.
Phase 1 ships deterministic mocks only; all mock output is labelled `MOCK`.
Model IDs come from `config.yaml`. Live mode is refused until Phase 2.

## Phase map

1. Walking skeleton with mocks (this phase).
2. Real providers + research + FFmpeg.
3. API (FastAPI) and web UI.
4. Evals, hardening.
5. Submission packaging.

## Phase 2 — Real research & brand intelligence

Same graph, same engine: `research_agent` and `brand_product_analyst` dispatch to live
implementations when the injected research toolset is not a mock (`build_graph(..., until="analyst")`
cuts the graph after them; `studio research` drives it). Ledger, stage cache, fingerprints and
checkpoints apply unchanged.

**Tools** (`studio/tools/`): `web_fetch`, `instagram_fetch`, `download_image`. All network access goes
through one `Transport` (`transport.py`): `UrllibTransport` (stdlib, real) or `RecordedTransport`
(fixtures). `HttpClient` enforces a host allowlist, robots.txt (unreachable robots = fetch nothing),
size limits and bounded retries with backoff on 429/5xx/network errors.

**Agent bounds**: `research.max_steps / max_fetches / max_cost_usd`. Unknown tools, missing arguments and
duplicate calls are refused and traced, never substituted. Tool failures become `failed`/`blocked`
sources with `access_limitations`; if nothing at all is retrieved the run fails explicitly.

**Policy**: `AnthropicLLM` (needs `ANTHROPIC_API_KEY`, exercised only through recorded transports in this
environment) or `ScriptedResearchPolicy` (fixed crawl plan, labelled *not autonomous*). The CLI never falls
back from the first to the second silently.

**Instagram**: instagram.com HTML is never scraped. `ApifyInstagram` (needs `APIFY_TOKEN`, paid, not
retry-safe) or `ManualImportInstagram` (YAML with mandatory provenance).

**Trust model**: fetched content is untrusted data (sanitised, wrapped in `<untrusted_data>`, injection
phrases flagged). Evidence is `verified` only if its excerpt is re-found in the stored artifact whose
sha256 still matches; tampered artifacts are excluded and reported. Operator-attested observations
(e.g. packaging photos) are `manual`, tied to image hashes, never `verified`. Qualitative judgements
without a model are `unknown`; model inferences are `assumption` and must cite verified evidence.

**Outputs** (`runs/<id>/research/`, copied as JSON to `--out`): `brand_profile.json`,
`evidence_registry.json`, `source_index.json`, `run_summary.json`. Raw third-party media stays in the
run directory and is never exported.
