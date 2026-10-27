"""Proves the network guards actually detect violations (not just that today's code is clean)."""
import http.client
import socket
import urllib.request

import pytest

from .conftest import ROOT, NetworkAttempt
from .netguard import scan_source, scan_tree

TRANSPORT = ROOT / "studio" / "tools" / "transport.py"
ALLOWED = {TRANSPORT: frozenset({"urllib.request"})}

VIOLATIONS = [
    "import socket",
    "import socket as s",
    "from socket import create_connection",
    "import urllib.request",
    "import urllib.request as u",
    "from urllib import request",
    "from urllib.request import urlopen",
    "from http import client",
    "import http.client",
    "import requests",
    "import httpx as h",
    "from anthropic import Anthropic",
    "import openai",
    "import ssl",
    "import smtplib",
    "__import__('socket')",
    "import importlib\nimportlib.import_module('socket')",
    "import foo\nfoo.urlopen('http://x')",
]


@pytest.mark.parametrize("src", VIOLATIONS)
def test_guard_flags_every_unauthorised_spelling(src):
    assert scan_source(src), f"guard missed: {src!r}"


@pytest.mark.parametrize("src", ["import json\nimport urllib.error\nfrom urllib.parse import urlparse",
                                 "import urllib.robotparser", "from pathlib import Path", "import yaml"])
def test_guard_allows_harmless_imports(src):
    assert scan_source(src) == []


def test_only_transport_py_may_use_urllib_request_and_nothing_else_banned():
    src = TRANSPORT.read_text(encoding="utf-8")
    assert scan_source(src) != []  # without the exemption it IS a violation
    assert scan_source(src, ALLOWED[TRANSPORT]) == []  # exemption is narrow
    assert scan_source("import socket", ALLOWED[TRANSPORT]) != []  # exemption does not cover other modules
    assert scan_source("import urllib.request", frozenset()) != []  # and does not apply to other files


def test_real_source_tree_is_clean_except_for_transport():
    assert scan_tree(ROOT / "studio", ALLOWED) == {}


def test_guard_catches_a_violation_planted_in_a_scanned_tree(tmp_path):
    (tmp_path / "ok.py").write_text("import json\n")
    (tmp_path / "bad.py").write_text("from urllib import request\nrequest.urlopen('http://x')\n")
    found = scan_tree(tmp_path, {})
    assert list(found) == [str(tmp_path / "bad.py")] and len(found[str(tmp_path / "bad.py")]) == 2


# --- runtime guard (conftest): any real connection attempt must fail the test -----------------
def test_runtime_guard_blocks_every_stdlib_route_to_the_network():
    with pytest.raises(NetworkAttempt):
        socket.create_connection(("example.com", 80))
    with pytest.raises(NetworkAttempt):
        socket.socket().connect(("93.184.216.34", 80))
    with pytest.raises(NetworkAttempt):
        socket.getaddrinfo("example.com", 80)
    with pytest.raises(NetworkAttempt):
        http.client.HTTPSConnection("example.com").request("GET", "/")
    with pytest.raises(NetworkAttempt):
        urllib.request.urlopen("https://example.com/")
    with pytest.raises(NetworkAttempt):
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b"x", ("8.8.8.8", 53))
