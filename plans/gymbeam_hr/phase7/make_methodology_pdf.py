"""Methodology PDF (Croatian, exactly 2 pages) -> submission/methodology/METODOLOGIJA_HR.pdf. Local only. Phase 7A, rewritten in Phase 7F (V8 Reel, S03B, slide 3/5/6 corrections, costs, paths).
Run from anywhere; set PDF_OUT to write somewhere else (e.g. the review package)."""
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(os.environ.get("PDF_OUT") or ROOT / "submission/methodology/METODOLOGIJA_HR.pdf"); OUT.parent.mkdir(parents=True, exist_ok=True)
for n, f in (("A", "arial.ttf"), ("A-B", "arialbd.ttf"), ("A-I", "ariali.ttf")):
    pdfmetrics.registerFont(TTFont(n, f"C:/Windows/Fonts/{f}"))
pdfmetrics.registerFontFamily("A", normal="A", bold="A-B", italic="A-I", boldItalic="A-B")
BURG = colors.HexColor("#7F2944")
H1 = ParagraphStyle("h1", fontName="A-B", fontSize=15, leading=18, textColor=BURG, spaceAfter=1)
SUB = ParagraphStyle("sub", fontName="A", fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"), spaceAfter=3)
H2 = ParagraphStyle("h2", fontName="A-B", fontSize=10, leading=12.2, textColor=BURG, spaceBefore=5, spaceAfter=2)
B = ParagraphStyle("b", fontName="A", fontSize=8.4, leading=10.8, alignment=TA_LEFT, spaceAfter=1.5)
BL = ParagraphStyle("bl", parent=B, leftIndent=8, bulletIndent=0)
TC = ParagraphStyle("tc", fontName="A", fontSize=7.7, leading=9.4)
CODE = ParagraphStyle("code", fontName="Courier", fontSize=7.1, leading=8.5, leftIndent=6, textColor=colors.HexColor("#222222"))
TH = ParagraphStyle("th", fontName="A-B", fontSize=7.7, leading=9.4, textColor=colors.white)


def tbl(rows, widths, head=True):
    data = [[Paragraph(str(c), TH if (head and i == 0) else TC) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c9b8bd")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
          ("LEFTPADDING", (0, 0), (-1, -1), 2.6), ("RIGHTPADDING", (0, 0), (-1, -1), 2.6)]
    if head:
        st.append(("BACKGROUND", (0, 0), (-1, 0), BURG))
    t.setStyle(TableStyle(st)); return t


def bl(txt):
    return Paragraph(txt, BL, bulletText="•")


S = []
S += [Paragraph("AI Brand Content Studio — metodologija i izvedena proizvodnja", H1),
      Paragraph("GymBeam (@gymbeamhr) · tri Instagram objave · 27. 10. – 1. 11. 2026. · zadatak za Sekvencu (Full-Stack Developer – AI Products)", SUB)]
S += [Paragraph("1. Cilj, odabir marke i kategorija", H2),
      Paragraph("Cilj: tri različite objave u kontroliranom, provjerljivom postupku uz ljudsko odobrenje: <b>hero fotografija</b> (100% Kreatin Monohidrat), <b>karusel</b> BeastPink Colla Pink (4 fotografije + 2 videa) i <b>Reel</b> s GymBeam 32% Protein Wafer vaflom i torbom Urban Duffle. "
                "Sve je zamišljeni portfolio rad: osobe su fiktivne (generirane umjetnom inteligencijom), ne radi se o službenoj suradnji s GymBeamom niti je išta pravno odobreno za javno oglašavanje.", B),
      bl("<b>Zašto GymBeam:</b> GymBeam je europski brend slovačkog podrijetla, s hrvatskom internetskom trgovinom gymbeam.hr i Instagram profilom @gymbeamhr. Odabran je zbog prepoznatljivog vizualnog identiteta, širokog asortimana proizvoda i aktivne prisutnosti na društvenim mrežama; javni profil (30 prikupljenih objava) i službene stranice proizvoda omogućuju istraživanje temeljeno na provjerljivim izvorima."),
      bl("<b>Zašto tri kategorije:</b> odabirom triju kategorija proizvoda — kreatina, BeastPink Colla Pink i proteinskog wafera — demonstrirana je primjenjivost istog AI postupka na različite formate i kreativne pristupe: <b>premium oglas proizvoda</b> (statični hero), <b>edukativni lifestyle karusel</b> i <b>kratki lifestyle Reel inspiriran UGC-om</b>. Izvorni brief bio je samo za kreatin; razvoj do konačnog opsega: <i>phases/02_plan/FINAL_SCOPE_REVISION_7F.md</i>.")]
S += [Paragraph("2. Pristup", H2),
      Paragraph("Tijek: <b>istraživanje</b> (web i Instagram) → <b>analiza brenda</b> → <b>plan</b> (JSON, shema CampaignPlan/2) → <b>produkcija</b> → <b>QA</b> → <b>ljudsko odobrenje</b> → izvoz. Načela:", B),
      bl("<b>Dokazi prije tvrdnji:</b> svaka brojka ima izvor sa službene stranice; tvrdnje o učinku tek uz provjerenu formulaciju (slajd 5: cink, Uredba (EU) 432/2012); status odobrenja izvornog plana u alatu je NONE (povijesno); isporučeno je dokumentirano u R9."),
      bl("<b>Stvarni proizvod:</b> pakiranja iz službenih fotografija (izrez, relight, kod) ili rendera uspoređenih s referencama; vidljivi tekst (Montserrat, Inter; SIL OFL) dodaje se kodom na svakom frameu, ne generira ga model."),
      bl("<b>Zaštita troška:</b> adapter s tvrdim proračunom, ograničenjem zahtjeva, bez automatskih ponavljanja, zapis prije slanja; ključevi se ne zapisuju."),
      bl("<b>Ljudski nadzor:</b> proizvode, naslove i verzije odabirala je autorica (Lara) i više puta odbacila ono što je strojni QA propustio. Opise je predložio model, uredila autorica; lektura izvornog govornika nije provedena.")]
S += [Paragraph("3. Faze i izlazi", H2),
      tbl([["Faza", "Što je napravljeno", "Rezultat"],
           ["1–3", "LangGraph kostur s mock pružateljima; istraživanje: agent Claude Haiku 5.5 (1. pokus neuspješan, 2. uspješan), 30 objava; plan: Claude Sonnet 5.5 + 1 revizija + ljudske izmjene", "baza dokaza, plan (bez odobrenja)"],
           ["4 Hero", "pravo pakiranje iz foto-izreza + generirana scena i čaša; V1–V5", "Post 1 (V5)"],
           ["5 Karusel", "naslovnica, slajdovi 2, 4, 6; videa slajdova 3 i 5 (Kling); tekst u postprodukciji", "Post 2 (6 slajdova)"],
           ["6 Reel", "13 keyframeova, 4 Kling klipa, V1–V4; zatim V5–V7 (odbačeni kandidati bez troška) i <b>V8</b>: 1 novi keyframe (S03B) + 1 Kling klip od 3 s za scenu spremanja vafla u torbu", "Post 3: <b>V8, 8,83 s</b>"],
           ["7A–7F Paket", "provjerene kopije (SHA-256), recept, testovi; 7F: slajd 3 v3, slajd 5 v4, slajd 6 v2, opisi, alt tekst, R9, ovaj PDF", "ovaj paket"]],
          [20, 118, 40])]
S += [Paragraph("4. Modeli, alati, promptovi i kod", H2),
      tbl([["Namjena", "Alat (kako je izvedeno)"],
           ["Istraživanje / plan", "Anthropic claude-haiku-5-5 (agent), claude-sonnet-5-5 (plan, effort medium)"],
           ["Slike", "OpenAI gpt-image-2.5-sunburst, xhigh, uređivanje s referentnim slikama (1152×2048 / 1600×2000)"],
           ["Video", "fal.ai Kling v4 image-to-video, 1080p, 3–5 s; tekst dodan u postprodukciji"],
           ["Lokalno", "Python, Pillow, NumPy, OpenCV, FFmpeg, proceduralni zvuk; deterministične skripte. Pravi promptovi i kod: <i>ai_recipe/prompts/</i>, <i>ai_recipe/AI_RECIPE.md</i>, <i>ai_recipe/code/</i>"]],
          [30, 148])]
S += [Paragraph("5. Kontrola kvalitete: odbacivanja i ispravci", H2),
      bl("<b>Primjer ispravka AI izlaza (Reel):</b> u kadru spremanja vafla u torbu ručka torbe imala je samo jedan oslonac i spajala se s prstima (V4 odbijen). Lokalno popravljanje nije bilo moguće bez izmišljanja geometrije, pa je <b>jednom</b> generiran novi keyframe iz službenih fotografija torbe (prednja ručka spuštena, oba kraja pričvršćena, stražnja ručka nije vidljiva; 0,12 USD), pregledan u punoj rezoluciji, i tek tada jedan Kling klip (0,705 USD). Šalica koja se u 17. frameu prije klipa S02 „preskoči” izbačena je rezom, ne retušem."),
      bl("<b>Kreativna odluka (Reel V8):</b> „Za treću objavu namjerno sam odabrala rough-cut stil montaže, inspiriran aktualnom TikTok i UGC estetikom. Izraženiji rezovi između kadrova kreativna su odluka kojom se nastoji postići spontaniji, autentičniji dojam sadržaja, uz jasnu priču i vidljivost proizvoda.” Stil montaže <b>nije opravdanje</b> za vizualne nedostatke AI materijala; oni su navedeni u odjeljku 7."),
      bl("<b>Karusel:</b> slajd 3 v3 – podnaslov smanjen da žlica ne prekriva tekst (isti video); slajd 5 v4 – tvrdnja o cinku prema tri zasebno odobrene tvrdnje (kosa, nokti, koža); slajd 6 v2 – lokalni retuš triju potvrđenih artefakata. Hero i naslovnica: odbačeni pokušaji, ciljane izmjene.")]
S += [KeepTogether([Paragraph("6. Trošak i vrijeme: stvarno naspram procijenjeno", H2),
      tbl([["Stavka", "Potvrđeno USD", "Procjena USD", "Osnova"],
           ["Tekstualni modeli (istraživanje + plan)", "0,53", "–", "zapisi o korištenju (usage)"],
           ["Slike (hero, karusel, Reel; uklj. S03B 0,115665)", "2,80", "–", "zapisi o korištenju (1,28 + 1,40 + 0,12)"],
           ["Kling (slajd 3: 5 s; slajd 5: 2 × 5 s; Reel: 4 × 3 s + S03B 3 s)", "–", "7,06", "PROCJENA 0,235 USD/s (dala Lara; zapisana stopa); <b>račun davatelja nije provjeren</b>, S03B 0,705 također procjena"],
           ["<b>Ukupno</b>", "<b>≈ 3,33</b>", "<b>≈ 7,06</b>", "<b>≈ 10,39 USD</b>; Apify nije raspisan; faze 7B, 7C, 7E, 7F bez novih zahtjeva"]],
          [66, 22, 22, 68])]),
      Spacer(1, 2),
      tbl([["Vrijeme", "Vrijednost", "Status i osnova"],
           ["Kalendarski raspon (nije radno vrijeme)", "27. 10. – 1. 11. 2026.", "izmjereno do 29. 10. 19:02 UTC ≈ 48 h (7 sesija); kasnije sesije nisu mjerene"],
           ["<b>Aktivni rad autorice</b> (pregled, odluke, upute, odobrenja)", "<b>10–12 h</b>", "PROCJENA autorice, izričito potvrđena; nije izmjereno. Odvojeno od vremena stroja i od kalendarskog raspona"],
           ["Kontrola iz zapisa sesija (do faze 7D)", "≈ 9,7 h ljudsko · ≈ 8,0 h strojno", "PROCJENA iz vremenskih oznaka (razmak najviše 30 min); ne uključuje 7E–7F; služi samo kao provjera reda veličine"],
           ["AI generiranje i čekanje API-ja", "nije zasebno izmjereno", "trajanja poziva dobavljača nisu zapisana; izmjeren je samo poziv agenta za istraživanje ≈ 14 s; troškovi su u tablici iznad"],
           ["Automatska obrada i testiranje", "zapisano samo za provjeru ZIP-a", "potpuna provjera iz svježe ekstrakcije (7F): hash 5 s, bootstrap 5 s, venv 13 s, pip 63 s, pytest 119 s, mock 4 s, smoke testovi 244 s ≈ 7,5 min (zapisnik); trajanja lokalnih montaža nisu mjerena"]],
          [46, 38, 94]),
      Paragraph("Procjena autorice (10–12 h aktivnog rada) <b>ne zbraja se</b> s vremenom stroja ni s kalendarskim rasponom. Vrijeme AI generiranja, automatske obrade, testiranja i čekanja vodi se zasebno i ne izmišlja se tamo gdje nije zapisano.", B)]
S += [Paragraph("7. Ograničenja i otvorena pitanja", H2),
      bl("<b>Odobrenja:</b> izvorni plan u alatu ima status odobrenja NONE (povijesno); Reel (vafl) zamjenjuje planirani „Klik prije izlaska” odlukom autorice (R9: <i>phases/02_plan/CONTENT_PLAN_FINAL_REVISION.md</i>, izvorni plan sačuvan, hash 970975125494…). Status: <b>autorica je 1. 11. 2026. osobno pregledala i prihvatila završne objave, videe i zvuk Reela, opise i plan R9 za privatnu demonstraciju zadatka (Sekvenca) — samo portfolio demonstracija; NIJE odobreno za javno komercijalno oglašavanje bez dodatnih prava i pregleda usklađenosti</b> (prava na fotografije brenda, pravni pregled tvrdnji, lektura); odobrenje marke ili pravnog tima nije tražen niti se tvrdi (<i>FINAL_SIGNOFF_7F.md</i>)."),
      bl("<b>Vjernost proizvoda i pokret:</b> pakiranja i torba su AI renderi iz referenci od 700 px; sitni tekst na omotu je mekan u pokretu; u V8 je preostalo zamućenje stopala u kadru teretane, skok kontinuiteta torbe pri rezu iz kuhinje u scenu spremanja te blago različito lice po kadrovima; zvuk je sintetiziran (autorica ga je pregledala i prihvatila); AI-renderirana pakiranja u videu dokumentirano su odstupanje od izvornog pravila „ne generirati pakiranje”, ne dokaz točnosti."),
      bl("<b>Usklađenost:</b> slajd 5 koristi tri odobrena iskaza o cinku (Uredba 432/2012, hrvatski tekst) uz opći tekst „Napitak za ljepotu / Ljepota počinje iznutra.”; cjelokupan oglas nije pravno očišćen; stranica proizvoda ima neusklađene podatke (FAQ navodi maksimalno 18 g dnevno, doziranje 1 mjerica = 8 g)."),
      bl("<b>Reproducibilnost:</b> montaže (V4, V8, slajd 3 v3, slajd 5 v4, slajd 6 v2, naslovnica B) provjerene su identičnim dekodiranim frameovima; plaćeni koraci (agent, plan, slike, Kling) nisu ponovljivi bit po bit i nisu ponovno pokretani."),
      bl("<b>Što može varirati pri ponovnom izvođenju:</b> Pri ponovnom AI generiranju mogu varirati scene, izgled generiranih osoba, pokreti i kadrovi videa. Identitet odabranih proizvoda, službene reference, planirani tekstovi i tipografija definirani su receptom, dok se rezultat provjerava istim QA pravilima. Ponovno sastavljanje iz arhiviranih odobrenih materijala reproducibilno je, ali novi generativni pozivi ne jamče identične rezultate.")]
S += [Paragraph("8. Gdje je što i kako pokrenuti (bez API ključeva)", H2),
      Paragraph("<b>U paketu:</b> brief <i>ai_recipe/repo/briefs/gymbeam_hr.yaml</i>, <i>phases/02_plan/gymbeam_hr_canonical_brief.yaml</i> · istraživanje i reference <i>phases/01_research/</i>, <i>REFERENCE_ASSETS.md</i> · plan R9 <i>phases/02_plan/</i> (uklj. <i>FINAL_SCOPE_REVISION_7F.md</i>) · prompti i kod <i>ai_recipe/</i> · završni mediji i opisi <i>posts/</i> · usklađenost i alt tekst <i>compliance/</i> · hashevi <i>SHA256SUMS.txt</i>, <i>SUBMISSION_MANIFEST.json</i>.", B),
      Paragraph("<b>Windows 10/11 (provjereno), PowerShell, Python 3.12</b> (testirano i 3.14), <i>py</i>; internet samo za <i>pip</i>; ZIP na kratku putanju (npr. C:/work/pkg). .env treba samo za plaćene korake, čiji su limiti potrošeni. <b>macOS/Linux: NEPROVJERENO</b> – isti koraci uz python3 i kosu crtu u putanjama; skripte nisu na njima testirane.", B)]
for c in ("cd C:/work/pkg/submission",
          "py tools/verify_hashes.py                              # SHA-256 svih datoteka",
          "py tools/bootstrap_workspace.py --target C:/work/ws    # vraca raspored mapa",
          "cd C:/work/ws ; py -3.12 -m venv .venv ; ./.venv/Scripts/python.exe -m pip install -e '.[dev,media]'",
          "./.venv/Scripts/python.exe -m pytest                   # testovi",
          "$env:STUDIO_NO_DOTENV='1'; ./.venv/Scripts/studio.exe run --mock --run demo --export-dir $env:TEMP/mock_out",
          "$env:SUBMISSION_DIR='C:/work/pkg/submission'; ./.venv/Scripts/python.exe plans/gymbeam_hr/phase7/smoke_tests.py"):
    S.append(Paragraph(c.replace("&", "&amp;"), CODE))
S += [Paragraph("9. Daljnje unapređenje: učenje iz povratnih informacija (PRIJEDLOG — <u>nije implementirano</u>)", H2),
      Paragraph("Ovaj rad <b>ne sadrži</b> učenje iz povratnih informacija ni dohvat metrika. Prijedlog: (1) svako ljudsko odobrenje/odbijanje bilježi se strukturirano (objava, verzija, hash, odluka, razlog); (2) rezultati objava – komentari, spremanja, dijeljenja, doseg, klikovi i konverzije gdje postoje – povezuju se s planom i verzijom prompta; "
                "(3) odbijanja i metrike sažimaju se u „lekcije” kao ulaz agentu za plan, a svaka promjena prompta je nova verzija, prikazana kao usporedba i odobrena od čovjeka; "
                "(4) <b>mjerenje:</b> usporedba s ranijim usporedivim sadržajem (isti format, proizvod, kategorija), normalizirano po dosegu i vremenu objave, uz oznaku nepouzdanosti za male uzorke te usporedbu verzija i provjeru usklađenosti s brendom; jedna objava nikad ne mijenja prompt automatski; ljudsko odobrenje marke i usklađenosti ostaje obavezno.", B)]
doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=11 * mm, title="AI Brand Content Studio — metodologija", author="Lara (projekt), Claude Code (izvedba)")
doc.build(S)
print(OUT)
