"""What the first real Haiku 5.5 run exposed: the model must be told the tools, and failures must keep their evidence."""
import json
from pathlib import Path

import yaml

from studio import cli
from studio.nodes.research_live import TOOL_CATALOG, _refuse
from studio.providers.base import ResearchStep
from studio.providers.live import ANTHROPIC_URL
from studio.tools.transport import RecordedTransport

from . import research_fixtures as fx
from .test_research import dump_transport, make
from .test_spend import KEY, ROOT, metered, tool_reply


def step(**kw):
    return {"action": "tool", **kw}


def test_the_model_is_told_the_exact_tool_names_and_allowed_hosts(tmp_path, rsettings):
    t = fx.site(with_products=False, apify=False)
    t.add(ANTHROPIC_URL, **tool_reply({"action": "finish"}))
    llm = metered(t, budget=1.0, pin=0.1, pout=0.5)
    orch, _ = make(tmp_path, rsettings, t, llm=llm)
    try:
        orch.run("tc", brief=fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]))
    except Exception:  # no source retrieved is expected here; we only inspect the request
        pass
    sent = t.bodies[-1].decode()
    data = json.loads(sent)["messages"][0]["content"].rsplit("<data>", 1)[1].split("</data>")[0]
    payload = json.loads(data)
    assert set(payload["tools"]) == {"web_fetch", "instagram_fetch", "download_image"} == set(TOOL_CATALOG)
    assert payload["allowed_hosts"] == ["gymbeam.hr"] and "do not guess paths" in payload["tools"]["web_fetch"]["args"]["url"]
    assert KEY not in sent


def test_refusing_an_unknown_tool_tells_the_model_what_is_valid():
    msg = _refuse(ResearchStep(action="tool", tool="fetch_page", args={"url": "u"}),
                  ("web_fetch", "instagram_fetch", "download_image"), set())
    assert "unknown tool 'fetch_page'" in msg and "valid tools are exactly: web_fetch, instagram_fetch, download_image" in msg


def test_failed_paid_run_exits_cleanly_and_saves_the_real_evidence(tmp_path, monkeypatch, capsys):
    """Model guesses wrong tool names and a 404 URL (what Haiku really did): no crash, a report with its reasons."""
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    t = fx.site(with_products=False, apify=False)
    t.add(f"{fx.SITE}/kreatin.html", status=404, body="gone")
    t.add("https://api.anthropic.com/v1/models/claude-haiku-5-5", body=json.dumps({"id": "claude-haiku-5-5"}),
          content_type="application/json")
    seq = [step(tool="fetch_page", args={"url": fx.SITE}, rationale="homepage first"),
           step(tool="web_fetch", args={"url": f"{fx.SITE}/kreatin.html"}, rationale="guess the category page")]
    for s in seq:
        t.add(ANTHROPIC_URL, **tool_reply(s, tin=1300, tout=150))
    fixdir, out = tmp_path / "fx", tmp_path / "out"
    dump_transport(t, fixdir)
    conf = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    conf["anthropic_pricing"]["claude-haiku-5-5"].update(input_usd_per_mtok=0.1, output_usd_per_mtok=0.5)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump(conf), encoding="utf-8")
    brief = tmp_path / "b.yaml"
    brief.write_text(yaml.safe_dump(fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]).model_dump(mode="json")))
    rc = cli.main(["--config", str(cfg), "--runs-dir", str(tmp_path / "runs"), "research", "--brief", str(brief),
                   "--mode", "fixture", "--fixtures", str(fixdir), "--policy", "anthropic", "--model", "claude-haiku-5-5",
                   "--instagram", "none", "--max-steps", "2", "--max-api-spend-usd", "0.10", "--max-requests", "5",
                   "--run", "fail1", "--out", str(out)])
    err = capsys.readouterr().err
    assert rc == cli.EXIT_ERROR and "research failed: ResearchFailed" in err and "api accounting: 3/5 requests" in err
    assert "Traceback" not in err and KEY not in err
    rep = json.loads((out / "run_summary.json").read_text(encoding="utf-8"))
    assert rep["status"] == "failed" and rep["policy_autonomous"] is True
    assert [d["tool"] for d in rep["model_decisions"]] == ["fetch_page", "web_fetch"]
    assert rep["model_decisions"][0]["reason"] == "homepage first"  # the model's own stated reason is preserved
    assert rep["tool_results"] == [{"step": "s1:web_fetch", "ok": False, "error": "http_error: HTTP 404",
                                    "urls": [f"{fx.SITE}/kreatin.html"]}]
    assert rep["api"]["message_requests"] == 2 and rep["api"]["input_tokens"] == 2600
    assert KEY not in json.dumps(rep) and KEY not in (out / "api_usage.jsonl").read_text(encoding="utf-8")


def test_trace_from_ledger_rebuilds_the_step_sequence(tmp_path):
    from studio.contracts import OperationStatus
    from studio.ledger import Ledger
    from studio.providers.live import AnthropicLLM
    ledger = Ledger(tmp_path / "s.db")
    info = AnthropicLLM("m", RecordedTransport(), api_key=None).info
    for key, ok in (("s0:policy", True), ("s0:web_fetch", True), ("s1:policy", False)):
        op = ledger.begin("r", "research_agent", "run", info, f"run|research|fp|g0|{key}")
        ledger.complete(op, {"x": 1}, None, __import__("studio.contracts", fromlist=["CostRecord"]).CostRecord(
            operation_id=op, run_id="r", node="n", provider="p", kind=info.kind, model_id="m", units=1, unit="call",
            estimated_usd=0.0)) if ok else ledger.fail(op, "boom")
    steps = cli.trace_from_ledger(ledger.list("r"))
    assert steps[0] == {"step": 0, "policy_status": OperationStatus.DONE.value, "tool_status": "done", "tool_called": "web_fetch"}
    assert steps[1]["policy_status"] == "failed" and steps[1]["policy_error"] == "boom"
    assert Path(tmp_path / "s.db").exists()
