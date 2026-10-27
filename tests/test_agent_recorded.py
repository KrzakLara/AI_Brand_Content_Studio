"""Phase 2b debugging suite: the real-agent pipeline end to end on RECORDED Anthropic responses (no credits spent).

Hops covered: API response -> tool_use -> decision -> tool routing -> execution -> tool result back to the model ->
source extraction -> provenance -> persistence -> verified evidence; plus the hard request/money limits.
"""
import json

import pytest

from studio.cost import BudgetExceeded
from studio.nodes.research_live import ResearchFailed
from studio.providers.base import ResearchStep
from studio.providers.live import ANTHROPIC_URL, AnthropicLLM, RequestLimitExceeded
from studio.tools.transport import GuardedTransport, RecordedTransport, RequestLimitReached

from . import research_fixtures as fx
from .test_research import make
from .test_spend import KEY, MODELS_URL, metered, tool_reply

HOST = ("api.anthropic.com",)


def guarded(inner, limit, log=None):
    return GuardedTransport(inner, limit=limit, hosts=HOST, log_path=log)


def llm_over(transport, **kw):
    kw.setdefault("budget", 1.0)
    return metered(transport, pin=0.1, pout=0.5, **kw)


def decide(**kw):
    return tool_reply({"action": "tool", **kw}, tin=900, tout=70)


def posts(t):
    return [c for c in t.calls if c[0] == "POST"]


# =============================== 2. the request limit can never permit a sixth ==================================
def test_guard_allows_exactly_five_and_refuses_the_sixth_without_forwarding(tmp_path):
    t = RecordedTransport().add(ANTHROPIC_URL, method="POST", body="{}", content_type="application/json")
    t.add("https://example.invalid/other", body="x")
    g = guarded(t, 5, tmp_path / "req.log")
    for _ in range(5):
        g.request("POST", ANTHROPIC_URL, body=b"{}")
    with pytest.raises(RequestLimitReached, match="request NOT sent"):
        g.request("POST", ANTHROPIC_URL, body=b"{}")
    assert len(posts(t)) == 5 and g.count == 5
    g.request("GET", "https://example.invalid/other")  # other hosts are not counted or limited
    log = (tmp_path / "req.log").read_text(encoding="utf-8").splitlines()
    assert log == ["POST api.anthropic.com/v1/messages"] * 5  # method+host+path only: no headers, query or key
    # a "new process" sees the same persisted count
    g2 = guarded(t, 5, tmp_path / "req.log")
    assert g2.count == 5
    with pytest.raises(RequestLimitReached):
        g2.request("POST", ANTHROPIC_URL, body=b"{}")


def test_guard_stops_the_sixth_even_when_the_adapter_has_no_limit_of_its_own():
    t = RecordedTransport().add(ANTHROPIC_URL, **tool_reply({"action": "finish"}))
    llm = llm_over(guarded(t, 5), max_requests=None)  # adapter would happily keep going
    llm.transport = guarded(t, 5)
    for _ in range(5):
        llm.structured(ResearchStep, task="research_policy", payload={})
    with pytest.raises(RequestLimitExceeded, match="request NOT sent"):
        llm.structured(ResearchStep, task="research_policy", payload={})
    assert len(posts(t)) == 5


def test_guard_still_holds_when_the_adapters_own_bookkeeping_is_wrong(tmp_path):
    """The original breach: earlier requests were under-counted by hand. The guard's own log is the authority."""
    t = RecordedTransport().add(ANTHROPIC_URL, **tool_reply({"action": "finish"}))
    (tmp_path / "req.log").write_text("POST api.anthropic.com/v1/messages\n" * 3, encoding="utf-8")  # 3 really sent
    usage = tmp_path / "api_usage.jsonl"
    usage.write_text(json.dumps({"kind": "message", "requests": 1}) + "\n", encoding="utf-8")  # adapter thinks 1
    llm = AnthropicLLM("claude-test-model", guarded(t, 5, tmp_path / "req.log"), api_key=KEY, origin="fixture",
                       sleep=lambda s: None, input_usd_per_mtok=0.1, output_usd_per_mtok=0.5, budget_usd=1.0,
                       max_requests=5, usage_path=usage)
    assert llm.api_requests == 1  # the adapter believes it may send 4 more ...
    sent = 0
    for _ in range(4):
        try:
            llm.structured(ResearchStep, task="research_policy", payload={})
            sent += 1
        except RequestLimitExceeded:
            break
    assert sent == 2 and len(posts(t)) == 2  # ... but only 2 more can go out: 3 + 2 = 5, never 6


def test_retries_consume_the_same_allowance_and_the_total_never_exceeds_five():
    t = RecordedTransport().add(ANTHROPIC_URL, method="POST", status=529, body="busy")
    llm = llm_over(guarded(t, 5), max_requests=5)  # retries=2 -> 3 attempts per call
    for expected in (3, 2):  # second call only gets 2 attempts before the allowance is gone
        with pytest.raises((RequestLimitExceeded, Exception)):
            llm.structured(ResearchStep, task="research_policy", payload={})
    assert len(posts(t)) == 5 and llm.api_requests == 5
    with pytest.raises(RequestLimitExceeded):
        llm.structured(ResearchStep, task="research_policy", payload={})
    assert len(posts(t)) == 5


def test_preflight_plus_four_messages_is_five_and_the_fifth_message_is_refused():
    t = RecordedTransport().add(MODELS_URL, body=json.dumps({"id": "claude-test-model"}), content_type="application/json")
    t.add(ANTHROPIC_URL, **tool_reply({"action": "finish"}))
    llm = llm_over(guarded(t, 5), max_requests=5)
    llm.preflight()
    for _ in range(4):
        llm.structured(ResearchStep, task="research_policy", payload={})
    with pytest.raises(RequestLimitExceeded):
        llm.structured(ResearchStep, task="research_policy", payload={})
    assert len(t.calls) == 5 and len(posts(t)) == 4


def test_a_malformed_response_never_triggers_a_hidden_recovery_request():
    from studio.providers.base import ProviderResponseError
    t = RecordedTransport().add(ANTHROPIC_URL, method="POST", status=200, content_type="application/json",
                                body=json.dumps({"content": [{"type": "text", "text": "not json"}],
                                                 "usage": {"input_tokens": 10, "output_tokens": 5}}))
    llm = llm_over(guarded(t, 5), max_requests=5)
    with pytest.raises(ProviderResponseError, match="malformed"):
        llm.structured(ResearchStep, task="research_policy", payload={})
    assert len(posts(t)) == 1 and llm.api_requests == 1  # one request, billed, no automatic second attempt


def test_the_money_limit_is_enforced_independently_of_the_request_count():
    t = RecordedTransport().add(ANTHROPIC_URL, **tool_reply({"action": "finish"}, tin=2000, tout=300))
    # plenty of request allowance, almost no money: refused by the monetary check, request counter untouched
    rich_in_requests = llm_over(guarded(t, 5), budget=0.0001, max_requests=5)
    with pytest.raises(BudgetExceeded) as e:
        rich_in_requests.structured(ResearchStep, task="research_policy", payload={})
    assert not isinstance(e.value, RequestLimitExceeded) and rich_in_requests.api_requests == 0 and posts(t) == []
    # plenty of money, no request allowance: refused by the request limit, with money left over
    rich_in_money = llm_over(guarded(t, 1), budget=1.0, max_requests=1)
    rich_in_money.structured(ResearchStep, task="research_policy", payload={})
    with pytest.raises(RequestLimitExceeded):
        rich_in_money.structured(ResearchStep, task="research_policy", payload={})
    assert rich_in_money.remaining_usd() > 0.99
    # actual spend at/over the budget blocks everything else even though requests remain
    spent_out = llm_over(guarded(t, 9), budget=0.00001, max_requests=9)
    spent_out.spent_usd = 0.00001
    with pytest.raises(BudgetExceeded, match="already spent"):
        spent_out.structured(ResearchStep, task="research_policy", payload={})


# =============================== 3. recorded round trips through the agent ===================================
def brief_kw(**kw):
    return fx.brief(instagram_handle=None, seed_urls=[f"{fx.SITE}/kreatin-monohidrat"], focus_keywords=["kreatin"], **kw)


def replies(t, *decisions):
    for d in decisions:
        t.add(ANTHROPIC_URL, **d)


def test_successful_round_trip_tool_results_reach_the_model_and_evidence_is_verified(tmp_path, rsettings):
    t = fx.site(apify=False)
    replies(t,
            decide(tool="web_fetch", args={"url": f"{fx.SITE}/kreatin-monohidrat"}, rationale="category from seeds"),
            decide(tool="web_fetch", args={"url": fx.A_URL}, rationale="product page seen in category results"),
            decide(tool="download_image", args={"url": fx.IMG_A1, "role": "product"}, rationale="its image"),
            tool_reply({"action": "finish", "rationale": "enough"}))
    llm = llm_over(guarded(t, 5), max_requests=5)
    orch, h = make(tmp_path, rsettings, t, llm=llm)
    res = orch.run("ok1", brief=brief_kw())
    out = res.values["research"]
    assert out["stop_reason"] == "policy_finished" and llm.api_requests == 4
    assert [x["tool"] for x in out["trace"]] == ["web_fetch", "web_fetch", "download_image"]
    # the category page's results were handed back to the model on the next request
    second = json.loads(t.bodies[[i for i, c in enumerate(t.calls) if c[0] == "POST"][1]])
    payload = json.loads(second["messages"][0]["content"].rsplit("<data>", 1)[1].split("</data>")[0])
    assert payload["history"][0]["tool"] == "web_fetch" and payload["history"][0]["ok"] is True
    assert fx.A_URL in payload["history"][0]["product_urls"]
    assert set(payload["tools"]) == {"web_fetch", "instagram_fetch", "download_image"}
    # sources persisted with provenance
    idx = {s["url"]: s for s in out["source_index"]["sources"]}
    for u in (f"{fx.SITE}/kreatin-monohidrat", fx.A_URL, fx.IMG_A1):
        s = idx[u]
        assert s["retrieval_status"] == "ok" and s["origin"] == "fixture" and s["retrieved_at"] and s["artifact_sha256"]
        assert (tmp_path / "runs" / "ok1" / s["artifact_path"]).is_file()
    assert (tmp_path / "runs" / "ok1" / "research" / "source_index.json").is_file()
    # verified evidence derived from the page the model chose
    ev = res.values["research"]["evidence"]["items"]
    variants = [e for e in ev if e["subject"] == "product_variant"]
    assert len(variants) == 3 and all(e["verification_status"] == "verified" and e["source_url"] == fx.A_URL for e in variants)
    assert all(e["retrieved_at"] for e in variants)


def test_original_failure_reproduced_refusals_and_a_404_are_kept_and_explained(tmp_path, rsettings):
    """Haiku's real sequence: three non-existent tool names, then a guessed URL that 404s."""
    t = fx.site(with_products=False, apify=False)
    t.add(f"{fx.SITE}/kreatin.html", status=404, body="gone")
    replies(t,
            decide(tool="fetch_page", args={"url": fx.SITE}, rationale="homepage first"),
            decide(tool="browse", args={"url": fx.SITE}, rationale="homepage"),
            decide(tool="fetch_page", args={"url": f"{fx.SITE}/kreatin.html"}, rationale="category"),
            decide(tool="web_fetch", args={"url": f"{fx.SITE}/kreatin.html"}, rationale="retry with a real tool"))
    llm = llm_over(guarded(t, 4), max_requests=4)
    s = rsettings.model_copy(update={"research": rsettings.research.model_copy(update={"max_steps": 4})})
    orch, _ = make(tmp_path, s, t, llm=llm)
    with pytest.raises(ResearchFailed, match=r"stop_reason=max_steps") as e:
        orch.run("fail1", brief=fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]))
    p = e.value.partial
    assert [x["tool"] for x in p["trace"]] == ["fetch_page", "browse", "fetch_page", "web_fetch"]
    assert [x.get("error", "")[:20] for x in p["trace"][:3]] == ["unknown tool 'fetch_"] * 1 + ["unknown tool 'browse'"[:20]] + ["unknown tool 'fetch_"]
    assert all("valid tools are exactly: web_fetch" in x["error"] for x in p["trace"][:3])
    assert p["trace"][3]["ok"] is False and "404" in p["trace"][3]["error"]
    failed = [x for x in p["sources"] if x["url"].endswith("/kreatin.html")]
    assert failed and failed[0]["retrieval_status"] == "failed" and "404" in failed[0]["access_limitations"]
    kept = json.loads((tmp_path / "runs" / "fail1" / "research" / "partial_research.json").read_text(encoding="utf-8"))
    assert kept["sources"] == p["sources"]  # persisted, not just in memory
    # the refusal text (with the valid tool names) was fed back to the model on the very next request
    third = json.loads(t.bodies[[i for i, c in enumerate(t.calls) if c[0] == "POST"][1]])
    history = json.loads(third["messages"][0]["content"].rsplit("<data>", 1)[1].split("</data>")[0])["history"]
    assert "valid tools are exactly" in history[0]["error"]


def test_a_404_on_a_guessed_url_is_recorded_and_the_agent_recovers_via_a_link_it_has_seen(tmp_path, rsettings):
    t = fx.site(with_products=False, apify=False)
    t.add(f"{fx.SITE}/guess", status=404, body="gone")
    replies(t,
            decide(tool="web_fetch", args={"url": fx.SITE}, rationale="home"),
            decide(tool="web_fetch", args={"url": f"{fx.SITE}/guess"}, rationale="guess"),
            decide(tool="web_fetch", args={"url": f"{fx.SITE}/kreatin-monohidrat"}, rationale="link seen on the home page"),
            tool_reply({"action": "finish"}))
    llm = llm_over(guarded(t, 5), max_requests=5)
    orch, _ = make(tmp_path, rsettings, t, llm=llm)
    res = orch.run("rec1", brief=fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]))
    st = {s["url"]: s["retrieval_status"] for s in res.values["research"]["source_index"]["sources"]}
    assert st[f"{fx.SITE}/guess"] == "failed" and st[f"{fx.SITE}/kreatin-monohidrat"] == "ok" and st[fx.SITE] == "ok"
    assert res.values["research"]["stop_reason"] == "policy_finished"


def test_stop_reasons_max_steps_max_requests_and_max_budget_are_distinct_and_exact(tmp_path, rsettings):
    def run(name, steps, cap, budget, n_replies=9):
        t = fx.site(with_products=False, apify=False)
        for i in range(n_replies):
            t.add(ANTHROPIC_URL, **decide(tool="web_fetch", args={"url": fx.SITE if i == 0 else f"{fx.SITE}/p{i}"},
                                         rationale="r"), )
            t.add(f"{fx.SITE}/p{i + 1}", status=404, body="x")
        llm = llm_over(guarded(t, cap), max_requests=cap, budget=budget)
        s = rsettings.model_copy(update={"research": rsettings.research.model_copy(update={"max_steps": steps})})
        orch, _ = make(tmp_path / name, s, t, llm=llm)
        res = orch.run(name, brief=fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]))
        return res.values["research"], t, llm
    out, t, llm = run("steps", steps=5, cap=9, budget=1.0)  # exactly five permitted by max_steps
    assert out["stop_reason"] == "max_steps" and len(posts(t)) == 5 and llm.api_requests == 5
    out, t, llm = run("reqs", steps=9, cap=5, budget=1.0)  # the sixth is rejected by the request cap
    assert out["stop_reason"] == "max_api_requests" and len(posts(t)) == 5
    out, t, llm = run("money", steps=9, cap=9, budget=0.0009)  # recorded replies are tiny, so use a tiny budget
    assert out["stop_reason"] == "max_api_budget" and 1 <= len(posts(t)) < 5 and 0 < llm.spent_usd < 0.0009


def test_cli_wires_the_transport_guard_and_never_sends_a_sixth_request(tmp_path, monkeypatch, capsys):
    import yaml
    from pathlib import Path

    from studio import cli

    from .test_research import dump_transport
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    t = fx.site(with_products=False, apify=False)
    for i in range(9):  # a model that never finishes
        t.add(ANTHROPIC_URL, **decide(tool="web_fetch", args={"url": fx.SITE if i == 0 else f"{fx.SITE}/p{i}"}, rationale="r"))
        t.add(f"{fx.SITE}/p{i + 1}", status=404, body="x")
    fixdir, out = tmp_path / "fx", tmp_path / "out"
    dump_transport(t, fixdir)
    conf = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
    conf["models"]["research_llm"] = "claude-haiku-5-5"
    conf["research"]["max_steps"] = 9
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump(conf), encoding="utf-8")
    brief = tmp_path / "b.yaml"
    brief.write_text(yaml.safe_dump(fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]).model_dump(mode="json")))
    rc = cli.main(["--config", str(cfg), "--runs-dir", str(tmp_path / "runs"), "research", "--brief", str(brief),
                   "--mode", "fixture", "--fixtures", str(fixdir), "--policy", "anthropic", "--instagram", "none",
                   "--skip-preflight", "--max-requests", "5", "--max-api-spend-usd", "0.03", "--run", "g1", "--out", str(out)])
    text = capsys.readouterr().out
    assert rc == cli.EXIT_OK and "stop_reason: max_api_requests" in text
    guard_log = (tmp_path / "runs" / "g1" / "api_requests.log").read_text(encoding="utf-8").splitlines()
    assert len(guard_log) == 5 and set(guard_log) == {"POST api.anthropic.com/v1/messages"}
    summ = json.loads((out / "run_summary.json").read_text(encoding="utf-8"))
    assert summ["api"]["api_requests"] == 5 and summ["stop_reason"] == "max_api_requests" and KEY not in json.dumps(summ)
    # a second invocation of the same run id cannot send anything: the allowance is already spent
    rc2 = cli.main(["--config", str(cfg), "--runs-dir", str(tmp_path / "runs"), "research", "--brief", str(brief),
                    "--mode", "fixture", "--fixtures", str(fixdir), "--policy", "anthropic", "--instagram", "none",
                    "--skip-preflight", "--max-requests", "5", "--max-api-spend-usd", "0.03", "--run", "g1"])
    assert len((tmp_path / "runs" / "g1" / "api_requests.log").read_text(encoding="utf-8").splitlines()) == 5
    assert rc2 in (cli.EXIT_OK, cli.EXIT_ERROR)


def test_optional_llm_enrichment_degrades_gracefully_when_the_allowance_is_spent(tmp_path, rsettings):
    """Real run: 5 agent requests used the whole allowance; the analyst's optional tone call (a 6th) was refused.
    That refusal must be reported as a limitation, not crash the run."""
    import yaml
    from studio.tools.instagram import ManualImportInstagram
    ig = tmp_path / "ig.yaml"
    ig.write_text(yaml.safe_dump({"provenance": {"collected_by": "o", "method": "m", "collected_at": "d", "source_description": "s"},
                                  "posts": [dict(shortcode="A1", url="https://www.instagram.com/p/A1/", type="Video",
                                                 timestamp="2026-10-20T16:00:00.000Z", caption="Zdravo", owner="gymbeamhr",
                                                 likes=1, comments=0, hashtags=[])]}))
    t = fx.site(with_products=False, apify=False)
    replies(t, decide(tool="web_fetch", args={"url": fx.SITE}, rationale="home"),
            decide(tool="instagram_fetch", args={"handle": "gymbeamhr"}, rationale="posts"))
    llm = llm_over(guarded(t, 2), max_requests=2)  # exactly the two research requests, nothing left for enrichment
    orch, _ = make(tmp_path, rsettings, t, llm=llm, ig=ManualImportInstagram(ig))
    res = orch.run("deg1", brief=fx.brief(seed_urls=[], focus_keywords=[]))
    prof = res.values["brand_profile"]["profile"]
    assert prof["analysis_mode"] == "heuristic_only" and len(posts(t)) == 2 and llm.api_requests == 2
    assert any("Optional LLM tone analysis was skipped" in x and "RequestLimitExceeded" in x for x in prof["limitations"])
    assert any(o["status"] == "unknown" and "Qualitative tone" in o["statement"] for o in prof["communication_tone"])
