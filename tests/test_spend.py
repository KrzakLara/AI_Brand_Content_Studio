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
    with pytest.raises(BudgetExceeded, match="request NOT sent"):  # worst case (400 output tokens) > 0.001 USD
        metered(t, budget=0.001).structured(ResearchStep, task="research_policy", payload={})
    assert t.calls == []  # nothing left the process


def test_actual_usage_is_recorded_and_the_cap_binds_before_the_request_that_would_break_it():
    t = RecordedTransport().add(ANTHROPIC_URL, **reply_usage('{"action": "finish"}', tin=2000, tout=300))
    llm = metered(t, budget=0.015)  # one request worst case is about 0.009 USD: room for exactly one
    llm.structured(ResearchStep, task="research_policy", payload={})
    assert llm.http_requests == 1 and len(llm.usage_log) == 1
    u = llm.usage_log[0]
    assert (u["input_tokens"], u["output_tokens"], u["request_id"]) == (2000, 300, "req_test_1")
    assert u["cost_usd"] == pytest.approx((2000 * 3 + 300 * 15) / 1e6) and llm.spent_usd == pytest.approx(u["cost_usd"])
    assert llm.remaining_usd() == pytest.approx(0.015 - u["cost_usd"])
    with pytest.raises(BudgetExceeded):
        llm.structured(ResearchStep, task="research_policy", payload={})
    assert len(t.calls) == 1  # the second request was never sent
    assert KEY not in json.dumps(llm.usage_log)  # the key never reaches logs


def test_research_policy_requests_are_capped_to_a_small_max_tokens():
    t = RecordedTransport().add(ANTHROPIC_URL, **reply_usage('{"action": "finish"}'))
    metered(t, max_tokens=4096).structured(ResearchStep, task="research_policy", payload={})
    body = json.loads(t.bodies[0])
    assert body["max_tokens"] == 400 and body["model"] == "claude-test-model"


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
    llm = metered(t, budget=0.02)  # affords exactly one decision
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
    base = ["--runs-dir", str(tmp_path), "research", "--mode", "live", "--policy", "anthropic", "--max-requests", "5"]
    assert cli.main(base) == cli.EXIT_ERROR
    assert "explicit --max-api-spend-usd" in capsys.readouterr().err
    assert cli.main(["--runs-dir", str(tmp_path), "research", "--mode", "live", "--policy", "anthropic",
                     "--max-api-spend-usd", "1"]) == cli.EXIT_ERROR
    assert "explicit --max-requests" in capsys.readouterr().err
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
    conf["anthropic_pricing"] = {"claude-sonnet-5-5": {"input_usd_per_mtok": 3.0, "output_usd_per_mtok": 15.0}}
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
    assert summ["estimated_cost_usd"] == pytest.approx(api["spent_usd"]) and summ["tool_cost_usd"] == 0  # paid spend is not hidden


# --- Haiku 5.5 test-run guarantees ---------------------------------------------------------------
def test_config_carries_the_verified_haiku_55_prices_and_nothing_invented():
    from studio.config import load_settings
    p = load_settings(ROOT / "config.yaml").anthropic_pricing
    h = p["claude-haiku-5-5"]
    assert (h.input_usd_per_mtok, h.output_usd_per_mtok, h.max_prompt_tokens) == (0.10, 0.50, 100_000)
    assert "platform.claude.com" in h.source_url and h.verified_on == "2026-10-27"
    assert set(p) == {"claude-haiku-5-5"}  # no price for any other model was guessed


def test_the_planned_haiku_run_fits_the_budget_with_a_wide_margin():
    """5 requests max, 0.10 USD cap: even the pessimistic per-request worst case leaves room for every request."""
    t = RecordedTransport().add(ANTHROPIC_URL, **reply_usage('{"action": "finish"}'))
    llm = metered(t, budget=0.10, pin=0.10, pout=0.50, max_requests=5)
    big_prompt = "x" * 40_000  # far larger than a compact research prompt
    worst = llm._worst_case_usd(big_prompt, 400)
    assert worst * 5 < 0.10 and worst < 0.01


def test_request_cap_counts_preflight_messages_and_retries():
    t = RecordedTransport().add(MODELS_URL, body=json.dumps({"id": "claude-test-model"}), content_type="application/json")
    t.add(ANTHROPIC_URL, **reply_usage('{"action": "finish"}'))
    llm = metered(t, budget=1.0, pin=0.1, pout=0.5, max_requests=3)
    llm.preflight()  # 1
    llm.structured(ResearchStep, task="research_policy", payload={})  # 2
    llm.structured(ResearchStep, task="research_policy", payload={})  # 3
    from studio.providers.live import RequestLimitExceeded
    with pytest.raises(RequestLimitExceeded, match="request NOT sent"):
        llm.structured(ResearchStep, task="research_policy", payload={})
    assert llm.api_requests == 3 and len(t.calls) == 3
    t2 = RecordedTransport().add(ANTHROPIC_URL, method="POST", status=529, body="busy")
    l2 = metered(t2, budget=1.0, pin=0.1, pout=0.5, max_requests=2)
    with pytest.raises(RequestLimitExceeded):  # attempt 1 and its first retry are sent; the third is refused
        l2.structured(ResearchStep, task="research_policy", payload={})
    assert len(t2.calls) == 2


def test_prompts_that_could_cross_the_price_tier_are_refused_not_priced_by_guesswork():
    t = RecordedTransport().add(ANTHROPIC_URL, **reply_usage('{"action": "finish"}'))
    llm = metered(t, budget=1.0, pin=0.1, pout=0.5, max_prompt_tokens=500)
    with pytest.raises(BudgetExceeded, match="higher price tier"):
        llm.structured(ResearchStep, task="research_policy", payload={"blob": "y" * 5000})
    assert t.calls == []


def tool_reply(inp, tin=800, tout=60):
    return dict(method="POST", status=200, content_type="application/json", headers={"request-id": "req_tool"},
                body=json.dumps({"model": "claude-test-model", "stop_reason": "tool_use",
                                "content": [{"type": "tool_use", "id": "toolu_1", "name": "respond", "input": inp}],
                                "usage": {"input_tokens": tin, "output_tokens": tout}}))


def test_request_forces_one_client_side_tool_and_uses_no_server_side_tools():
    t = RecordedTransport().add(ANTHROPIC_URL, **tool_reply({"action": "finish"}))
    step = metered(t).structured(ResearchStep, task="research_policy", payload={"x": 1})
    assert step.action == "finish"
    body = json.loads(t.bodies[0])
    assert set(body) == {"model", "max_tokens", "tools", "tool_choice", "messages"}
    (tool,) = body["tools"]
    assert set(tool) == {"name", "description", "input_schema"}  # a client tool: no "type" => not a server-side tool
    assert tool["name"] == "respond" and body["tool_choice"]["name"] == "respond" and body["tool_choice"]["type"] == "tool"
    assert "web_search" not in t.bodies[0].decode() and "web_fetch" not in t.bodies[0].decode().split("<data>")[0]
    assert KEY not in t.bodies[0].decode()


def test_tool_arguments_are_validated_against_the_schema():
    t = RecordedTransport().add(ANTHROPIC_URL, **tool_reply({"action": "dance"}))
    with pytest.raises(ProviderResponseError, match="malformed"):
        metered(t).structured(ResearchStep, task="research_policy", payload={})


def test_text_fallback_tolerates_prose_around_the_json_and_errors_show_what_the_model_said():
    t = RecordedTransport().add(ANTHROPIC_URL, **reply_usage('Sure! Here you go: {"action": "finish"} Hope that helps.'))
    assert metered(t).structured(ResearchStep, task="research_policy", payload={}).action == "finish"
    t2 = RecordedTransport().add(ANTHROPIC_URL, **reply_usage('{"action": "tool", "tool": "web_fetch" "args": {}}'))
    with pytest.raises(ProviderResponseError, match="model text starts: .*web_fetch"):
        metered(t2).structured(ResearchStep, task="research_policy", payload={})


def test_request_and_spend_caps_survive_a_process_restart(tmp_path):
    log = tmp_path / "run" / "api_usage.jsonl"
    t = RecordedTransport().add(MODELS_URL, body=json.dumps({"id": "claude-test-model"}), content_type="application/json")
    t.add(ANTHROPIC_URL, **tool_reply({"action": "finish"}, tin=1000, tout=100))
    a = metered(t, budget=0.10, pin=0.10, pout=0.50, max_requests=3, usage_path=log)
    a.preflight()
    a.structured(ResearchStep, task="research_policy", payload={})
    assert a.api_requests == 2
    b = metered(t, budget=0.10, pin=0.10, pout=0.50, max_requests=3, usage_path=log)  # "new process", same run
    assert b.api_requests == 2 and b.spent_usd == pytest.approx(a.spent_usd) and len(b.usage_log) == 1
    b.structured(ResearchStep, task="research_policy", payload={})  # 3rd request: allowed
    from studio.providers.live import RequestLimitExceeded
    c = metered(t, budget=0.10, pin=0.10, pout=0.50, max_requests=3, usage_path=log)
    with pytest.raises(RequestLimitExceeded):
        c.structured(ResearchStep, task="research_policy", payload={})  # the 4th is refused across processes
    assert KEY not in log.read_text(encoding="utf-8") and len(t.calls) == 3


def test_a_request_is_counted_before_it_is_sent_so_a_crash_cannot_hide_spending(tmp_path):
    log = tmp_path / "api_usage.jsonl"
    t = RecordedTransport().add(ANTHROPIC_URL, method="POST", raises="TransportError")
    llm = metered(t, budget=1.0, pin=0.1, pout=0.5, max_requests=10, usage_path=log, retries=0)
    with pytest.raises(ProviderResponseError):
        llm.structured(ResearchStep, task="research_policy", payload={})
    lines = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert [x["kind"] for x in lines] == ["message"] and lines[0]["requests"] == 1


def test_cli_real_run_needs_a_run_id_for_persistent_accounting(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    rc = cli.main(["--runs-dir", str(tmp_path), "research", "--mode", "live", "--policy", "anthropic",
                   "--model", "claude-haiku-5-5", "--max-api-spend-usd", "0.1", "--max-requests", "5"])
    assert rc == cli.EXIT_ERROR and "needs --run RUN_ID" in capsys.readouterr().err and not list(tmp_path.iterdir())


def test_paid_policy_gets_a_compact_view_of_what_the_tools_returned():
    from studio.nodes.research_live import _view
    h = [{"tool": "web_fetch", "args": {"url": "u"}, "ok": True, "titles": ["T"], "product_count": 3,
          "links": [f"https://gymbeam.hr/page{i}" for i in range(200)] + ["https://gymbeam.hr/kreatin-x.html"],
          "product_urls": [f"https://gymbeam.hr/p{i}.html" for i in range(60)],
          "stylesheets": ["a", "b", "c"], "images": [f"i{i}" for i in range(20)]}]
    full, compact = _view(h), _view(h, ["kreatin"])
    assert len(full[0]["links"]) == 201 and len(compact[0]["links"]) == 12
    assert "https://gymbeam.hr/kreatin-x.html" in compact[0]["links"]  # relevant links survive the cut
    assert len(compact[0]["product_urls"]) == 12 and len(compact[0]["stylesheets"]) == 2 and len(compact[0]["images"]) == 6
    assert len(json.dumps(compact)) < len(json.dumps(full)) / 4


def test_dotenv_loader_sets_only_missing_vars_and_never_returns_values(tmp_path, monkeypatch):
    monkeypatch.delenv("STUDIO_NO_DOTENV")
    f = tmp_path / ".env"
    f.write_text("\n".join(["# comment", 'ANTHROPIC_API_KEY="from-dotenv-value"', "EXISTING=new", "EMPTY=",
                            "export OTHER='o'", "bad line", ""]))
    monkeypatch.setenv("EXISTING", "keep")
    names = cli.load_dotenv(f)
    import os
    assert sorted(names) == ["ANTHROPIC_API_KEY", "OTHER"]  # names only
    assert os.environ["ANTHROPIC_API_KEY"] == "from-dotenv-value" and os.environ["EXISTING"] == "keep"
    assert "EMPTY" not in os.environ
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.delenv("OTHER")
    monkeypatch.setenv("STUDIO_NO_DOTENV", "1")  # the guard the test-suite relies on
    assert cli.load_dotenv(f) == [] and "ANTHROPIC_API_KEY" not in os.environ


def test_cli_refuses_a_model_without_a_configured_price(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    rc = cli.main(["--runs-dir", str(tmp_path), "research", "--mode", "live", "--policy", "anthropic",
                   "--model", "claude-unpriced-9", "--max-api-spend-usd", "0.1", "--max-requests", "5"])
    err = capsys.readouterr().err
    assert rc == cli.EXIT_ERROR and "no entry for model 'claude-unpriced-9'" in err and KEY not in err
    assert not list(tmp_path.iterdir())
