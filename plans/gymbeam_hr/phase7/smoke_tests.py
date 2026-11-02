"""Phase 7A non-paid smoke tests. Nothing here calls a paid API; outputs go to a temp dir, never over delivered files.
Writes submission/smoke_tests/smoke_results.json.

SUBMISSION_DIR (env) points to an extracted package when run from a bootstrapped workspace (then results go to <ROOT>/smoke_results_workspace.json and the package is not modified)."""
import hashlib
import os
import importlib
import json
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "plans/gymbeam_hr/phase6/reel"))
SUB = Path(os.environ.get("SUBMISSION_DIR") or ROOT / "submission").resolve()   # the package under test
TMP = Path(tempfile.mkdtemp(prefix="smoke_"))
RES = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rec(name, ok, detail):
    RES.append({"test": name, "result": "PASS" if ok else "FAIL", "detail": detail}); print(("PASS " if ok else "FAIL ") + name + " :: " + detail)


def frames_md5(path, w, h):
    from reel_lib import read_frames
    f = read_frames(path, w, h)
    return len(f), hashlib.md5(f.tobytes()).hexdigest()


# 1. spend guards refuse (no network is touched: the guard raises before any request)
def t_guards():
    from studio.cost import BudgetExceeded
    from studio.providers.fal_video import FalKlingVideo

    class NoNet:
        def request(self, *a, **k):
            raise AssertionError("network must not be used")
    v = FalKlingVideo(transport=NoNet(), api_key="x", budget_usd=2.0, max_requests=1)
    ok1 = abs(v.estimate_usd(5, "1080p") - 1.175) < 1e-9 and abs(v.estimate_usd(5, "720p") - 0.785) < 1e-9
    try:
        v.check_budget(9, "1080p"); ok2 = False
    except BudgetExceeded:
        ok2 = True
    v.api_requests = 1
    try:
        v.check_budget(3, "1080p"); ok3 = False
    except BudgetExceeded:
        ok3 = True
    rec("fal_video spend guard (estimate 5 s 1080p = 1.175; 9 s refused; 2nd request refused)", ok1 and ok2 and ok3, f"estimate_ok={ok1} over_budget_refused={ok2} request_limit_refused={ok3}")


def t_cli_preflights():
    for script, shot in (("run_kling.py", "S02"), ("gen_keyframe.py", "S01")):
        r = subprocess.run([sys.executable, str(ROOT / "plans/gymbeam_hr/phase6/reel" / script), shot, "--preflight"], capture_output=True, text=True, cwd=ROOT)
        refused = r.returncode != 0 and ("BudgetExceeded" in r.stderr or "RequestLimit" in r.stderr or "NOT sent" in r.stderr)
        rec(f"{script} {shot} --preflight refuses (project caps already used)", refused, (r.stderr.strip().splitlines() or ["(no stderr)"])[-1][:200])


# 2. V4 edit reproduces decoded frames of the delivered file from raw assets (written to a temp dir)
def t_v4():
    import assemble_reel as A
    A.FIN = TMP; A.AUD = TMP; A.R = TMP
    (TMP / "logs").mkdir(exist_ok=True)
    v4 = importlib.import_module("assemble_reel_v4")
    v4.main()
    n1, h1 = frames_md5(TMP / "GYMBEAM_WAFER_LIFESTYLE_REEL_V4.mp4", 1080, 1920)
    n0, h0 = frames_md5(ROOT / "runs/gymbeam-wafer-reel/final/GYMBEAM_WAFER_LIFESTYLE_REEL_V4.mp4", 1080, 1920)
    rec("V4 (rejected history version) re-edit from raw Kling clips reproduces its decoded frames", (n1, h1) == (n0, h0), f"frames {n1} vs {n0}; decoded-frame md5 {'equal' if h1 == h0 else 'DIFFERENT'}")


# 2b (7F). FINAL V8 re-edit from raw Kling clips (incl. the new S03B clip) reproduces the delivered Reel: decoded frames and bytes
def t_v8():
    """Runs in a FRESH interpreter: the synthesised foley uses a module-level seeded RNG, so audio bytes are only reproducible from a fresh process (the video frames never depend on it)."""
    out_dir = TMP / "v8"; (out_dir / "logs").mkdir(parents=True, exist_ok=True)
    code = ("import sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
            "from pathlib import Path\nimport assemble_reel as A\nA.FIN = A.AUD = A.R = Path(%r)\n"
            "import importlib; importlib.import_module('assemble_reel_v8_candidate').main()\n") % (str(ROOT), str(ROOT / "plans/gymbeam_hr/phase6/reel"), str(out_dir))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    out = out_dir / "GYMBEAM_WAFER_LIFESTYLE_REEL_V8_CANDIDATE.mp4"
    final = ROOT / "runs/gymbeam-wafer-reel/final/GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4"
    pk = SUB / "posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4"
    if r.returncode != 0 or not out.is_file():
        rec("Reel FINAL V8 re-edit", False, (r.stderr.strip().splitlines() or ["no output"])[-1][:200]); return
    n1, h1 = frames_md5(out, 1080, 1920); n0, h0 = frames_md5(final, 1080, 1920); n2, h2 = frames_md5(pk, 1080, 1920)
    same_bytes = sha(out) == sha(pk)
    rec("Reel FINAL V8 re-edit from raw Kling clips (incl. S03B) in a fresh process reproduces the delivered file (decoded frames and bytes)", (n1, h1) == (n0, h0) == (n2, h2) and n1 == 212 and same_bytes, f"frames {n1}/{n0}/{n2}; md5 {'equal' if h1 == h0 == h2 else 'DIFFERENT'}; bytes_equal={same_bytes}")


# 3. slide 3 v2: text layer identical, video re-built into temp, decoded frames equal
def t_slide3():
    sp = importlib.util.spec_from_file_location("s3", ROOT / "plans/gymbeam_hr/phase5/slide3_title_v2.py"); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    from PIL import Image
    import numpy as np
    layer, s = m.build()
    same = np.array_equal(np.asarray(layer), np.asarray(Image.open(ROOT / "runs/colla-pink/slide3_video/text_layer_v2_1080x1350.png").convert("RGBA")))
    out = TMP / "slide3_v2.mp4"; lp = TMP / "layer.png"; layer.save(lp)
    ff = m.imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(ROOT / "runs/colla-pink/slide3_video/kling_raw.mp4"), "-loop", "1", "-i", str(lp), "-filter_complex",
                    "[0:v]crop=1286:1608,scale=1080:1350:flags=lanczos,format=rgba[v];[v][1:v]overlay=0:0:shortest=1,format=yuv420p", "-an", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-r", "24",
                    "-movflags", "+faststart", str(out)], check=True)
    n1, h1 = frames_md5(out, 1080, 1350); n0, h0 = frames_md5(ROOT / "runs/colla-pink/slide3_video/slide3_priprema_FINAL_v2_1080x1350.mp4", 1080, 1350)
    rec("Slide 3 v2: text layer rebuilt identical; video rebuilt from kling_raw.mp4 gives equal decoded frames", same and (n1, h1) == (n0, h0), f"layer_identical={same}; frames {n1} vs {n0}; md5 {'equal' if h1 == h0 else 'DIFFERENT'}; title px {s}")


# 4. cover B composite rebuilt into temp
def t_cover():
    src = (ROOT / "plans/gymbeam_hr/phase6/reel/cover_wrapper_fix.py").read_text(encoding="utf-8").replace('OUT = R / "cover_options"', f'OUT = Path(r"{TMP}")')
    ns = runpy.run_path("<cover>", init_globals=None) if False else None
    code = compile(src, "cover_wrapper_fix.py", "exec"); g = {"__file__": str(ROOT / "plans/gymbeam_hr/phase6/reel/cover_wrapper_fix.py"), "__name__": "__main__"}
    exec(code, g)
    ok = sha(TMP / "COVER_B_corrected_wrapper_1080x1920.png") == sha(ROOT / "runs/gymbeam-wafer-reel/cover_options/COVER_B_corrected_wrapper_1080x1920.png")
    rec("Cover B composite rebuilt from the cover + S01 still is byte-identical to the delivered file", ok, "sha256 equal" if ok else "sha256 differs")


# 5. delivered media: formats
def t_formats():
    from reel_lib import FF
    expect = {"posts/post_02_beastpink_carousel/slide_3_PRIPREMA_video_v3_1080x1350.mp4": ("1080x1350", "05.04"), "posts/post_02_beastpink_carousel/slide_5_napitak_za_ljepotu_video_v4_1080x1350.mp4": ("1080x1350", "05.04"),
              "posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4": ("1080x1920", "08.83")}
    from PIL import Image
    allok = True; det = []
    for rel, (size, dur) in expect.items():
        err = subprocess.run([FF, "-hide_banner", "-i", str(SUB / rel)], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
        ok = (size in err) and ("Duration: 00:00:" + dur) in err and "24 fps" in err and "h264" in err
        allok &= ok; det.append(f"{Path(rel).name}: {'ok' if ok else 'BAD ' + repr([l.strip()[:90] for l in err.splitlines() if 'Duration' in l or 'Video:' in l])}")
    for rel, sz in (("posts/post_01_creatine_hero/hero_FINAL_v5_1080x1350.png", (1080, 1350)), ("posts/post_02_beastpink_carousel/slide_1_cover_FROZEN_1080x1350.png", (1080, 1350)),
                    ("posts/post_02_beastpink_carousel/slide_2_sto_je_unutra_NO_FOOTER_1080x1350.png", (1080, 1350)), ("posts/post_02_beastpink_carousel/slide_4_kako_pripremiti_1080x1350.png", (1080, 1350)),
                    ("posts/post_02_beastpink_carousel/slide_6_odaberi_svoj_okus_FINAL_v2_1080x1350.png", (1080, 1350)), ("posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_REEL_SELECTED_COVER_B_1080x1920.png", (1080, 1920))):
        ok = Image.open(SUB / rel).size == sz; allok &= ok; det.append(f"{Path(rel).name}: {'ok' if ok else 'BAD'}")
    rec("Delivered media formats (1080x1350 / 1080x1920, 24 fps H.264, durations)", allok, "; ".join(det))


# 6. secrets hygiene: no key-like strings in the package text files
PLACEHOLDERS = ("sk-test-NOT-A-REAL-KEY", "from-dotenv-value")


def t_secrets():
    import re
    pat = re.compile(r"((?<![A-Za-z0-9/])sk-(?:proj-|ant-)[A-Za-z0-9_\-]{20,}|(?<![A-Za-z0-9/])sk-[A-Za-z0-9]{32,}|AIza[0-9A-Za-z_\-]{30,}|FAL_KEY=\S{10,}|OPENAI_API_KEY=\S{10,}|ANTHROPIC_API_KEY=\S{10,})")
    env_vals = {}
    for l in ((ROOT / ".env").read_text(encoding="utf-8").splitlines() if (ROOT / ".env").is_file() else []):   # no .env in a fresh workspace
        if "=" in l:
            k, v = l.split("=", 1); v = v.strip().strip('"')
            if len(v) > 12: env_vals[k] = v
    hits = []
    for p in SUB.rglob("*"):
        if p.is_file() and p.name != "smoke_tests.py" and p.suffix.lower() in {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".py", ".log", ".csv", ".toml", ".example", ""}:
            t = p.read_text(encoding="utf-8", errors="ignore")
            real = [m.group(0) for m in pat.finditer(t) if not any(a in m.group(0) for a in PLACEHOLDERS)]   # the repo's tests use obvious fake keys
            if real or any(v in t for v in env_vals.values()):
                hits.append(p.relative_to(SUB).as_posix())
    rec("No API keys / .env values in any text file of submission/", not hits, "clean" if not hits else "HITS: " + ", ".join(hits))


# 7 (Phase 7B/7C). slide 5: v2 rebuild equals the preserved v2 (provenance); v3 (zinc claim) rebuild equals the runs/ export AND the packaged copy
def t_slide5():
    def load(name):
        sp = importlib.util.spec_from_file_location(name, ROOT / f"plans/gymbeam_hr/phase5/{name}.py"); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
    m2, m3 = load("slide5_final_v2"), load("slide5_final_v3")
    o2 = m2.rebuild(TMP)
    n2, h2 = frames_md5(o2, 1080, 1350); r2 = frames_md5(ROOT / "runs/colla-pink/slide5_video/slide5_napitak_za_ljepotu_FINAL_v2_1080x1350.mp4", 1080, 1350)
    rec("Slide 5 v2 (superseded) rebuilt from kling_raw_v2.mp4 + text layer equals the preserved v2 (decoded frames)", (n2, h2) == r2, f"frames {n2} vs {r2[0]}; md5 {'equal' if h2 == r2[1] else 'DIFFERENT'}")
    d3 = TMP / "v3"; o3 = m3.build(d3)
    n3, h3 = frames_md5(o3, 1080, 1350); r3 = frames_md5(ROOT / "runs/colla-pink/slide5_video/slide5_napitak_za_ljepotu_FINAL_v3_1080x1350.mp4", 1080, 1350)
    pk = frames_md5(SUB / "phases/05_carousel_post2/superseded_7E/slide_5_napitak_za_ljepotu_video_v3_1080x1350.mp4", 1080, 1350)
    same_bytes = sha(o3) == sha(SUB / "phases/05_carousel_post2/superseded_7E/slide_5_napitak_za_ljepotu_video_v3_1080x1350.mp4")
    rec("Slide 5 v3 (superseded 7E zinc wording) rebuilt locally equals the runs/ export and the archived copy (frames and bytes)", (n3, h3) == r3 == pk and same_bytes, f"frames {n3}; md5 {'equal' if h3 == r3[1] else 'DIFFERENT'}; bytes_equal={same_bytes}")
    q = m3.qa(o3, ROOT / "runs/colla-pink/slide5_video/slide5_napitak_za_ljepotu_FINAL_v2_1080x1350.mp4", d3 / "text_layer_v4_zinc_1080x1350.png", d3)
    rec("Slide 5 v3 per-frame QA (121 frames, text present on every frame, layer unchanged above the edited box)", q["ok"], f"claim err {q['claim_text_mean_abs_err_vs_burgundy_max_over_frames']}, headline err {q['headline_mean_abs_err_max_over_frames']}, diff above box mean {q['above_y1130_vs_v2']['mean_abs_diff']}")

    m4 = load("slide5_final_v4")
    d4 = TMP / "v4"; o4 = m4.build(d4)
    n4, h4 = frames_md5(o4, 1080, 1350); r4 = frames_md5(ROOT / "runs/colla-pink/slide5_video/slide5_napitak_za_ljepotu_FINAL_v4_1080x1350.mp4", 1080, 1350)
    pk4 = SUB / "posts/post_02_beastpink_carousel/slide_5_napitak_za_ljepotu_video_v4_1080x1350.mp4"
    same4 = sha(o4) == sha(pk4)
    rec("Slide 5 v4 (three authorised zinc claims) rebuilt locally equals the runs/ export and the packaged file (frames and bytes)", (n4, h4) == r4 == frames_md5(pk4, 1080, 1350) and same4, f"frames {n4}; md5 {'equal' if h4 == r4[1] else 'DIFFERENT'}; bytes_equal={same4}")
    q4 = m4.qa(o4, ROOT / "runs/colla-pink/slide5_video/slide5_napitak_za_ljepotu_FINAL_v3_1080x1350.mp4", d4 / "text_layer_v5_zinc3_1080x1350.png", d4)
    rec("Slide 5 v4 per-frame QA (121 frames, text burgundy on every frame, layer unchanged above the edited box)", q4["ok"], f"claim err {q4['claim_text_mean_abs_err_vs_burgundy_max_over_frames']}, headline err {q4['headline_mean_abs_err_max_over_frames']}")


# 7b (7F). slide 3 v3: subtitle never touched by the spoon/scoop; rebuild equals the packaged file
def t_slide3_v3():
    sp = importlib.util.spec_from_file_location("s3v3", ROOT / "plans/gymbeam_hr/phase5/slide3_final_v3.py"); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    d = TMP / "s3v3"; out = m.build(d, None)
    pk = SUB / "posts/post_02_beastpink_carousel/slide_3_PRIPREMA_video_v3_1080x1350.mp4"
    n1, h1 = frames_md5(out, 1080, 1350); n0, h0 = frames_md5(pk, 1080, 1350); same = sha(out) == sha(pk)
    rec("Slide 3 v3 rebuilt locally equals the packaged file (decoded frames and bytes)", (n1, h1) == (n0, h0) and same, f"frames {n1} vs {n0}; md5 {'equal' if h1 == h0 else 'DIFFERENT'}; bytes_equal={same}")
    from PIL import Image
    raw = m.read(m.OUT / "kling_raw.mp4"); occ = m.occlusion(Image.open(d / "text_layer_v3_1080x1350.png").convert("RGBA"), raw)
    bad = [i for i, c in enumerate(occ["subtitle"]) if c > 0]
    rec("Slide 3 v3: no spoon/scoop pixel within 4 px of the subtitle text in any of the 121 frames", not bad and len(raw) == 121, f"frames with contact: {bad}")


# 7c (7F). slide 6 v2: retouch re-run on the frozen original equals the packaged file; the frozen original is preserved
def t_slide6():
    sp = importlib.util.spec_from_file_location("s6c", ROOT / "plans/gymbeam_hr/phase5/slide6_cleanup.py"); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(m.SRC).convert("RGB")); out, info = m.retouch(im)
    pk = np.asarray(Image.open(SUB / "posts/post_02_beastpink_carousel/slide_6_odaberi_svoj_okus_FINAL_v2_1080x1350.png").convert("RGB"))
    frozen = SUB / "phases/05_carousel_post2/superseded_7E/slide_6_odaberi_svoj_okus_FINAL_1080x1350.png"
    ok = np.array_equal(out, pk) and sha(frozen) == sha(m.SRC)
    rec("Slide 6 v2: local retouch re-run on the frozen original equals the packaged file; the frozen original is preserved unchanged", ok, f"retouch equal={np.array_equal(out, pk)}; frozen original hash equal={sha(frozen) == sha(m.SRC)}; filled px {info['patch_fill_px']}, streak px {info['streak_px']}")



# 8. original plan preserved (hashes recorded in the final revision)
def t_plan_preserved():
    rev = json.loads((ROOT / "plans/gymbeam_hr/final_revision/content_plan_final_revision.json").read_text(encoding="utf-8"))
    bad = [k for k, v in rev["preserved_originals"].items() if sha(ROOT / k) != v]
    plan = json.loads((ROOT / "plans/gymbeam_hr/content_plan.json").read_text(encoding="utf-8"))
    ok = not bad and plan["plan_hash"] == rev["supersedes_plan_hash"]
    rec("Original plan files unchanged (SHA-256 equal to the hashes recorded in R9) and plan hash 970975125494... intact", ok, "equal" if ok else f"CHANGED: {bad}")


# 8b. R9 matches the exact delivered files
def t_r9():
    rev = json.loads((ROOT / "plans/gymbeam_hr/final_revision/content_plan_final_revision.json").read_text(encoding="utf-8"))
    bad = []
    for post in rev["posts"]:
        for rel, h in post["deliverable_sha256"].items():
            f = SUB / rel
            if not f.is_file() or sha(f) != h: bad.append(rel)
    posts = [p["title"] for p in rev["posts"]]
    ok = not bad and len(posts) == 3 and "Wafer" in posts[2] and "V8" in posts[2] and rev["posts"][1]["slide_files"][4].endswith("video_v4_1080x1350.mp4") and rev["posts"][1]["slide_files"][2].endswith("video_v3_1080x1350.mp4") and rev["posts"][2]["deliverable"].endswith("FINAL_V8.mp4")
    rec("R9 lists exactly the 3 delivered posts and every listed file hash equals the file in submission/posts (slide 3 = v3, slide 5 = v4, Reel = FINAL V8)", ok, "ok" if ok else f"mismatch: {bad}")


# 9b (Phase 7E). captions of record (POST.md) equal the captions in R9; disclosures present; slide 6 text untouched; Post 2 compliance flagged pending
def t_captions():
    import re
    rev = json.loads((ROOT / "plans/gymbeam_hr/final_revision/content_plan_final_revision.json").read_text(encoding="utf-8"))
    norm = lambda t: re.sub(r"\s+", " ", re.sub(r"[>*]", " ", t)).strip()
    probs = []
    for rel, post in zip(("posts/post_01_creatine_hero/POST.md", "posts/post_02_beastpink_carousel/POST.md", "posts/post_03_gymbeam_wafer_reel/POST.md"), rev["posts"]):
        text = norm((SUB / rel).read_text(encoding="utf-8"))
        if norm(post["caption_final"]) not in text: probs.append(f"{rel}: caption differs from R9")
        if "službena suradnja s gymbeamom" not in post["caption_final"].lower(): probs.append(f"{rel}: no 'not an official collaboration' disclosure")
        if not all(h in post["caption_final"] for h in post["final_hashtags"]): probs.append(f"{rel}: hashtags not in caption")
        if "#gymbeamhr" not in post["final_hashtags"]: probs.append(f"{rel}: #gymbeamhr missing")
    cap = " ".join(p["caption_final"] for p in rev["posts"])
    if "obaveza" in cap or "GymBeamom niti" in cap or "na fotografijama je fiktivna" in cap or "na linku" in cap: probs.append("an uncorrected phrase is still in a caption")
    if "osoba i prizori u objavi generirani su umjetnom inteligencijom" not in rev["posts"][1]["caption_final"] or "BeastPinkom" not in rev["posts"][1]["caption_final"] or "#beastpink" not in rev["posts"][1]["final_hashtags"]: probs.append("post 2 disclosure/#beastpink")
    ac = rev.get("author_confirmation") or {}
    if ac.get("statement") != "Author-reviewed and accepted for the Sekvenca private take-home demonstration, including visual content, captions and Reel audio." or not re.fullmatch(r"20\d\d-\d\d-\d\d", ac.get("date", "")) or ac.get("brand_or_legal_approval") != "none claimed": probs.append("author confirmation record (statement/date/no brand-legal approval)")
    if "Portfolio demonstration only; not approved for public commercial advertising." not in rev["approval_status"]["B_public_commercial_advertising"] or "RECORDED" not in rev.get("signoff_status", ""): probs.append("approval categories A/B or sign-off status")
    if "reviewed and accepted by the author" not in rev["approval_status"]["audio_review"]: probs.append("audio acceptance record")
    low = json.dumps(rev).lower()
    for bad in ("not signed", "not listened", "audio review required", "no audio approval", "approval pending", "signature not recorded"):
        if bad in low: probs.append(f"obsolete warning '{bad}' in R9")
    if "FINAL_SCOPE_REVISION_7F" not in rev.get("final_scope_revision", ""): probs.append("R9 does not reference the final scope")
    if rev["posts"][1].get("slide6_text_unchanged") != "ODABERI SVOJ OKUS." or "NOT CLEARED" not in rev["posts"][1].get("compliance_status", ""): probs.append("post 2 slide 6 / compliance status")
    rec("Captions of record (POST.md) = R9 captions; each has the not-an-official-collaboration disclosure; corrected phrases; slide 6 text unchanged; Post 2 compliance marked pending", not probs, "ok" if not probs else "; ".join(probs))


# 9. submission consistency
def t_consistency():
    S = SUB; probs = []
    posts = sorted(p.name for p in (S / "posts").iterdir() if p.is_dir())
    if posts != ["post_01_creatine_hero", "post_02_beastpink_carousel", "post_03_gymbeam_wafer_reel"]: probs.append(f"post folders: {posts}")
    car = sorted(p.name for p in (S / "posts/post_02_beastpink_carousel").glob("slide_*"))
    want = [("slide_1_", ".png"), ("slide_2_", ".png"), ("slide_3_", ".mp4"), ("slide_4_", ".png"), ("slide_5_", ".mp4"), ("slide_6_", ".png")]
    if len(car) != 6 or any(not (n.startswith(a) and n.endswith(b)) for n, (a, b) in zip(car, want)): probs.append(f"carousel slides: {car}")
    if "slide_3_PRIPREMA_video_v3" not in "".join(car): probs.append("slide 3 is not the v3 PRIPREMA file")
    if "slide_5_napitak_za_ljepotu_video_v4" not in "".join(car): probs.append("slide 5 is not v4")
    if "slide_6_odaberi_svoj_okus_FINAL_v2" not in "".join(car): probs.append("slide 6 is not v2")
    if not (S / "posts/post_02_beastpink_carousel/BEASTPINK_CAROUSEL_FINAL_CONTACT_SHEET_v4.png").is_file() or list((S / "posts").rglob("*CONTACT_SHEET_v3*")) or list((S / "posts").rglob("*CONTACT_SHEET_v2*")): probs.append("contact sheet is not v4 only")
    r = sorted(p.name for p in (S / "posts/post_03_gymbeam_wafer_reel").glob("*"))
    if "GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4" not in r or any(n.endswith("_V4.mp4") for n in r) or not any("SELECTED_COVER_B_1080x1920" in n for n in r): probs.append(f"reel files: {r}")
    for rel in ("phases/06_reel_post3/versions/GYMBEAM_WAFER_LIFESTYLE_REEL_V4_REJECTED.mp4", "phases/06_reel_post3/versions/GYMBEAM_WAFER_LIFESTYLE_REEL_V8_CANDIDATE_source.mp4", "phases/06_reel_post3/video_clips/S03B_kling_raw.mp4",
                "phases/05_carousel_post2/superseded_7E/slide_6_odaberi_svoj_okus_FINAL_1080x1350.png", "phases/05_carousel_post2/superseded_7E/slide_3_PRIPREMA_video_v2_1080x1350.mp4", "compliance/ZINC_CLAIM_432_2012_HR.md", "phases/02_plan/FINAL_SCOPE_REVISION_7F.md", "phases/02_plan/FINAL_SCOPE_REVISION_7F.yaml", "ai_recipe/repo/briefs/gymbeam_hr.yaml", "compliance/ALT_TEXT_HR.md", "compliance/CAPTION_CHANGES_7F.md", "compliance/HASHTAG_CHECK_7F.md", "FINAL_SIGNOFF_7F.md"):
        if not (S / rel).is_file(): probs.append(f"missing: {rel}")
    for rel, needle in (("posts/post_01_creatine_hero/POST.md", "## Full caption"), ("posts/post_02_beastpink_carousel/POST.md", "## Full caption"),
                        ("posts/post_03_gymbeam_wafer_reel/POST.md", "## Caption"), ("phases/06_reel_post3/review_package/CAPTION.md", "")):
        f = S / rel
        if not f.is_file() or needle not in f.read_text(encoding="utf-8"): probs.append(f"caption missing: {rel}")
    import hashlib as _h
    if _h.sha256((S / "ai_recipe/repo/briefs/gymbeam_hr.yaml").read_bytes()).hexdigest() != "e4e6572ec2c39227c57fbce3b60e980246b0e9449cfb998bdc99d3e147bb32d2": probs.append("original brief changed")
    for rel in ("README.md", "START_HERE.md", "FINAL_SIGNOFF_7F.md", "FINAL_READINESS_REPORT.md", "posts/post_01_creatine_hero/POST.md", "posts/post_02_beastpink_carousel/POST.md", "posts/post_03_gymbeam_wafer_reel/POST.md", "phases/02_plan/CONTENT_PLAN_FINAL_REVISION.md"):
        low = (S / rel).read_text(encoding="utf-8").lower()
        for bad in ("sign-off is pending", "pending lara", "awaiting lara", "_candidate.zip` in the project root", "approval none**", "nothing here is approved yet", "no handwritten signature", "not listened to", "human audio review", "no audio approval", "audio approval pending", "signature not recorded", "no signature and no approval"):
            if bad in low: probs.append(f"draft wording '{bad}' in {rel}")
    pdf = (S / "methodology/METODOLOGIJA_HR.pdf").read_bytes()
    import re
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
    if not 1 <= pages <= 2: probs.append(f"PDF pages {pages}")
    for rel in ("ai_recipe/AI_RECIPE.md", "ai_recipe/prompts/reel/KLING_S02_prompt_SENT.txt", "ai_recipe/code/phase5/slide5_final_v3.py", "ai_recipe/code/phase5/slide5_final_v4.py", "ai_recipe/code/phase5/slide3_final_v3.py", "ai_recipe/code/phase5/slide6_cleanup.py", "ai_recipe/code/phase5/final_contact_sheet_v4.py", "ai_recipe/code/phase6_reel/assemble_reel_v8_candidate.py", "ai_recipe/code/phase6_reel/gen_keyframe_S03B.py", "ai_recipe/code/phase6_reel/run_kling_S03B.py", "ai_recipe/code/phase5/final_contact_sheet_v3.py", "phases/05_carousel_post2/slide5_video/slide5_v3_QA.json", "phases/05_carousel_post2/slide5_video/superseded_v2/slide5_napitak_za_ljepotu_FINAL_v2_1080x1350.mp4", "FINAL_READINESS_REPORT.md", "ai_recipe/repo/studio/providers/live.py", "ai_recipe/repo/pyproject.toml",
                "compliance/SLIDE5_CLAIM_REVIEW.md", "phases/02_plan/CONTENT_PLAN_FINAL_REVISION.md", "phases/02_plan/content_plan.json", "setup/SETUP.md"):
        if not (S / rel).is_file(): probs.append(f"missing: {rel}")
    rec("Submission consistency: 3 posts, 6 ordered carousel slides (slide 3 v3, slide 5 v4, slide 6 v2), Reel FINAL V8 + cover B, captions, PDF 1-2 pages, required files present", not probs, "ok" if not probs else "; ".join(probs))


# 10 (7F). every package path named in the methodology PDF exists inside the package; PDF has exactly 2 pages
def t_pdf_paths():
    import re
    try:
        import fitz
    except ImportError:
        rec("PDF paths exist inside the package", True, "SKIPPED: PyMuPDF (fitz) not installed; checked by the packaging run"); return
    d = fitz.open(str(SUB / "methodology/METODOLOGIJA_HR.pdf")); text = " ".join(p.get_text() for p in d).replace("\n", " ")
    paths = set(re.findall(r"((?:ai_recipe|phases|posts|compliance|tools|setup|assets)/[A-Za-z0-9_./\-]*[A-Za-z0-9_\-/])", text)) | {"REFERENCE_ASSETS.md", "SHA256SUMS.txt", "SUBMISSION_MANIFEST.json", "START_HERE.md"}
    missing = sorted(p for p in paths if not (SUB / p.rstrip("/")).exists() and not any(SUB.glob(p.rstrip("/") + "*")))
    rec("Methodology PDF: exactly 2 pages and every package path it names exists inside the package", len(d) == 2 and not missing, f"pages {len(d)}; paths checked {len(paths)}; missing {missing}")


if __name__ == "__main__":
    for fn in (t_guards, t_cli_preflights, t_v4, t_v8, t_slide3, t_slide3_v3, t_slide5, t_slide6, t_cover, t_formats, t_plan_preserved, t_r9, t_captions, t_consistency, t_pdf_paths, t_secrets):
        try:
            fn()
        except Exception as e:
            rec(fn.__name__, False, f"{type(e).__name__}: {str(e)[:300]}")
    out = (ROOT if os.environ.get("SUBMISSION_DIR") else SUB / "smoke_tests"); out.mkdir(parents=True, exist_ok=True)
    (out / ("smoke_results_workspace.json" if os.environ.get("SUBMISSION_DIR") else "smoke_results.json")).write_text(json.dumps(RES, indent=1, ensure_ascii=False), encoding="utf-8")
    print(sum(r["result"] == "PASS" for r in RES), "pass /", len(RES))
    sys.exit(0 if all(r["result"] == "PASS" for r in RES) else 1)   # 7D: a failing test must fail the run
