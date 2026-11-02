"""Contracts, ledger, store, CLI and requirement H (no network / no paid APIs)."""
import socket

import pytest
from pydantic import ValidationError

from studio import cli
from studio.contracts import (
    BrandProfile,
    ContentPlan,
    OperationStatus,
    PostPlan,
    ProviderKind,
)
from studio.cost import BudgetExceeded, CostEstimator
from studio.ledger import Ledger, NeedsReconciliation, OperationRunner
from studio.providers.base import ProviderInfo
from studio.state import merge_dicts
from studio.store import RunStore

from .conftest import ROOT, NetworkAttempt


def plan_post(pid, fmt):
    return dict(post_id=pid, format=fmt, objective="o", hook="h", key_message="k",
                evidence_ids=["E1"], cta="c")


def test_content_plan_requires_three_posts_with_fixed_formats():
    ok = [plan_post("01", "carousel"), plan_post("02", "hero"), plan_post("03", "reel")]
    assert ContentPlan(posts=ok).post("03").format == "reel"
    with pytest.raises(ValidationError):
        ContentPlan(posts=ok[:2])
    with pytest.raises(ValidationError):
        ContentPlan(posts=[plan_post("01", "hero"), *ok[1:]])
    with pytest.raises(ValidationError):
        PostPlan(**{**ok[0], "evidence_ids": []})


def test_contracts_forbid_extra_fields_and_check_palette():
    with pytest.raises(ValidationError):
        PostPlan(**plan_post("01", "carousel"), surprise=1)
    with pytest.raises(ValidationError):
        BrandProfile(brand_name="b", positioning="p", voice="v", palette=["red"], audience_summary="a")


def info(retry: bool) -> ProviderInfo:
    return ProviderInfo("p", ProviderKind.IMAGE, "m", is_mock=False, safe_to_retry=retry)


def test_ledger_marks_interrupted_calls_unknown_and_refuses_unsafe_retry(tmp_path, settings):
    ledger = Ledger(tmp_path / "s.db")
    runner = OperationRunner(ledger, CostEstimator(settings), "r")
    op = ledger.begin("r", "n", "01", info(False), "k1")  # process "dies" here: no complete()
    assert ledger.reconcile_pending("r") == 1
    assert ledger.list("r")[0].status == OperationStatus.UNKNOWN and op
    with pytest.raises(NeedsReconciliation):
        runner.run(node="n", scope="01", provider=info(False), key="k1", fn=lambda: {"x": 1})
    assert runner.run(node="n", scope="01", provider=info(True), key="k1", fn=lambda: {"x": 1}) == {"x": 1}
    # done results are reused, fn is not called again
    assert runner.run(node="n", scope="01", provider=info(True), key="k1",
                      fn=lambda: pytest.fail("called twice")) == {"x": 1}


def test_ledger_records_failure(tmp_path, settings):
    ledger = Ledger(tmp_path / "s.db")
    runner = OperationRunner(ledger, CostEstimator(settings), "r")

    def boom():
        raise ValueError("provider error")
    with pytest.raises(ValueError):
        runner.run(node="n", scope=None, provider=info(True), key="k", fn=boom)
    assert ledger.summary("r")["failed"] == 1


def test_budget_guard_blocks_before_the_call(tmp_path, settings):
    settings = settings.model_copy(update={"budget_usd": 0.0})
    settings.pricing["image"].usd_per_unit = 1.0
    runner = OperationRunner(Ledger(tmp_path / "s.db"), CostEstimator(settings), "r")
    with pytest.raises(BudgetExceeded):
        runner.run(node="n", scope=None, provider=info(True), key="k",
                   fn=lambda: pytest.fail("must not be called"))


def test_stage_cache_validity_and_forced_invalidation(tmp_path):
    s = RunStore(tmp_path / "s.db")
    s.put_stage("r", "01", "produce#0", "fpA", {"v": 1})
    assert s.get_stage("r", "01", "produce#0", "fpA") == {"v": 1}
    assert s.get_stage("r", "01", "produce#0", "fpB") is None  # changed input
    s.put_stage("r", "02", "produce#0", "fpA", {"v": 2})
    assert s.invalidate("r", prefixes=["produce"], scope="01") == 1
    assert s.get_stage("r", "01", "produce#0", "fpA") is None
    assert s.get_stage("r", "02", "produce#0", "fpA") == {"v": 2}  # other post untouched
    assert s.generation("r", "01", "produce#0") == 1 and s.generation("r", "02", "produce#0") == 0


def test_merge_reducer_keeps_both_sides():
    assert merge_dicts({"01": 1}, {"02": 2}) == {"01": 1, "02": 2}
    assert merge_dicts(None, {"a": 1}) == {"a": 1}


# H ------------------------------------------------------------------------
def test_h_network_is_blocked_in_tests():
    with pytest.raises(NetworkAttempt):
        socket.create_connection(("example.com", 80))


def test_h_run_uses_only_mock_providers_and_costs_nothing(make_orch, brief):
    orch = make_orch()
    orch.run("run-h", brief=brief)  # would raise NetworkAttempt on any socket use
    with orch.open("run-h") as (svc, *_):
        ops = svc.ledger.list("run-h")
        assert svc.is_mock and ops and all(o.mock and o.estimated_cost_usd == 0 for o in ops)
        assert all(o.provider.startswith("mock-") for o in ops)
        assert svc.ledger.total_cost("run-h") == 0


def test_h_source_has_no_network_or_vendor_client_imports():
    """AST scan (see tests/netguard.py): only studio/tools/transport.py may import urllib.request."""
    from .netguard import scan_tree
    transport = ROOT / "studio" / "tools" / "transport.py"
    assert scan_tree(ROOT / "studio", {transport: frozenset({"urllib.request"})}) == {}


# CLI ----------------------------------------------------------------------
def test_cli_run_mock_and_live_refusal(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(ROOT)
    base = ["--runs-dir", str(tmp_path / "runs")]
    assert cli.main([*base, "run", "--export-dir", str(tmp_path / "sub")]) == cli.EXIT_ERROR
    assert "Phase 2" in capsys.readouterr().err
    assert cli.main([*base, "run", "--mock", "--export-dir", str(tmp_path / "sub")]) == cli.EXIT_OK
    assert "status: completed" in capsys.readouterr().out
    assert len(list((tmp_path / "sub").glob("run-*/manifest.json"))) == 1


def test_cli_manual_approval_flow_and_status(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(ROOT)
    base = ["--runs-dir", str(tmp_path / "runs")]
    ex = ["--export-dir", str(tmp_path / "sub")]
    assert cli.main([*base, "run", "--mock", "--manual-approval", *ex, "--run", "r1",
                     "--brief", "briefs/gymbeam_hr.yaml"]) == cli.EXIT_PAUSED
    assert cli.main([*base, "approve", "--run", "r1", "--gate", "final"]) == cli.EXIT_ERROR  # wrong gate
    assert cli.main([*base, "approve", "--run", "r1", "--gate", "plan"]) == cli.EXIT_OK
    assert cli.main([*base, "run", "--mock", "--manual-approval", *ex, "--run", "r1"]) == cli.EXIT_PAUSED
    assert cli.main([*base, "approve", "--run", "r1", "--gate", "final"]) == cli.EXIT_OK
    assert cli.main([*base, "run", "--mock", "--manual-approval", *ex, "--run", "r1"]) == cli.EXIT_OK
    out = tmp_path / "approvals.yaml"
    assert cli.main([*base, "export-approvals", "--run", "r1", "--out", str(out)]) == cli.EXIT_OK
    assert cli.main([*base, "run", "--mock", *ex, "--approvals", str(out), "--run", "r2",
                     "--brief", "briefs/gymbeam_hr.yaml"]) == cli.EXIT_OK
    capsys.readouterr()
    assert cli.main([*base, "status", "--run", "r2"]) == cli.EXIT_OK
    assert '"status": "completed"' in capsys.readouterr().out


def test_cli_crash_resume_and_post_redo(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(ROOT)
    base = ["--runs-dir", str(tmp_path / "runs")]
    ex = ["--export-dir", str(tmp_path / "sub")]
    assert cli.main([*base, "run", "--mock", *ex, "--run", "rc", "--mock-crash", "03"]) == cli.EXIT_CRASH
    assert cli.main([*base, "run", "--mock", *ex, "--run", "rc"]) == cli.EXIT_OK
    assert cli.main([*base, "run", "--mock", *ex, "--run", "rc", "--post", "03", "--mock-fail", "03=1"]) == cli.EXIT_OK
    assert "post 03 [reel]: exported (repairs: 1)" in capsys.readouterr().out
    assert cli.main([*base, "run", "--mock", *ex, "--run", "rc", "--from", "plan"]) == cli.EXIT_OK


def test_cli_interactive_brief_writes_validated_yaml(tmp_path, monkeypatch):
    def answer(*vals):
        it = iter(vals)
        monkeypatch.setattr("builtins.input", lambda prompt="": next(it))
    # the empty campaign_goal answer is rejected (required) and re-prompted
    answer("Acme", "Widget", "", "Sell widgets", "Makers", "", "", "https://acme.example")
    out = tmp_path / "b.yaml"
    assert cli.main(["brief", "--out", str(out)]) == cli.EXIT_OK
    brief = cli.load_brief(str(out))
    assert brief.brand_name == "Acme" and brief.campaign_goal == "Sell widgets"
    assert brief.tone == "confident, friendly" and brief.website_url == "https://acme.example"
    answer("A", "B", "C", "D", "", "", "not-a-url")  # invalid url -> nothing written
    out2 = tmp_path / "b2.yaml"
    assert cli.main(["brief", "--out", str(out2)]) == cli.EXIT_ERROR and not out2.exists()
    answer("A", "B", "C", "D", "", "", "")
    assert cli.main(["brief", "--out", str(out)]) == cli.EXIT_ERROR  # refuses to overwrite
