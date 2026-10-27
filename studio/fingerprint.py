"""Content-based fingerprints. Deterministic and independent of run ids and timestamps."""
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _plain(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


def canonical(obj: Any) -> str:
    return json.dumps(_plain(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(*parts: Any) -> str:
    return hashlib.sha256(canonical(list(parts)).encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
