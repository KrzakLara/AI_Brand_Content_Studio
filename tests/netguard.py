"""AST-based guard: only `studio/tools/transport.py` may reach the network.

Regexes miss `from urllib import request`, `from http import client`, aliasing and dynamic imports,
so this walks the syntax tree. It flags (1) imports of network/vendor modules however spelled,
(2) dynamic imports (`__import__`, `importlib.import_module`), (3) any `.urlopen(` call.
"""
import ast
from pathlib import Path

BANNED = (
    "socket", "ssl", "http.client", "http.server", "urllib.request", "urllib3", "ftplib", "smtplib",
    "telnetlib", "poplib", "imaplib", "xmlrpc", "websocket", "websockets", "requests", "httpx", "aiohttp",
    "openai", "anthropic", "google.genai", "google.generativeai", "replicate", "cohere", "mistralai",
    "boto3", "grpc",
)
DYNAMIC = {"__import__", "import_module"}


def _banned(name: str) -> str | None:
    return next((b for b in BANNED if name == b or name.startswith(b + ".")), None)


def scan_source(src: str, allowed: frozenset[str] = frozenset()) -> list[str]:
    """Return human-readable violations. ``allowed`` lists banned module prefixes this file may use."""
    out: list[str] = []
    for n in ast.walk(ast.parse(src)):
        names: list[str] = []
        if isinstance(n, ast.Import):
            names = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            names = [n.module] + [f"{n.module}.{a.name}" for a in n.names]  # `from urllib import request`
        for name in names:
            hit = _banned(name)
            if hit and hit not in allowed:
                out.append(f"line {n.lineno}: import of {name}")
        if isinstance(n, ast.Call):
            f = n.func
            fname = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if fname in DYNAMIC:
                out.append(f"line {n.lineno}: dynamic import via {fname}()")
            if fname == "urlopen" and "urllib.request" not in allowed:
                out.append(f"line {n.lineno}: urlopen() call")
    return sorted(set(out))


def scan_tree(root: Path, allowed_files: dict[Path, frozenset[str]]) -> dict[str, list[str]]:
    result = {}
    for p in sorted(root.rglob("*.py")):
        v = scan_source(p.read_text(encoding="utf-8"), allowed_files.get(p, frozenset()))
        if v:
            result[str(p)] = v
    return result
