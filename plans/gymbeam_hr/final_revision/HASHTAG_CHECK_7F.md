# Hashtag check (Phase 7F, 2026-11-01)

Data: the 30 most recent @gymbeamhr Instagram posts collected with Apify on 2026-10-27 (`research/exports/apify_instagram_post_scraper_gymbeamhr_2026-10-27.json`, in the package under `phases/01_research/`). Count = number of the 30 posts that contain the tag (case-insensitive, caption or hashtag list).

| Tag | Posts of 30 | Used in | Verdict |
|---|---|---|---|
| #gymbeamhr | 19 | Posts 1, 2, 3 | brand tag, **supported** |
| #gbig | 16 | Post 1 | brand tag, **supported** |
| #gbfit | 6 | Posts 2, 3 | brand tag, **supported** (least frequent of the three; relevant to fitness/beauty content) |
| #gbwomen | 13 | — | brand tag, would suit Colla Pink (target group: women) — **not added** (no instruction; mentioned as an option) |
| #beastpink | 0 | Post 2 | **not a brand tag in the collected posts**; added in 7F at the project lead's request because the product is a BeastPink product |
| #ProteinWafer | 0 | Post 3 | descriptive product tag, not a brand tag |
| #GymBeam, #GymRoutine | 0 | removed from Post 3 | redundant with #gymbeamhr / generic and unverified |

Caveat: 30 posts are a small sample; frequency says the brand uses a tag, not that it performs well. The hashtag choice is final (selected with R9).
