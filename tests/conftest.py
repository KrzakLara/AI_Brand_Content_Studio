import socket
from pathlib import Path

import pytest
import yaml

from studio.config import load_settings
from studio.contracts import BriefInput
from studio.orchestrator import Orchestrator
from studio.providers.mock import build_mock_providers

ROOT = Path(__file__).resolve().parents[1]


class NetworkAttempt(AssertionError):
    pass


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any outbound connection attempt fails the test (requirement H)."""
    def blocked(*a, **k):
        raise NetworkAttempt("network access attempted during tests")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket.socket, "sendto", blocked)  # connectionless (UDP/DNS) route
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


@pytest.fixture
def settings():
    return load_settings(ROOT / "config.yaml")


@pytest.fixture
def brief():
    return BriefInput.model_validate(
        yaml.safe_load((ROOT / "briefs" / "gymbeam_hr.yaml").read_text(encoding="utf-8")))


@pytest.fixture
def make_orch(settings, tmp_path):
    """Factory: fresh providers each call, shared runs/export dirs (simulates a new process)."""
    def make(*, fail_rounds=None, crash_post=None, auto=True, approvals=None):
        return Orchestrator(
            settings, runs_dir=tmp_path / "runs", export_dir=tmp_path / "submission",
            providers=build_mock_providers(settings, fail_rounds=fail_rounds, crash_post=crash_post),
            auto_approve_mock=auto, approvals=approvals)
    return make


@pytest.fixture(autouse=True)
def no_credentials(monkeypatch):
    """Tests must never see real credentials, so no paid provider can be reached by accident."""
    monkeypatch.setenv("STUDIO_NO_DOTENV", "1")  # a developer's real .env must never reach a test
    for k in ("ANTHROPIC_API_KEY", "APIFY_TOKEN", "APIFY_API_TOKEN", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture
def rsettings(settings):
    """Settings with zero retry backoff so failure tests are fast."""
    return settings.model_copy(update={"research": settings.research.model_copy(update={"backoff_s": 0.0})})
