# AI Brand Content Studio

An end-to-end, human-supervised **AI content-production system**. It takes a brand brief, researches the brand from real sources, plans a small Instagram campaign, produces images and video, runs quality and compliance checks, and delivers reviewed posts. Every paid AI call is metered, capped and logged.

> **Disclaimer.** The GymBeam Croatia case in this repository is an **unofficial portfolio case study**, made as a practical task for a Full-Stack Developer – AI Products application. It is not an official GymBeam collaboration. The people shown in the generated media are fictional (AI-generated). GymBeam's photographs and the finished media are **not** distributed here (see [What is deliberately not in this repository](#what-is-deliberately-not-in-this-repository)).

## What it does and the problem it solves

Producing a coherent social campaign with generative AI is not "prompt in, picture out". Brand facts must be verified, claims must be traceable to evidence, paid image and video calls must not exceed the budget, outputs must be reviewed by a human, and the whole run must be resumable and auditable. This project implements that as software:

* **Evidence-based research.** A tool-calling research agent collects brand and product facts, label data and public Instagram data into an evidence registry. Every later claim points back to evidence.
* **Plan before production.** A planner LLM proposes three posts (carousel, hero image, Reel) with concepts, copy and the evidence behind each claim. Nothing is produced until a human approves the plan hash.
* **Controlled production.** Image-editing and image-to-video calls go through adapters with hard request and USD caps, request logs and fingerprints.
* **Deterministic post-production.** Typography, cut-outs, footers, carousel assembly, Reel montage, foley/audio and QA are local, scripted and reproducible.
* **QA and delivery.** Technical validation, evidence/compliance validation, reviewer steps, targeted repair, human final approval, and export with a manifest.

## Architecture

```
Brief ─▶ Research ─▶ Plan ─▶ Production ─▶ QA ─▶ Delivery
 YAML    agent +     planner   carousel /    validators,   export +
         analyst     + human   hero / reel   reviewers,    manifest,
                     approval  (3 branches)  repair/gate   audit trail
```

| Stage | Components | Kind |
|---|---|---|
| Research | `research_agent` (autonomous tool-calling), `brand_product_analyst` (structured LLM + vision) | agent + step |
| Plan | `content_planner` (structured LLM), human approval of the plan hash, audited field-level edits | step + human gate |
| Production | `carousel_producer`, `hero_producer`, `reel_producer`; one independent branch per post | steps |
| QA | technical + evidence validation (deterministic), brand/creative/video reviewers, `qa_judge` → PASS / targeted REPAIR / ESCALATE | steps |
| Delivery | human final approval, exporter, manifest with hashes | step + human gate |

Design rules: only the research step is an autonomous loop; everything else is a structured workflow step. LangGraph state holds small JSON and artifact *references* (path, SHA-256, size), never media bytes. A SQLite ledger records every operation, so a crashed run resumes without repeating completed (paid) work. Full specification: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Technology

| | |
|---|---|
| Language / core | Python ≥ 3.12 (tested on 3.12 and 3.14), Pydantic contracts, PyYAML |
| Orchestration | **LangGraph** with a SQLite checkpointer |
| LLMs | **Anthropic** for the research agent and content planner (default `claude-sonnet-5-5`; Haiku 5.5 used for the cheap agent run) |
| Image editing | **OpenAI** image-edit API (hero and carousel stills), behind a spend-guarded adapter |
| Image-to-video | **fal.ai / Kling** (carousel and Reel clips), `studio/providers/fal_video.py` |
| Post-production | Pillow, NumPy, OpenCV (headless), **FFmpeg** via `imageio-ffmpeg`, ReportLab |
| Tests | pytest; network sockets are blocked during the suite |

## Repository layout

```
studio/            application: contracts/ nodes/ providers/ strategy/ tools/ prompts/
                   graph.py state.py ledger.py cost.py cli.py orchestrator.py
briefs/            campaign brief (briefs/gymbeam_hr.yaml)
research/          research outputs and labelled manual imports
plans/gymbeam_hr/  content plan, evidence map, decision/edit history, and the production and
                   post-production scripts (art_direction/, phase5/ carousel, phase6/reel/, phase7/ tooling)
tests/             pytest suite (mock workflow, units, spend guards, strategy, edits, image adapter, provenance)
docs/              architecture, Instagram collection notes, CLI notes for phases 1-3
config.yaml        models, pricing table, caps (no secrets)
.env.example       variable names only
submission/        git-ignored; only README.md and .gitkeep are tracked
```

## Mock mode vs. real AI content

This distinction matters:

| | What it is | Output |
|---|---|---|
| `studio run --mock` | Architecture test with deterministic mock providers. **No AI, no network, no FFmpeg.** | Flat single-colour PNGs with a MOCK banner and JSON placeholders instead of video. **These are not the final posts.** |
| Local reconstruction | The scripts in `plans/gymbeam_hr/` re-assemble the real media from archived AI outputs. Free and offline. | The real posts, but **no model is called**. Copying a stored PNG is not an AI generation. |
| New paid AI generation | Live Anthropic / OpenAI / fal.ai calls with your own keys. | New, *different* media (generation is stochastic). Costs money. Not verified as a one-click flow. |

The real GymBeam posts (hero, 6-slide carousel with two videos, Reel with audio) were produced by the live path in the original run (about 9.55 USD of image/video spend in total, hard-capped), with human approval at each gate. Those caps are consumed, so the paid scripts refuse to run again unchanged.

## Quick start (Windows PowerShell)

```powershell
git clone git@github.com:KrzakLara/AI_Brand_Content_Studio.git
cd AI_Brand_Content_Studio
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"      # use ".[dev,media]" for the local post-production scripts
$env:STUDIO_NO_DOTENV = "1"
.\.venv\Scripts\studio.exe run --mock --run demo           # MOCK workflow: placeholders only
.\.venv\Scripts\python.exe -m pytest                       # no network, no API keys
```

Live commands (research, planning, approvals, edits) are documented in [`docs/DEVELOPMENT_LOG_PHASES_1_3.md`](docs/DEVELOPMENT_LOG_PHASES_1_3.md).

### API access needed for live runs (your own keys)

Copy `.env.example` to `.env` (git-ignored) and fill in only what you use:

* `ANTHROPIC_API_KEY`: research and planning
* `OPENAI_API_KEY`: image edits
* `FAL_KEY`: Kling video
* `APIFY_TOKEN` (optional): Instagram scraping

Every paid command requires explicit `--max-requests` / `--max-api-spend-usd` caps. Keys are never printed or logged. Tests and mock runs need none.

## Results

* End-to-end pipeline from brief to three reviewed posts, with human approval gates, resumable runs and a per-operation ledger.
* A real research-agent run on Haiku 5.5, an evidence-linked plan, and audited human copy edits (AI wording is never recorded as human-authored).
* Three delivered posts: a hero image, a BeastPink Colla Pink 6-slide carousel (2 Kling clips) and an 8.83 s Reel with sound design.
* Test suite: all tests pass offline (249 passed in the development checkout; 247 passed + 2 skipped in a clean package extraction, where the 2 skipped need an official product photo that is not redistributed). No test makes a paid call.

## Limitations

* Single brand and single market (Croatian). No web UI or API yet (`api/` and `web/` are placeholders).
* Paid generation is stochastic and its caps are consumed. A new generation would produce different pictures and was not verified as a one-click flow.
* Local reconstruction was tested on Windows 10, PowerShell 5.1 and Python 3.12 with pinned media packages. Byte-identical video needs the pinned `imageio-ffmpeg`; other platforms are untested.
* Official GymBeam reference photographs must be fetched by the user, and some scripts assume them.
* Compliance checks are an engineering aid, not legal review.

## Possible next steps

* A web review UI over the approval gates.
* A provider abstraction for additional image and video models.
* Automatic reference-asset fetching with licence checks.
* Learned QA critics evaluated against human decisions.
* A CI matrix (Python 3.12 / 3.14) with fixture replay of research.

## What is deliberately not in this repository

* `.env`, API keys, tokens, databases, caches, `.venv`, `.claude/`, local logs and API usage ledgers.
* GymBeam's official photographs, the generated posts, raw Kling clips, the contact sheet built from product photos, and the final hand-in ZIP. Distribution rights are not confirmed, so `submission/*`, `runs/` and `*.zip` are git-ignored. They are delivered separately to the reviewers.
