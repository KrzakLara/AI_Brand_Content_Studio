# WORKLOG

Only facts recorded during the session. Human active time was **not measured** and is
not estimated here.

## 2026-10-27 — Phase 1 (walking skeleton, mock providers)

Work done (by the implementation agent):
- Created `docs/ARCHITECTURE.md` (none existed), contracts, ledger, stage cache,
  mock providers, LangGraph parent graph + per-post subgraph, approvals, exporter, CLI.
- Wrote 30 pytest tests; fixed failures found by running them:
  parallel reviewers both wrote `status` (LangGraph concurrent-update error) → reviewers
  now write only their own key; mock defect config leaked into other posts' fingerprints →
  scoped per post; `interrupt()` loses node events → stale-approval flag moved into the
  interrupt payload; CLI needed a default brief for new named runs.

Measured waiting times:
- Full pytest runs: 36.9 s (28/30 passing), 44.4 s, 40.2 s (30/30 passing).
- Dependency installation: not timed.
- External API calls: none, cost 0.00 USD.

Not measured / unknown: human review time, total wall-clock of the session.

## 2026-10-27 - Phase 2 (real research & brand intelligence, GymBeam HR)

Work done (implementation agent; Sonnet 5.5):
- Inspected credentials and tools first: no ANTHROPIC_API_KEY / APIFY_TOKEN / Instagram token in the
  environment; gymbeam.hr reachable and its robots.txt allows product pages; instagram.com serves a login wall.
- Built `studio/tools` (transport, polite HTTP client, extractors, toolset, Instagram adapters), live providers
  (Anthropic adapter, scripted policy, unavailable stubs), live research agent + analyst nodes, `studio research`.
- Ran the research workflow against the real site, then iterated on defects found by inspecting the output:
  images came from the category page not product pages; product links hidden in an ItemList; same sku under two
  URLs double-counted; capsule flavour parsed as "."; "0 excluded" Instagram line was misleading; Instagram
  artifact read without a hash check (found by a test); manual-observation hash changed when the CDN re-encoded an
  image (caught by the hash check, then re-attested after viewing).
- 36 new tests; Phase 1's network-import guard tightened to "only transport.py".

Measured / known times and costs:
- Apify runs (development-time, via MCP): 42.9 s and 43.2 s, 36 posts at the listed 0.0017 USD = about 0.06 USD
  (estimate; actual Apify billing not checked).
- Full pytest: 66 passed in 58.14 s and again in 64.78 s (earlier Phase 2 test runs not individually timed).
- Live research run wall-clock and dependency installs: not timed. Human active time: not measured.

Disclosure: the first reconnaissance requests and two live research runs sent a User-Agent containing the user's
email address to gymbeam.hr. It was removed from the config afterwards and the final research run used the
clean User-Agent. Earlier runs' requests cannot be recalled.

## 2026-10-27 - Phase 2b (closing the research phase)

**Item 1 - real Anthropic run of research_agent: NOT DONE (blocked).** `ANTHROPIC_API_KEY` is not set in this
environment (checked at the start and again later), so the autonomous agent could not run and **no comparison with the
manually collected sources exists yet**. The adapter, loop, limits (`research.max_steps/max_fetches/max_cost_usd` in
`config.yaml`) and recorded-fixture tests are in place; nothing was simulated. When a key exists:

```powershell
$env:ANTHROPIC_API_KEY = "..."          # never commit it
studio research --mode live --policy anthropic --instagram import `
  --instagram-import research/imports/instagram_gymbeamhr.yaml --run research-agent-live --out research/gymbeam_hr_agent
studio compare-research --a research/gymbeam_hr_agent --b research/gymbeam_hr --label-a agent --label-b scripted --out docs/agent_vs_scripted.md
```
then paste the differences and `estimated_cost_usd` here. Cost of the real agent run so far: 0.00 USD (never ran).

Done in this phase:
- Item 2: Instagram sample raised from 10 to **30** newest brand-owned posts (19 video/reel, 10 carousel, 1 image).
  Apify run `WtGf9fc7CBKSCedez` (actor `apify/instagram-post-scraper`, input and cost in `docs/instagram_collection.md`).
  Imported programmatically from the raw export (0 caption/URL/timestamp mismatches); export saved under `research/exports/`.
- Item 3: visual analysis of **14 cover images** with post URLs for every conclusion: people, product display,
  composition, overlay typography, palette (computed). Labelled `manual` (operator-labelled, images not stored),
  never `verified`. Format distribution over all 30 posts is `verified`, with URLs per format.
- Items 4-5: current pack = NEW orange/silver "100% Pure micronised" pouch (Last-Modified of its images:
  2026-08-30 primary image, 2026-10-20 front packshot; old pouch images dated up to 2025-12/2026-04; the pack also
  appears in Instagram post DeweAhoFvZr). Selected packshot `creatine-monohydrate-unflavoured-01_8.jpg`
  (1080x1080 JPEG, grey background, no alpha, claim badges overlap the pack) -> mechanical **cut-out step** added
  (`studio/tools/imagecheck.py`), result re-inspected (transparent corners), limitation (badges stay) recorded.
- Item 6: font = Inter (verified as the website text face, 8 CSS declarations); use as creative stand-in = assumption;
  licence = assumption; wordmark typeface unknown.
- Item 7: every price has `price_retrieved_at` (32 variants), also in `evidence_registry.json`.
- Item 8: `.gitignore` ignores local Claude settings only; `.claude/skills/` is tracked again. CI guard updated.

Defects found by the work itself: packshot selection ignored identical bytes under two URLs (attestation attached to
the wrong URL; fixed + test); my first assumption "orange pouch = current" was wrong until server dates were checked;
per-variant gallery packshots turned out to be the OLD design; cached analyst output did not reflect code changes
(extractor version bumped, outputs regenerated from a clean run).

Measured: Apify run 67.6 s; full pytest 124 passed in 89.5 s. Apify cost for this run about 0.10 USD (estimate;
billing not checked). Human active time: not measured.

## 2026-10-27 - Phase 2b, second attempt: real agent run STILL BLOCKED

Requested: one real run of the autonomous research agent with `claude-sonnet-5-5`, max 5 steps, max 1 USD,
budget checked before every request. **Result: not executed.** Preflight found `ANTHROPIC_API_KEY` unset in the process,
in the Windows user/machine environment and as a `.env` file. Per the instructions I stopped there and did not look for
a key elsewhere. **Real API calls: 0. Autonomous steps: 0. Tokens: 0. Cost: 0.00 USD. No comparison exists.**
Waiting time: none (blocked immediately); active work this attempt = building the spend controls below (not timed).

What was built so the run is safe the moment a key exists (tested on recorded transports only):
- `AnthropicLLM`: worst-case cost of each request is checked BEFORE every HTTP request (retries included) against the cap;
  refuses to run without configured token prices (`anthropic_pricing` in config.yaml is empty on purpose - I did not
  invent Sonnet 5.5 prices); `max_tokens` capped at 1024 for policy decisions; actual tokens/cost from each response's
  `usage` block; request ids kept; key never logged (tested).
- Free preflight (`GET /v1/models/claude-sonnet-5-5`, no tokens) distinguishing 401 / 403 / 404 / 429 / network.
- Agent stops safely with `stop_reason: max_api_budget` instead of crashing; `--max-steps 5` verified to give exactly 5
  requests; `--max-api-spend-usd` is mandatory for a real run.
- `run_summary.json` gains `tools_selected` and an `api` block (model, requests, tokens, spent, per-call usage).

Housekeeping per instructions: whole `.claude/` ignored again, `.claude/skills/.gitkeep` removed from tracking, CI guard
rejects ANY tracked `.claude/` file (tests execute the real guard script, incl. force-added skills). The earlier
unpushed commit b2ad6d7 still contains `.claude/skills/.gitkeep` in its tree (history not rewritten); the new commit removes it.

Not done because the real run did not succeed: no `phase-2b` tag, no push (as instructed: only on success).

## Known limitations at end of Phase 2
- The autonomous agent path (AnthropicLLM) is implemented and tested only against hand-authored recorded replies;
  it has never run against the real API (no key). The real research run used the scripted, non-autonomous policy.
- Instagram posts are a manual import (10 brand-owned posts), not collected by the runtime. APIFY path is tested
  against fixtures only.
- No vision model: Instagram visual style and packaging generations rest on operator-labelled observations
  (status `manual`, 14 of 30 covers), not on a model.
- Tone/voice is `unknown` without an LLM; only measurable signals (language, emoji, CTA, hashtags, formats) are verified.
- Per-variant packaging generation is unestablished (all `unverified`).
- Prices/ratings are snapshots from 2026-10-27.

## Known limitations at end of Phase 1
- No real LLM/vision/image/video/research providers; no FFmpeg; live mode refused.
- Reel deliverable is a JSON placeholder, not a video.
- Per-post work is checkpointed at post granularity by LangGraph; finer resume relies on the
  ledger + stage cache (tested), not on subgraph checkpoints.
- `unknown` ledger operations are retried only for providers declaring `safe_to_retry`;
  the reconciliation flow for paid providers is designed, not built.
- Mock plan hashes are content based, so approval files replay across runs only while the
  brief is unchanged (intended).
- No API/web, Docker, Redis, Celery, PostgreSQL.
