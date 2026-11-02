"""Phase 7D: add the usability files to submission/ (fonts, plan history, tools, REFERENCE_ASSETS). Local only; nothing is generated or downloaded.
Run before add_7b_files.py and finalize_submission.py."""
import hashlib
import json
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / "submission"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def put(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.chmod(0o666); dst.unlink()
    shutil.copy2(src, dst); dst.chmod(0o666)


def reference_assets():
    rows = []
    for x in json.loads((ROOT / "runs/gymbeam-wafer-reel/references/reference_ledger.json").read_text(encoding="utf-8")):
        rows.append({"use": "Reel: wafer / bag reference", "file": x["file"], "url": x["url"], "sha256": x["sha256"], "size": x.get("size")})
    assets = yaml.safe_load((ROOT / "plans/gymbeam_hr/phase5/colla_pink_assets.yaml").read_text(encoding="utf-8"))
    base = assets.get("source_base_url") or ""
    for f in assets["flavours"]:
        rows.append({"use": "Carousel: Colla Pink packshot", "file": f["file"], "url": f"{base}{f['file']}" if base else None, "sha256": f["sha256"], "note": "page https://gymbeam.hr/colla-pinkbeastpink.html"})
    rows.append({"use": "Tests (2 skipped without it): official creatine packshot", "file": "99543edff63b17e3.jpg (shop name creatine-monohydrate-unflavoured-01_8.jpg)", "url": "https://gymbeam.hr/media/catalog/product/cache/70f742f66feec18cb83790f14444a3d1/c/r/creatine-monohydrate-unflavoured-01_8.jpg",
                 "sha256": "99543edff63b17e355cd7bfcc734ef364ae81f08304e561e6a347c09e8954f1c",
                 "note": "place with `tools/place_packshot.py`; it also regenerates the derived cut-out (sha256 86613b3f58580bf96b4e3517095682da0842a4ba389b3e97db89eb50ce7023d8) locally, nothing else to download"})
    rows.append({"use": "Hero: official pouch photograph", "file": "creatine-monohydrate-unflavoured-lifestyle.png", "url": None,
                 "sha256": "cc19b0cd800dc8bd2fba06eec193335192d1e3ac02b601dd24098628e92358e0",
                 "note": "EXACT URL NOT RECORDED (only filename + hash). It is in the product gallery of https://gymbeam.hr/ (creatine monohydrate unflavoured); check any file you download against the hash"})
    rows.append({"use": "Hero/carousel: product page text", "file": "colla-pinkbeastpink_2026-10-28.html", "url": "https://gymbeam.hr/colla-pinkbeastpink.html",
                 "sha256": "79b0bb526d738372f4ab562513f421bcbb310a3c3da0d05eaec0a6f937d1e753", "note": "page changes over time; the hash is of the 2026-10-28 copy"})
    return rows, base


def main():
    for f in ("Montserrat.ttf", "Montserrat_OFL.txt"):
        put(ROOT / "runs/colla-pink/font" / f, SUB / "assets/fonts" / f)
    (SUB / "assets/fonts/README.md").write_text("# Fonts\n\nMontserrat (typography of the carousel, rebuilt locally by the post-production scripts) under the SIL Open Font License 1.1 (`Montserrat_OFL.txt`); redistribution with the scripts is permitted by that license. The scripts load it from `runs/colla-pink/font/Montserrat.ttf`; `tools/bootstrap_workspace.py` puts it there.\n", encoding="utf-8")
    hist = ROOT / "plans/gymbeam_hr/history"
    for p in hist.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            put(p, SUB / "phases/02_plan/history" / p.relative_to(hist))
    for n in ("bootstrap_workspace.py", "verify_hashes.py", "verify_fresh_extraction.py", "place_packshot.py"):
        put(ROOT / "plans/gymbeam_hr/phase7" / n, SUB / "tools" / n)
    rows, base = reference_assets()
    (SUB / "assets/reference_assets.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    md = ["# Official reference photographs NOT included in this package",
          "",
          "GymBeam's photographs are brand-owned and are deliberately not redistributed. **No script downloads them for you and none is needed** for the deterministic local rebuilds (V4, slide 3, slide 5, cover B), which use only the raw generated clips and stills that are in `phases/`.",
          "They are needed only to repeat the **paid generation** steps (hero, carousel stills, reel keyframes). Retrieval is manual: open the page, save the image, check the SHA-256 below, put the file where the script expects it (see the script header; the original layout is `runs/gymbeam-wafer-reel/references/`, `runs/colla-pink/source/`, `runs/hero-proof/source/`).",
          "Recorded 2026-10-27..29. Product images on the shop change; a different hash means a different image, not a corrupt download. Permission to publish derived media has not been obtained (see `FINAL_READINESS_REPORT.md`).",
          "",
          "| Use | File | Official URL | SHA-256 | Size / note |", "|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['use']} | `{r['file']}` | {r['url'] or '**not recorded**'} | `{r['sha256']}` | {r.get('size') or ''} {r.get('note') or ''} |")
    md += ["", "Other recorded, brand-sourced inputs: Instagram posts of @gymbeamhr (collected with Apify, `phases/01_research/`), product page facts (`research/imports/*.yaml` in `ai_recipe/repo/`).",
           "Not obtained at all: official logo asset, licensed music (see readiness report)."]
    (SUB / "REFERENCE_ASSETS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("update_7d done;", len(rows), "reference rows")


if __name__ == "__main__":
    main()
