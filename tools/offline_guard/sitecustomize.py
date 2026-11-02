"""Offline guard (Phase 7G). REPRODUCE_SVE_TRI_OBJAVE_7F.ps1 puts this folder on PYTHONPATH, so every Python process of the reproduction
loads this module at start-up and REFUSES any non-local network connection. A reproduction step that tried to reach OpenAI, Anthropic, fal.ai
or any other host would stop with an error instead of silently spending money. Local (loopback / Unix) sockets stay allowed."""
import socket

_real_connect, _real_connect_ex, _real_getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
_LOCAL = ("127.", "::1", "localhost", "0.0.0.0")


def _is_local(addr) -> bool:
    host = addr[0] if isinstance(addr, tuple) else addr
    return isinstance(addr, (str, bytes)) and not isinstance(addr, tuple) or str(host).startswith(_LOCAL)


def _blocked(host):
    raise OSError(f"OFFLINE GUARD: network access to {host!r} is blocked during the free local reproduction (no API calls allowed)")


def connect(self, addr):
    if not _is_local(addr): _blocked(addr)
    return _real_connect(self, addr)


def connect_ex(self, addr):
    if not _is_local(addr): _blocked(addr)
    return _real_connect_ex(self, addr)


def getaddrinfo(host, *a, **k):
    if not str(host).startswith(_LOCAL) and host is not None: _blocked(host)
    return _real_getaddrinfo(host, *a, **k)


socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, getaddrinfo
