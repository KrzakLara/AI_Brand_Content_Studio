# Objava 3 – GymBeam 32% Protein Wafer, lifestyle Reel „Moj mali gym essential"

[<img src="reel-cover-9x16.png" width="320" alt="Naslovnica Reela: žena u kuhinji drži GymBeam Protein Wafer, uz šalicu kave i crnu GymBeam torbu">](protein-wafer-reel.mp4)

**▶ [Pogledaj Reel: `protein-wafer-reel.mp4`](protein-wafer-reel.mp4)** (8,5 MB; ako se video ne reproducira u pregledniku, koristi *View raw* ili *Download*)

| | |
|---|---|
| Format | Instagram Reel 9:16, **1080 × 1920 px**, MP4 H.264 + AAC stereo 44,1 kHz, 24 fps, **8,83 s (212 frameova)**. Finalna isporučena verzija **V8**. |
| Naslovnica | [`reel-cover-9x16.png`](reel-cover-9x16.png) (opcija B, odabrala autorica) i [prikaz u mreži profila 4:5](reel-cover-grid-4x5.png) |
| Tekst na ekranu | MALI RITUALI U POKRETU. (0–1,5 s) |
| Zvuk | bez glazbe i glasa; vrlo tih sintetizirani foley |

## Što prikazuje
Kratka UGC priča „kuhinja → torba → auto → teretana". Wafer je glavni proizvod, a torba GymBeam Urban Duffle sporedni. Montaža je namjerno u rough-cut stilu, kao kreativna odluka autorice inspirirana TikTok i UGC estetikom.

| Vrijeme | Kadar |
|---|---|
| 0,00–1,50 s | wafer, torba, šalica i ključevi na kuhinjskom pultu, uz tekst |
| 1,50–2,83 s | uzima wafer i podiže ga sa smiješkom |
| 2,83–5,29 s | spušta wafer u otvorenu crnu GymBeam torbu |
| 5,29–6,88 s | u parkiranom autu, otvara omot |
| 6,88–8,83 s | ulazi u teretanu |

## Kako je nastao
- **Keyframeovi:** 14 keyframeova generirano je s `gpt-image-2.5-sunburst` prema službenim fotografijama wafera i torbe.
- **Video:** 5 Kling v4 image-to-video klipova (fal.ai) od 3 s.
- **Montaža, zvuk i naslovnica:** deterministične Python i FFmpeg skripte; ponovno sastavljanje daje identične dekodirane frameove.
- **Verzije:** V4–V7 su odbijene ili zamijenjene (npr. V4 zbog deformirane ručke torbe). Za V8 je generiran jedan novi keyframe i jedan Kling klip. V8 je autorica odabrala vizualnim pregledom.
- Skripte i QA: [`plans/gymbeam_hr/phase6/reel/`](../../plans/gymbeam_hr/phase6/reel/) (konačna montaža: `assemble_reel_v8_candidate.py`)

## Opis (caption)
> Od jutarnjih obveza do treninga — neke sitnice jednostavno uvijek idu sa mnom. 🤎
>
> GymBeam 32% Protein Wafer.
>
> Zamišljeni portfolio oglas (AI-generirani sadržaj) — nije službena suradnja s GymBeamom ni stvarna preporuka influencera.
>
> #gymbeamhr #gbfit #ProteinWafer

## Poznata ograničenja
Pri rezu u kadar s torbom postoji skok kontinuiteta, lice blago varira između kadrova, a u kadru teretane cipela je zamućena. Sitni tekst na omotu je mekši u pokretu. Pakiranje i torba u videu su AI renderi prema službenim fotografijama, ne pikseli s fotografije.

*Prava i ograničenja korištenja: [README → Prava na medije](../../README.md#prava-na-medije).*
