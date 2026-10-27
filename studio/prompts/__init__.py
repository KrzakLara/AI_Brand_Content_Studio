"""Versioned prompt texts. Their hash is part of every stage fingerprint."""
from functools import cache
from pathlib import Path

from studio.fingerprint import sha256_bytes


@cache
def load(name: str) -> str:
    return (Path(__file__).parent / f"{name}.md").read_text(encoding="utf-8")


def version(name: str) -> str:
    return sha256_bytes(load(name).encode("utf-8"))[:12]
