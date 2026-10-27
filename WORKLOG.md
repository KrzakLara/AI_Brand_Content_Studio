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

## 2026-10-27 - Phase 2b, third attempt: FIRST REAL AGENT RUN (claude-haiku-5-5) - FAILED, allowance exhausted

Setup requested: model `claude-haiku-5-5`, max 5 API requests, max 0.10 USD, compact prompts, low output limits, no
paid server-side tools. The key was found in a git-ignored `.env` (never printed; a search for its value in the repo,
run outputs and all commits found 0 occurrences).

**Pricing verified** on the official page (platform.claude.com/docs/en/about-claude/pricing, read 2026-10-27, page shows
no date): Claude Haiku 5.5 = 0.10 USD/MTok input and 0.50 USD/MTok output for prompts up to 100,000 tokens (0.50/2.50 above;
the adapter REFUSES prompts that could cross 100k tokens instead of guessing a tier). Worst case per request ~0.002 USD, so
the 0.10 USD cap allowed the run with a very wide margin; it never came close.

**What really happened** (timestamps UTC; wall clock: attempt 1 = 9 s, attempt 2 = 7 s; human active time not measured):
1. 21:43 attempt 1: preflight OK (key valid, model accessible). Step s0 succeeded; step s1 returned free-text JSON that
   did not parse -> run aborted. Token usage of these two calls was lost with the process (upper bound 0.001 USD each).
2. Compatibility fix (no budget change): replaced free-text JSON with ONE client-side forced tool (`respond`, schema =
   the step schema, `tool_choice` forced). No server-side tools are sent (tested: request keys and tool shape).
3. 21:45 attempt 2 (preflight skipped, same run id; s0 reused from the ledger): the model returned valid tool calls, but
   - s0 `fetch_page`, s1 `browse`, s2 `fetch_page`: **tool names that do not exist** - REFUSED by the agent (our bug:
     the prompt never listed the tools);
   - s3 `web_fetch https://gymbeam.hr/kreatin.html` (a guessed path): executed, **HTTP 404**;
   - s4: not sent (request cap reached). Result: 0 sources retrieved -> `ResearchFailed`.
   Model's stated reasons (verbatim): "Official homepage first, to find creatine category and product pages." /
   "Try official Croatian creatine category page directly." / "Prior calls used unknown tool names; retry with a plausible
   fetch tool on the creatine category page." Full record: `research/gymbeam_hr_agent/run_summary.json`.

**Requests, tokens, cost (measured vs bounded):**
- API requests that reached Anthropic: **6 = 1 preflight + 5 messages. This is ONE MORE than the approved 5.** Cause: after
  attempt 1 I recorded the lost accounting by hand as if only ONE message had been sent; the ledger shows two (s0 and the
  malformed s1). The cap then allowed a request it should have refused. Corrected in `api_usage.jsonl`; verified against the
  ledger (`s0 sent, s1 failed-sent, s1 retry, s2, s3 sent, s4 NOT SENT`). Impact: well under 0.01 USD, but it is a breach.
- Measured (usage blocks): 3 calls (all in attempt 2) = 1330/159, 1446/169 and 1575/187 input/output tokens = 4,351 in /
  515 out = **0.000693 USD**. Unmeasured: the 2 calls of attempt 1, bounded at 0.001 USD each. **Total <= 0.002693 USD of 0.10.**
  Request ids are in `api_usage.jsonl`.

**Comparison with the GymBeam research:** not meaningful. Agent: 0 sources, 0 evidence, 0 products. Manual/scripted snapshot:
60 sources (29 live + 31 imported), 109 evidence items, 8 products. `studio compare-research` cannot run because the agent
produced no `brand_profile`/`source_index`. No success metric is claimed.

**Fixes made after the run (tested offline, NOT re-run against the API):** tool catalogue + allowed hosts now sent to the model,
"never guess paths" instruction, refusal text lists the valid tools, failed paid runs write their report instead of a
traceback, request accounting persisted per run and cumulative across restarts. 152 tests pass.

**Not done:** a successful agent run, the comparison, `phase-2b` tag, push. A retry needs a NEW explicit request allowance
(suggested: 6 requests / 0.10 USD, expected cost ~0.003 USD) - I did not extend it.

## 2026-10-27 - Phase 2b, fourth attempt: DEBUG + ONE CONTROLLED REAL RETRY (claude-haiku-5-5) - SUCCEEDED

**Diagnosis of the failed run (from its ledger, hop by hop).** API response -> `tool_use` -> parsed decision: worked every
time. Tool routing: 3 of 4 decisions named tools that do not exist (`fetch_page`, `browse`) because our payload never
listed the tools (our bug, not Haiku's) and were correctly refused. Execution: the only call that ran was a GUESSED url
(`/kreatin.html`, HTTP 404) because the homepage fetch had been refused, so no links were known. Persistence: the failed
source existed only in the ledger; `ResearchFailed` fired before anything was written -> no source index, no stage cache,
no evidence. Zero sources = three refusals + one 404 + a failure path that discarded partial results.

**Fixes (all covered by recorded-response tests; 165 tests pass; mock smoke test passes):**
- Tool catalogue + allowed hosts sent to the model; refusals list the valid tool names and are fed back to the model.
- Failure path now persists everything (`research/partial_research.json`, failed sources, refusals, reasons) and raises
  `ResearchFailed` carrying it; distinct stop reasons `policy_finished` / `max_steps` / `max_api_requests` / `max_api_budget`.
- Request limit: a `GuardedTransport` is now the FINAL authority: it counts every request to api.anthropic.com (retries,
  preflight, any code path), writes the count to `runs/<id>/api_requests.log` BEFORE forwarding and refuses at the limit,
  independent of the adapter's own counter (the first run's sixth request came from my wrong hand-written accounting).
  Tests: exactly five pass and the sixth is refused without being forwarded; holds when the adapter's bookkeeping is
  wrong; retries and preflight consume the same allowance; across restarts; malformed replies cause no hidden recovery
  call. The money limit is enforced separately (worst case before each request + stop once actual spend reaches it);
  tests show each limit binds while the other has headroom. `--max-requests` is now mandatory for a real run.
- Optional LLM enrichment in the analyst can no longer crash a run (found by the real run, see below).

**The real run** (UTC 22:09; brief `briefs/gymbeam_hr.yaml`, seeds = previously verified GymBeam URLs; preflight skipped so all
5 requests were model requests; limits 5 requests / 0.03 USD; prices 0.10 in / 0.50 out per MTok verified earlier today):
- Requests: **5 of 5 (guard log: 5 lines, all POST /v1/messages)**. Tokens: **18,525 in / 778 out**. Cost: **0.002241 USD of
  0.03** (recomputed independently 0.002242). Request ids in `research/gymbeam_hr_agent/api_usage.jsonl`.
- Tool sequence chosen by the model, all valid, all executed: s0 web_fetch /kreatin-monohidrat (seed) -> s1 web_fetch
  .../kreatin-monohidrat-gymbeam-120106.html (seed) -> s2 web_fetch .../kreatin-monohidrat-prah-mammut-nutrition.html (a link it
  saw itself) -> s3 instagram_fetch gymbeamhr -> s4 web_fetch /kreatin-creapure (a link it saw itself). Stop: `max_steps`.
- The analyst's optional tone call tried a SIXTH request: refused BEFORE sending (the limit worked) but the refusal crashed the
  analyst; fixed, tested, run resumed from cache with ZERO further requests (guard log still 5).
- Sources: 4 live pages + 31 manual-import (Instagram) = 35 ok, 0 failed. Evidence: 36 verified + 14 manual. An independent audit
  (separate code from the analyst) reopened every artifact: **36/36 verified items re-found in the stored, hash-checked content.**
- Comparison with the manual snapshot (`studio compare-research`, `research/gymbeam_hr_agent/comparison_vs_manual.md`):
  33 sources in common; agent-only 2 (`/kreatin-creapure` category, a third-party Mammut Nutrition product); manual-only 27.

**Honest assessment of the agent's quality.** Limits and plumbing work; research quality with a 5-step budget is weak: it never
fetched the focal product page (sku 3885 `100% Kreatin Monohidrat`) or the homepage/CSS (so no font/palette), spent a step on a
third-party brand's product, downloaded no packshots, so no packshot/packaging result. Agent-derived web evidence is only 6 items
(2 descriptions, 2 ratings, 2 variants); the 30 Instagram evidence items and 14 visual observations come from OUR manual imports,
which the agent merely triggered by calling `instagram_fetch`. Differences are mostly "what 5 steps could reach", not defects.

**Success criteria:** within both limits OK; genuine tool calls recorded OK; >=1 real source OK; provenance persisted OK; evidence
supported by retrieved content OK (36/36); comparison produced OK. Caveat: one model run, 5 steps, Haiku only.
Active work and waiting: real run wall-clock about 14 s + resume; the rest was debugging/tests (not timed).

## Known limitations at end of Phase 2
- The autonomous agent (AnthropicLLM, claude-haiku-5-5) has now run ONCE against the real API (fourth Phase 2b attempt:
  5 requests, 0.002241 USD). Its research quality under a 5-step budget is weak (see that entry); the canonical research
  snapshot in research/gymbeam_hr/ still comes from the scripted, non-autonomous policy plus operator imports.
- Instagram posts are a manual import (30 brand-owned posts), not collected by the runtime. APIFY path is tested
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
