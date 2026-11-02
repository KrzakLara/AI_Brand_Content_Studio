# Wafer-snap prototype report (local, zero cost; V4 not modified)

## What the real wafer looks like (official gallery, 1200×1200)
Golden, **uncoated** rectangular wafer with a pronounced diamond/waffle grid on top; inside, 3 wafer sheets alternating with **dark-brown nougat cream** and **white cream**; hazelnut pieces only on the wrapper illustration. It breaks along a diagonal into angular pieces with exposed layers and a few crumbs (photo `0002_8`).

## Existing S07 assets vs. the real product
S07a/S07b (generated) show a **chocolate-coated bar with a bumpy, rough surface and no waffle grid**. The layer cross-section is roughly right (wafer/cream alternation), but the outer look is a different product. **Verdict: inaccurate — must not be used.** (See `qa/V5_SOURCE_COMPARISON.png`.)

## Prototypes (`prototypes/`, 2.0 s each, 1080×1920, 24 fps, with synthetic crunch at 0.83 s, 2-frame flash, procedural crumbs)
- **A — `SNAP_PROTOTYPE_A_official_photos_match_cut.mp4`**: hard cut between two *unaltered* official photos (wafer sliding out of the wrapper → wafer broken in three), centred to match. Product accuracy: **100% real wafer**. Problems: lime-green catalog backdrop breaks the beige reel look; neighbouring packs and hazelnuts intrude; the "intact" frame shows a wafer half inside its wrapper and the "broken" frame is a *different* wafer in a different pose, so it reads as two product photos, not one wafer snapping; photos are 1200 px, upscaled ~1.6× (soft).
- **B — `SNAP_PROTOTYPE_B_composite_on_counter.mp4`**: real pieces keyed out of the photos and composited onto our blurred kitchen counter. Problems: faint green fringe on edges, **no believable contact shadow (objects float)**, flash-lit studio light ≠ our daylight, the intact/broken pieces still come from different photos, the backdrop is a blurred crop that does not form a real scene. **Looks artificial.**

## Recommendation: keep V4 unchanged
No existing asset can show **one real wafer being broken**: the only intact-wafer picture has it half inside its wrapper, and the only broken-wafer picture is a different wafer. A convincing snap needs a new picture/clip of a real wafer in hands, which is outside "existing assets only". If you want a break shot anyway, **A is the only honest option** (as a 2-second product cutaway between car and gym), accepting its green catalog look — I do not recommend it.

## Cost
No API requests (images 15 / Kling 4, unchanged; 1.401 + 2.82 USD).
