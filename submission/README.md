# Project archive package (not in this repository)

This folder is a placeholder for the project's full archive package: raw AI outputs, intermediate and rejected versions, logs, compliance records and reproduction tooling. It is git-ignored (`submission/*`, except this README), so none of its contents are published.

**The final deliverables (the three Instagram posts) are published separately in [`../showcase/`](../showcase/).** These are byte-identical copies of the delivered files (SHA-256 manifest: [`../showcase/README.md`](../showcase/README.md)).

## Media rights

The rights statement that applies to every media file in this repository is in [`../README.md` → Prava na medije](../README.md#prava-na-medije). In short:

- The posts are speculative portfolio work for non-commercial demonstration only. They are not an official GymBeam or BeastPink collaboration, the brands neither commissioned nor approved them, and they are not approved for advertising.
- The product packaging in Posts 1 and 2 is cut out of official brand product photographs. In Post 3, the wafer and the bag are AI renders based on official photographs. **The rights holders have not granted permission to publish these photographs.** The media will be removed if a rights holder asks.
- The people shown are fictional and AI-generated. The health claims and the Croatian copy have not had a legal review or native-speaker proofreading.

## Archive package contents (for reference)

| Where | What |
|---|---|
| `START_HERE.md` | what to open, how to run, how the folders relate |
| `posts/` | the three finished posts, each with `POST.md` (captions, hashtags, formats, status) |
| `ai_recipe/` | `AI_RECIPE.md`, the prompts as sent, production scripts, a snapshot of the source repository |
| `phases/` | per-phase evidence: research, plan revisions, raw AI outputs, rejected and superseded versions |
| `compliance/` | claim review, zinc wording check, fact check, hashtag check, caption changes, alt text |
| `setup/`, `tools/`, `smoke_tests/` | setup, bootstrap and verification tools, test logs |
| `SUBMISSION_MANIFEST.json`, `SHA256SUMS.txt` | every file with its source path and SHA-256 |

Reproduction from the archive needs no API key: `py tools\verify_hashes.py`, `py tools\bootstrap_workspace.py --target C:\work\ws`, then the commands in `START_HERE.md`.
