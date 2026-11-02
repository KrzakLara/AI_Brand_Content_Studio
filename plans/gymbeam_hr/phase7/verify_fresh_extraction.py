"""Fresh-extraction verification (Phase 7D, extended in 7G). Extracts the submission ZIP into a NEW folder, bootstraps a workspace, installs the environment (with the 7G media pin), runs the tests,
runs tools/REPRODUCE_SVE_TRI_OBJAVE_7F.ps1 and the single commands documented in setup/SVE_NAREDBE_HERO_CAROUSEL_REEL_7F.md, and records how the paid scripts refuse without keys.
No API key is read and no network call is made by the project code (pip downloads packages from PyPI). Writes a timestamped log; the result of each step is the real exit code.

  python verify_fresh_extraction.py --zip <file.zip> --work <NEW empty folder, short path> --log <log file> [--py "py -3.12"]
"""
import argparse
import datetime as dt
import os
import shlex
import subprocess
import sys
import time
import zipfile
from pathlib import Path

RESULTS = []


def stamp():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(fh, text):
    fh.write(text + "\n"); fh.flush(); print(text)


def run(fh, name, cmd, cwd, env=None, tail=25, timeout=1500):
    log(fh, f"\n=== [{stamp()}] STEP {name}\n$ {' '.join(map(str, cmd))}   (cwd {cwd})")
    t = time.time()
    p = subprocess.run(list(map(str, cmd)), cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    out = (p.stdout + p.stderr).strip().splitlines()
    log(fh, "\n".join(out[-tail:]))
    ok = p.returncode == 0
    RESULTS.append((name, ok)); log(fh, f"--- {name}: {'PASS' if ok else 'FAIL'} (exit {p.returncode}, {time.time() - t:.0f} s)")
    return ok, "\n".join(out)


def doc_single_commands(fh, P, WS, W):
    """Executes the blocks of setup/SVE_NAREDBE_HERO_CAROUSEL_REEL_7F.md between the TEST markers literally (paths substituted), so the documented commands are proven to work."""
    import re
    md = (P / "setup/SVE_NAREDBE_HERO_CAROUSEL_REEL_7F.md").read_text(encoding="utf-8")
    body = md.split("<!-- TEST:BEGIN single -->")[1].split("<!-- TEST:END -->")[0]
    code = "\n".join(re.findall(r"```powershell\n(.*?)```", body, re.S))
    code = code.replace(r"C:\work\pkg\submission", str(P)).replace(r"C:\work\ws", str(WS)).replace(r"C:\work\einzeln", str(W / "einzeln"))
    script = W / "documented_single_commands.ps1"
    script.write_text("$ErrorActionPreference = 'Stop'\n" + code + "\nexit $LASTEXITCODE\n", encoding="utf-8-sig")
    run(fh, "documented single commands (SVE_NAREDBE...md, section 3) executed literally", ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script], W, tail=20, timeout=1800)


def guard_only_preflights(fh, WS, vpy, P):
    """The paid production scripts must REFUSE here (no key, caps consumed, official photos absent). Nothing is generated and no network access happens. PASS = refused as documented."""
    env = {"PYTHONPATH": str(P / "tools/offline_guard"), "PYTHONDONTWRITEBYTECODE": "1", "STUDIO_NO_DOTENV": "1"}
    cases = [("plans/gymbeam_hr/phase6/reel/run_kling.py", ["S08", "--preflight"], "video request limit 4 reached - request NOT sent"),
             ("plans/gymbeam_hr/phase6/reel/gen_keyframe.py", ["S01", "--preflight"], "image request limit 15 reached - request NOT sent"),
             ("plans/gymbeam_hr/phase6/reel/run_kling_S03B.py", ["--preflight"], "FileNotFoundError"),
             ("plans/gymbeam_hr/phase6/reel/gen_keyframe_S03B.py", ["--preflight"], "FileNotFoundError"),
             ("plans/gymbeam_hr/phase5/slide3_video_generate.py", [], "FileNotFoundError"),
             ("plans/gymbeam_hr/phase5/slide5_video_generate_v2.py", [], "FileNotFoundError"),
             ("plans/gymbeam_hr/art_direction/hero_proof/make_hero.py", ["preflight"], "FileNotFoundError")]
    for script, args, needle in cases:
        log(fh, f"\n=== [{stamp()}] GUARD-ONLY {script} {' '.join(args)}")
        r = subprocess.run([str(vpy), script] + args, cwd=WS, env={**os.environ, **env}, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        out = (r.stdout + r.stderr).strip().splitlines()
        log(fh, "\n".join(out[-3:]))
        ok = r.returncode != 0 and needle in (r.stdout + r.stderr)
        RESULTS.append((f"paid script refuses without key/caps: {Path(script).name} {' '.join(args)}", ok)); log(fh, f"--- refused as documented ({needle}): {'PASS' if ok else 'FAIL'} (exit {r.returncode})")
    log(fh, f"\n=== [{stamp()}] GUARD-ONLY plans/gymbeam_hr/phase5/carousel_rest.py preflight 3 (prints the guard state, sends nothing)")
    r = subprocess.run([str(vpy), "plans/gymbeam_hr/phase5/carousel_rest.py", "preflight", "3"], cwd=WS, env={**os.environ, **env}, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    log(fh, (r.stdout + r.stderr).strip()[-400:])
    RESULTS.append(("carousel_rest.py preflight 3 prints the guard state and sends nothing", r.returncode == 0 and "requests" in r.stdout)); log(fh, f"--- {'PASS' if RESULTS[-1][1] else 'FAIL'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, required=True); ap.add_argument("--work", type=Path, required=True); ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--py", default="py -3.12", help="Python launcher used to create the virtual environment")
    ap.add_argument("--packshot", type=Path, help="optional: the officially downloaded creatine packshot; then the 2 skipped tests are run too and must pass")
    a = ap.parse_args()
    W = a.work.resolve()
    if W.exists() and any(W.iterdir()):
        sys.exit(f"work folder {W} must be new/empty")
    W.mkdir(parents=True, exist_ok=True); a.log.parent.mkdir(parents=True, exist_ok=True)
    py = shlex.split(a.py)
    with open(a.log, "w", encoding="utf-8") as fh:
        log(fh, f"Fresh-extraction verification, started {stamp()}\nZIP: {a.zip}\nWork folder: {W}\nHost: {os.name}, launcher: {a.py}")
        zs = zipfile.ZipFile(a.zip); bad = zs.testzip()
        RESULTS.append(("zip integrity", bad is None)); log(fh, f"zip integrity (testzip): {'PASS' if bad is None else 'FAIL ' + bad}; {len(zs.namelist())} entries")
        zs.extractall(W / "extracted"); P = W / "extracted" / "submission"; WS = W / "ws"
        longest = max(len(str(P / n)) for n in zs.namelist()); log(fh, f"extracted to {P}; longest extracted path {longest} characters")
        run(fh, "verify package hashes (tools/verify_hashes.py)", py + [str(P / "tools/verify_hashes.py"), "--package", P], W)
        run(fh, "bootstrap workspace (tools/bootstrap_workspace.py)", py + [str(P / "tools/bootstrap_workspace.py"), "--package", P, "--target", WS], W)
        vpy = WS / ".venv/Scripts/python.exe"
        run(fh, "create virtual environment", py + ["-m", "venv", ".venv"], WS)
        run(fh, 'pip install -e ".[dev,media]" -c constraints-media-7G.txt', [vpy, "-m", "pip", "install", "-q", "-e", ".[dev,media]", "-c", "constraints-media-7G.txt"], WS, tail=6)
        ok, out = run(fh, "full test suite (pytest)", [vpy, "-m", "pytest", "-o", "addopts=", "-p", "no:cacheprovider"], WS, tail=6)
        if a.packshot:
            ok, out = run(fh, "pytest summary check: exactly the 2 external-asset tests skipped", [vpy, "-m", "pytest", "-o", "addopts=", "-p", "no:cacheprovider", "-q", "-rs", "tests/test_provenance.py", "tests/test_strategy.py"], WS, tail=6)
            skipped = [l for l in out.splitlines() if l.startswith("SKIPPED")]
            RESULTS[-1] = (RESULTS[-1][0], ok and len(skipped) == 2 and all("stored packshot not present" in l for l in skipped)); log(fh, f"skipped tests: {len(skipped)}, all 'stored packshot not present': {RESULTS[-1][1]}")
            run(fh, "place official packshot (tools/place_packshot.py)", [vpy, P / "tools/place_packshot.py", "--workspace", WS, "--file", a.packshot], WS)
            ok, out = run(fh, "full test suite WITH the packshot supplied (expect 249 passed, 0 skipped)", [vpy, "-m", "pytest", "-o", "addopts=", "-p", "no:cacheprovider"], WS, tail=4)
            RESULTS[-1] = (RESULTS[-1][0], ok and "249 passed" in out and "skipped" not in out.splitlines()[-1]); log(fh, f"249 passed and 0 skipped: {RESULTS[-1][1]}")
        env = {"STUDIO_NO_DOTENV": "1", "PYTHONIOENCODING": "utf-8"}
        run(fh, "mock workflow (studio run --mock)", [WS / ".venv/Scripts/studio.exe", "run", "--mock", "--run", "fresh7d", "--export-dir", W / "mock_out"], WS, env=env, tail=8)
        run(fh, "REPRODUCE_SVE_TRI_OBJAVE_7F.ps1: all three real posts into a NEW folder (no API call)", ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", P / "tools/REPRODUCE_SVE_TRI_OBJAVE_7F.ps1",
            "-Workspace", WS, "-OutDir", W / "tri_objave"], W, tail=14, timeout=1800)
        doc_single_commands(fh, P, WS, W)
        guard_only_preflights(fh, WS, vpy, P)
        run(fh, "smoke tests incl. deterministic video rebuilds (SUBMISSION_DIR = extracted package)", [vpy, "plans/gymbeam_hr/phase7/smoke_tests.py"], WS,
            env={**env, "SUBMISSION_DIR": str(P)}, tail=22, timeout=1800)
        log(fh, "\n=== SUMMARY")
        for n, ok in RESULTS:
            log(fh, f"{'PASS' if ok else 'FAIL'}  {n}")
        allok = all(ok for _, ok in RESULTS)
        log(fh, f"\nOVERALL: {'ALL STEPS PASSED' if allok else 'FAILED'} ({stamp()})")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
