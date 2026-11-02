# POST 3 — Production plan v2 (supersedes §3, §5, §6, §7 of REEL_PRODUCTION_PLAN.md)

Status: **creative direction approved by Lara; budget NOT authorized; nothing generated; 0.00 USD spent.**

## 1. Revision: real motion where it matters

Kling AI video is spent only on the three key product interactions. Everything else is local editing or one match cut. Walking is **not** animated with Kling.

| # | Time | Shot | Method | Paid? |
|---|---|---|---|---|
| 01 | 0–1.5 s | Morning counter, wafer pack, keys, coffee cup | **LOCAL**: keyframe + push-in + animated light sweep + coffee-steam overlay | image only |
| 02 | 1.5–4 s | **She picks up the wafer** from the counter | **AI VIDEO – Kling 3 s** (use ~2.5 s) | yes |
| 03 | 4–6.5 s | **She puts the wafer into the Urban Duffle and zips it** | **AI VIDEO – Kling 3 s** (use ~2.5 s) | yes |
| 04 | 6.5–8 s | Heading out | **LOCAL**: still A (low-angle bag in hand, local sway) → hard cut → still B (car door/handle) with door foley | images only |
| 05 | 8–9.5 s | Parked car, seated, bag on passenger seat, engine off | **LOCAL**: slow drift + moving window-light overlay | image only |
| 06 | 9.5–12.5 s | **Wafer taken out of the bag and unwrapped in the parked car** | **AI VIDEO – Kling 3 s** (use up to 3 s) | yes |
| 07 | 12.5–15 s | Crunch hero | **MATCH CUT**: intact wafer keyframe → cut on the beat + crunch SFX → broken wafer keyframe (2-frame flash) | images only |
| 08 | 15–18 s | End frame: pack + broken piece, bag blurred behind | **LOCAL**: slow push-in + text overlay | image only |

Total 18.0 s · 1080×1920 · 24 fps. All text is a deterministic overlay (Pillow/ffmpeg): opening `MALI RITUALI U POKRETU.` (0–1.5 s); ending `TVOJ SNACK. TVOJ RITAM.` + small label `GymBeam 32% Protein Wafer`.

Optional hardening (no extra Kling cost, +1 keyframe each): pass an **end frame** to Kling for S03 and S06 (bag closed / wrapper open) to limit morphing.

## 2. Exact paid generations needed

**Kling — 3 requests, 1080p, 3 s each, no automatic retry:** S02, S03, S06
- Rate used: **0.235 USD/s** (operator figure; fal's price API lists only 0.157 USD/s with no resolution tier, so the higher figure is used for safety).
- 3 s × 0.235 = **0.705 USD each → 2.115 USD** for all three.
- Option: S06 at 4 s (+0.235 → 2.350 USD) only if the unwrap needs it; decided at checkpoint 6.

**Keyframe images (OpenAI image edit, reference-conditioned) — 10 required:**
S01 · S02-start · S03-start · S04-A · S04-B · S05 · S06-start · S07-intact · S07-broken · S08
plus up to 6 retakes (identity / packaging failures) = at most 16 attempts.
Unit price is an **assumption of 0.09–0.15 USD per attempt** (Post 2 ledger: 11 requests = 0.997 USD ≈ 0.09 average; no price confirmed for 1080×1920 portrait). It is re-checked against the real usage block after the first image; I stop and report if it is higher.

| Scenario | Images | Kling | **Total** |
|---|---|---|---|
| Low (10 images @ 0.09, 3 × 3 s) | 0.90 | 2.115 | **≈ 3.0** |
| **Expected (13 images @ 0.11, 3 × 3 s)** | 1.43 | 2.115 | **≈ 3.55** |
| High (16 images @ 0.15, S06 at 4 s) | 2.40 | 2.350 | **≈ 4.75** |

Recommended authorization: **4.50 USD hard cap** — covers low and expected cases, and the high case only if S06 stays at 3 s (2.40 + 2.115 = 4.52, at the limit). Staged: Stage 1 keyframes (≈ 0.9–2.4 USD) → Stage 2 Kling (≈ 2.1–2.35 USD), one request at a time, each reviewed. No automatic retries; anything beyond the cap needs a new approval. **Not authorized yet.**

## 3. Audio — Version A: music + foley, no voiceover (no paid TTS)

Needed: bag zipper (S03), packaging rustle / wrapper (S02, S06), car door (S04), **wafer crunch (S07, hero)**, soft room tone, and one music bed (warm, minimal, ~90–100 BPM, ≥ 18 s).

**No audio files have been acquired yet.** Candidate sources — every file is recorded in `audio/AUDIO_LICENSE_LEDGER.csv` (URL, author, licence, access date, SHA-256) *before* use:
1. Freesound — **CC0 only** (filter) for foley.
2. Pixabay Content License (music + SFX) — licence page saved as evidence.
3. Fallback: locally synthesized foley (own work, no licence issue; lower realism) only if suitable licensed files cannot be found.

Not allowed: CC-BY-NC, "free for personal use", ripped or unattributed audio. Candidates are shown to you for approval before they go into the cut.

## 4. Continuity checks

See `qa/CONTINUITY_CHECKLIST.md` — woman, wafer packaging, duffle bag, car setting, hair/no wind, hands, framing, text and claims, safety. Gate: a keyframe that fails a MUST check is regenerated; a Kling clip that fails is **not retried automatically** — it is shown to you and you decide.

## 5. Approval checkpoints

1 ☐ storyboard + modes (this document) · 2 ☐ **budget ceiling** · 3 ☐ audio candidates · 4 ☐ keyframe batch 1 (S01, S02, S03, S06) · 5 ☐ keyframe batch 2 (S04, S05, S07, S08) · 6 ☐ each Kling clip, one at a time · 7 ☐ silent rough cut · 8 ☐ final with sound + copy/compliance read.
