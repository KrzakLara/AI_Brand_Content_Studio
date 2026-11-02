"""Fresh-extraction verification (Phase 7D). Extracts the submission ZIP into a NEW folder, bootstraps a workspace, installs the environment, and runs the tests.
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
        run(fh, 'pip install -e ".[dev,media]"', [vpy, "-m", "pip", "install", "-q", "-e", ".[dev,media]"], WS, tail=6)
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
