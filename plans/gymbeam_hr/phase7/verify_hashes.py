"""Verify every file of the extracted package against SHA256SUMS.txt (standard library only; works where `sha256sum` is not installed).

  python tools/verify_hashes.py [--package <extracted submission folder>]
Exit code 0 = all listed files present and identical; also reports files that are present but not listed."""
import argparse
import hashlib
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--package", type=Path, default=Path.cwd())
    P = ap.parse_args().package.resolve()
    sums = P / "SHA256SUMS.txt"
    if not sums.is_file():
        sys.exit(f"no SHA256SUMS.txt in {P}")
    listed, bad, missing = set(), [], []
    for line in sums.read_text(encoding="utf-8").splitlines():
        if "  " not in line:
            continue
        h, rel = line.split("  ", 1); listed.add(rel); f = P / rel
        if not f.is_file():
            missing.append(rel)
        elif hashlib.sha256(f.read_bytes()).hexdigest() != h:
            bad.append(rel)
    extra = sorted(p.relative_to(P).as_posix() for p in P.rglob("*") if p.is_file() and p.relative_to(P).as_posix() not in listed | {"SHA256SUMS.txt", ".gitkeep"})
    print(f"listed {len(listed)} | mismatched {len(bad)} | missing {len(missing)} | present but not listed {len(extra)}")
    for tag, items in (("MISMATCH", bad), ("MISSING", missing), ("UNLISTED", extra)):
        for i in items[:20]:
            print(" ", tag, i)
    sys.exit(1 if bad or missing else 0)


if __name__ == "__main__":
    main()
