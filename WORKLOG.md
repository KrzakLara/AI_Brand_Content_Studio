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

## Known limitations at end of Phase 2
- The autonomous agent path (AnthropicLLM) is implemented and tested only against hand-authored recorded replies;
  it has never run against the real API (no key). The real research run used the scripted, non-autonomous policy.
- Instagram posts are a manual import (10 brand-owned posts), not collected by the runtime. APIFY path is tested
  against fixtures only.
- No vision model: Instagram visual style is `unknown`; packaging generations rest on operator-attested
  observations (status `manual`), not on a model.
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
