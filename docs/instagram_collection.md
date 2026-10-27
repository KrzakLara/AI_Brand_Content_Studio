# Instagram collection (GymBeam HR, @gymbeamhr)

How the Instagram references were obtained, so the data can be reproduced, audited or replaced.

## Why not the runtime?
instagram.com serves a login wall and offers no open public API, so the studio never scrapes its HTML.
Two sanctioned routes exist in code: `ApifyInstagram` (needs `APIFY_TOKEN`, paid, not retry-safe) and
`ManualImportInstagram` (YAML with mandatory provenance). **No `APIFY_TOKEN` is available in this
environment, so the runtime Apify path has only run against test fixtures.** The posts below were collected
at development time by the operator session (Claude Code) through the Apify MCP connector and imported.

## The collection run (2026-10-27)
| | |
|---|---|
| Actor | `apify/instagram-post-scraper` (id `nH2AHrwxeTRJoN5hX`) |
| Run id / dataset id | `WtGf9fc7CBKSCedez` / `Ws21r5QsYrcldky99` |
| Started / finished | 2026-10-27T20:52:59Z / 2026-10-27T20:54:07Z (67.6 s) |
| Pricing seen | pay-per-event, FREE tier 0.0017 USD per post |
| Cost cap | `maxTotalChargeUsd: 0.15` |
| Estimated cost | about 0.10 USD (60 posts x 0.0017); **actual Apify billing not checked** |

Actor input:
```json
{"username": ["gymbeamhr"], "resultsLimit": 70, "skipPinnedPosts": false, "dataDetailLevel": "basicData"}
```
Result: 60 items = 46 brand-owned + 14 owned by other accounts (creator collaborations shown on the profile).
Earlier smaller runs (`IBw4JCdf06bKLQwA7`, `aTPUrqbrkIqnXC8o3`; 12 and 24 items) were superseded.

## What is in the repository
* `research/imports/instagram_gymbeamhr.yaml` - the import the `instagram_fetch` tool reads: the **30 newest
  brand-owned posts** (19 videos/reels, 10 carousels, 1 image; 2026-10-04 .. 2026-10-27). Captions were copied by
  script from the raw export (verified identical: 0 mismatches), not retyped.
* `research/exports/apify_instagram_post_scraper_gymbeamhr_2026-10-27.json` - the same posts as a JSON export with
  media metadata. Signed CDN query strings are stripped. The 14 non-owner posts and the 16 older brand posts are
  counted but not stored.
* `research/imports/instagram_visual_observations_gymbeamhr.yaml` - operator labels and computed palettes for
  14 of the 30 covers (see provenance inside; **cover images are not stored**, only their sha256).

## Known limits
* "Video" in the data covers Reels and feed videos; the basic data cannot tell them apart.
* Likes/comments are a snapshot (null when hidden). Only the first frame / first slide of each post is seen.
* Re-running the actor will return different posts (the feed moves) and different metrics.
