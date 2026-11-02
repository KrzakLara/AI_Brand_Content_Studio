# Phase 5, Slide 1 cover proof: report (UNAPPROVED; plan hash 970975125494 unchanged, approval NONE)

**Files** (git-ignored, derived from brand-owned images, not for publication) in `runs/colla-pink/`:
- `cover_raw.png`: raw model output (1600x2000); its jar and label text are AI-drawn and DISCARDED.
- `cover_slide1_1080x1350.png`: final authentic-packaging composite with typography. `cover_nolettering_1080x1350.png`: same without type.
- `qa_cover_closeups.png`: 3x close-ups (raw left, final right) of lid and fingertips, both hands at the jar edge, base and thumbs, label text.
- `model_reference/`: face/hair/light crop, outfit/hands crop, full reference, README.
- `cover_fidelity.json`, `cover_registration.json`, `cover_canvas.png`, `cover_mask.png`, `cover_prompt.txt`.
Code: `plans/gymbeam_hr/phase5/cover_slide1.py`, `jar_matte.py`.

**Method.** The real Strawberry Lemonade packshot (sha256 `1fa5e11d...`) was cut out by a silhouette matte (the silver lid is nearly white, so a colour matte fails), placed on a blush canvas at chest height and protected by a mask. One mask edit (`gpt-image-2.5-sunburst`, xhigh, 1600x2000) painted the fictional woman, her hands, the studio, light and shadows. The model, as with the hero pouch, re-drew the jar slightly smaller (386 px against the 480 px placeholder) and garbled its label text, so the real jar was registered to the model's geometry by a UNIFORM scale and offset (label-band match, mean abs diff 5.8/255; scale 0.507 of the layer), relit by a smooth bounded gain (mean 1.01, 0.92 to 1.05) and laid on top. No stretching or perspective change.

**Cost.** One request, 0.141235 USD (1880 input and 4244 output tokens, request id `req_9b6d2bec...`). Phase 5 spent 0.141235 of 3.00 USD, remaining 2.858765. The audit log now has 5 lines (401, 429, 2 paid hero images, this cover); same ledger.db and usage file, nothing reset.

**Fidelity (measured).** Jar in the final is 261 x 299 px (uniform 0.342 of the packshot). CIE76 colour difference of the label region against the source: median 3.95, p95 6.3; label detail correlation 0.94 (lower than the hero's 0.99 only because of the 0.34x downscale and two-step resize). The printed text is the real packshot text and sharp at 1:1; no finger touches the logo, flavour name, ingredients or net weight. The jar is source-authentic but relit and downscaled, not pixel-identical.

**Hands.** Fingers wrap around the back and only fingertips and thumbs touch the left and right edges; no overlap in front of the jar, so the occlusion problem of slide 1 did not arise. Fallback composition (model beside the jar) was not needed.

**Unresolved visual defects**
1. A small notch (about 3 px) at the left base corner of the jar where the matte steps; the dark packshot base line was trimmed by 4 px to avoid a grey crescent, which slightly shortens the base.
2. The real base reads a little lighter than the model's ambient light under the chin; relighting is only a smooth gain.
3. The jar is relatively small in the frame (24% of the width) and the ingredient text is therefore tiny at feed size; slide 2 carries the readable information.
4. Faint model-skin texture is slightly over-smooth at the cheek (AI portrait); the face is a made-up person, not a real or recognisable one, but a resemblance to a real person cannot be ruled out and no check exists.
5. The headline block is close to the hair on the left; the three-line subtitle is small. Type is Playfair Display Bold/Regular (SIL OFL, `runs/colla-pink/font/OFL.txt`), burgundy #6e1f35; the font choice is mine and still needs your confirmation.
6. Model consistency for Slide 5 is NOT guaranteed.

**Brand evidence (existing research, no new research).** Concrete links: CreaGlow collaboration post https://www.instagram.com/p/DeuNpiTikK6/ (evidence `E-e73f15ab`, manual: pink layout, decorative serif/script title, creator holding the tub); Pink Collagen video https://www.instagram.com/p/DeMvee0DEpN/ (`E-87ecea41`, verified, 2026-10-07, also #pinkoctober); Anti-Aging Collagen morning-ritual video https://www.instagram.com/p/De18LcqEsNP/ (`E-3ee6b5ba`, verified, 2026-10-23). Your screenshots are user-provided inspiration, not independently verified Instagram URLs; nothing from them is reproduced and the model is not the CreaGlow creator.
