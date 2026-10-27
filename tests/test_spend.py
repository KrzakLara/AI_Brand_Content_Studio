"""Spend control for the real Anthropic run, proven against recorded transports only.

These tests show the 5-step / USD limits bind BEFORE any request is sent, so a real run cannot exceed them.
The keys below are obviously fake; sockets are blocked by conftest.
"""
import json
from pathlib import Path

import pytest
import yaml

from studio import cli
from studio.cost import BudgetExceeded
from studio.providers.base import ProviderResponseError, ProviderUnavailable, ResearchStep
from studio.providers.live import ANTHROPIC_URL, AnthropicLLM
from studio.tools.transport import RecordedTransport

from . import research_fixtures as fx
from .test_research import dump_transport, index_of, make

KEY = "sk-test-NOT-A-REAL-KEY-0123456789"
MODELS_URL = "https://api.anthropic.com/v1/models/claude-test-model"
ROOT = Path(__file__).resolve().parents[1]


def metered(t, budget=1.0, pin=3.0, pout=15.0, **kw):
    return AnthropicLLM("claude-test-model", t, api_key=KEY, origin="fixture", sleep=lambda s: None,
                        input_usd_per_mtok=pin, output_usd_per_mtok=pout, budget_usd=budget, **kw)


def reply_usage(text, tin=1000, tout=200, status=200):
    return dict(method="POST", status=status, content_type="application/json", headers={"request-id": "req_test_1"},
                body=json.dumps({"id": "msg_x", "model": "claude-test-model", "stop_reason": "end_turn",
                                 "content": [{"type": "text", "text": text}],
                                 "usage": {"input_tokens": tin, "output_tokens": tout}}))


def test_preflight_distinguishes_every_failure_without_spending():
    ok = RecordedTransport().add(MODELS_URL, body=json.dumps({"id": "claude-test-model", "display_name": "Test"}),
                                 content_type="application/json")
    assert metered(ok).preflight() == {"ok": True, "model": "claude-test-model", "display_name": "Test"}
    for status, text in ((401, "authentication failed"), (403, "lacks permission"), (404, "not accessible"),
                         (429, "rate limited or out of credit")):
        t = RecordedTransport().add(MODELS_URL, status=status, body="{}")
        with pytest.raises(ProviderUnavailable, match=text):
            metered(t).preflight()
    t = RecordedTransport().add(MODELS_URL, raises="TransportError")
    with pytest.raises(ProviderUnavailable, match="network"):
        metered(t).preflight()
    with pytest.raises(ProviderUnavailable, match="not set"):
        AnthropicLLM("m", RecordedTransport(), api_key=None).preflight()
    assert all(m == "GET" for m, _ in ok.calls)  # preflight never POSTs a (billable) message


def test_no_request_is_sent_without_prices_or_when_the_budget_could_be_exceeded():
    t = RecordedTransport().add(ANTHROPIC_URL, **reply_usage('{"action": "finish"}'))
    with pytest.raises(ProviderUnavailable, match="anthropic_pricing is not configured"):
        metered(t, pin=None, pout=None).structured(ResearchStep, task="research_policy", payload={})
    with pytest.raises(BudgetExceeded, match="request NOT sent"):  # worst case (1024 output tokens) > 0.001 USD
        metered(t, budget=0.001).structured(ResearchStep, task="research_policy", payload={})
    assert t.calls == []  # nothing left the process


def test_actual_usage_is_recorded_and_the_cap_binds_before_the_request_that_would_break_it():
    t = RecordedTransport().add(ANTHROPIC_URL, **reply_usage('{"action": "finish"}', tin=2000, tout=300))
    llm = metered(t, budget=0.025)  # one request worst case is about 0.017 USD (1024 out tokens): room for exactly one
    llm.structured(ResearchStep, task="research_policy", payload={})
    assert llm.http_requests == 1 and len(llm.usage_log) == 1
    u = llm.usage_log[0]
    assert (u["input_tokens"], u["output_tokens"], u["request_id"]) == (2000, 300, "req_test_1")
    assert u["cost_usd"] == pytest.approx((2000 * 3 + 300 * 15) / 1e6) and llm.spent_usd == pytest.approx(u["cost_usd"])
    assert llm.remaining_usd() == pytest.approx(0.025 - u["cost_usd"])
    with pytest.raises(BudgetExceeded):
        llm.structured(ResearchStep, task="research_policy", payload={})
    assert len(t.calls) == 1  # the second request was never sent
    assert KEY not in json.dumps(llm.usage_log)  # the key never reaches logs


def test_research_policy_requests_are_capped_to_a_small_max_tokens():
    t = RecordedTransport().add(ANTHROPIC_URL, **reply_usage('{"action": "finish"}'))
    metered(t, max_tokens=4096).structured(ResearchStep, task="research_policy", payload={})
    body = json.loads(t.bodies[0])
    assert body["max_tokens"] == 1024 and body["model"] == "claude-test-model"


def test_retries_are_also_budget_checked_and_failures_are_not_billed():
    t = RecordedTransport().add(ANTHROPIC_URL, method="POST", status=529, body="busy")
    llm = metered(t, budget=1.0)
    with pytest.raises(ProviderResponseError, match="after retries"):
        llm.structured(ResearchStep, task="research_policy", payload={})
    assert llm.http_requests == 3 and llm.spent_usd == 0 and llm.usage_log == []


def test_agent_stops_safely_when_the_api_budget_is_reached(tmp_path, rsettings):
    t = fx.site(with_products=False, apify=False)
    t.add(ANTHROPIC_URL, **reply_usage(json.dumps({"action": "tool", "tool": "web_fetch", "args": {"url": fx.SITE}}),
                                       tin=2000, tout=300))
    llm = metered(t, budget=0.03)  # affords exactly one decision
    orch, _ = make(tmp_path, rsettings, t, llm=llm)
    res = orch.run("b1", brief=fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]))
    assert res.values["research"]["stop_reason"] == "max_api_budget"
    assert [s.url for s in index_of(res).sources] == [fx.SITE]  # what was collected before the stop is kept
    assert [c for c in t.calls if c[0] == "POST"] == [("POST", ANTHROPIC_URL)]  # exactly one API request


def test_agent_never_exceeds_the_step_limit_with_a_real_policy(tmp_path, rsettings):
    t = fx.site(with_products=False, apify=False)
    for i in range(1, 9):
        url = fx.SITE if i == 1 else f"{fx.SITE}/page{i}"
        t.add(ANTHROPIC_URL, **reply_usage(json.dumps({"action": "tool", "tool": "web_fetch", "args": {"url": url}})))
        t.add(f"{fx.SITE}/page{i}", status=404, body="x")
    s = rsettings.model_copy(update={"research": rsettings.research.model_copy(update={"max_steps": 5})})
    llm = metered(t, budget=1.0)
    orch, _ = make(tmp_path, s, t, llm=llm)
    res = orch.run("b2", brief=fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]))
    assert res.values["research"]["stop_reason"] == "max_steps" and res.values["research"]["counts"]["steps"] == 5
    assert llm.http_requests == 5 and len(llm.usage_log) == 5


def test_cli_refuses_a_real_run_without_budget_or_prices_before_touching_the_network(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)  # fake key: any network use would fail the test (sockets blocked)
    base = ["--runs-dir", str(tmp_path), "research", "--mode", "live", "--policy", "anthropic"]
    assert cli.main(base) == cli.EXIT_ERROR
    assert "explicit --max-api-spend-usd" in capsys.readouterr().err
    assert cli.main([*base, "--max-api-spend-usd", "1"]) == cli.EXIT_ERROR  # config.yaml prices are intentionally empty
    err = capsys.readouterr().err
    assert "anthropic_pricing" in err and KEY not in err and "Nothing was run" in err
    assert not list(tmp_path.iterdir())


def test_cli_real_policy_run_end_to_end_on_recorded_transport_writes_usage_metadata(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    t = fx.site(with_products=False, apify=False)
    t.add("https://api.anthropic.com/v1/models/claude-sonnet-5-5", body=json.dumps({"id": "claude-sonnet-5-5"}),
          content_type="application/json")
    for step in ({"action": "tool", "tool": "web_fetch", "args": {"url": fx.SITE}, "rationale": "start at the home page"},
                 {"action": "finish", "rationale": "enough for a smoke test"}):
        t.add(ANTHROPIC_URL, **reply_usage(json.dumps(step), tin=1500, tout=100))
    fixdir, out = tmp_path / "fx", tmp_path / "out"
    dump_transport(t, fixdir)
    conf = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    conf["anthropic_pricing"] = {"input_usd_per_mtok": 3.0, "output_usd_per_mtok": 15.0}
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump(conf), encoding="utf-8")
    brief = tmp_path / "b.yaml"
    brief.write_text(yaml.safe_dump(fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]).model_dump(mode="json")))
    rc = cli.main(["--config", str(cfg), "--runs-dir", str(tmp_path / "runs"), "research", "--brief", str(brief),
                   "--mode", "fixture", "--fixtures", str(fixdir), "--policy", "anthropic", "--instagram", "none",
                   "--max-steps", "5", "--max-api-spend-usd", "1.0", "--run", "api1", "--out", str(out)])
    text = capsys.readouterr().out
    assert rc == cli.EXIT_OK and "preflight ok: model claude-sonnet-5-5 accessible" in text and "max steps 5" in text
    raw = (out / "run_summary.json").read_text(encoding="utf-8")
    summ = json.loads(raw)
    assert KEY not in raw and summ["policy_autonomous"] is True and summ["tools_selected"] == {"web_fetch": 1}
    api = summ["api"]
    assert (api["model"], api["http_requests"], api["input_tokens"], api["output_tokens"]) == ("claude-sonnet-5-5", 2, 3000, 200)
    assert api["spent_usd"] == pytest.approx((3000 * 3 + 200 * 15) / 1e6) and api["budget_usd"] == 1.0
    assert api["calls"][0]["request_id"] == "req_test_1" and summ["trace"][0]["why"] == "start at the home page"
