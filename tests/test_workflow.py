"""Phase 1 acceptance tests A-G, I."""
import json

import pytest

from studio.contracts import Gate, OperationStatus, PostStatus, RunStatus
from studio.providers.mock import SimulatedCrash


def posts_of(res):
    return res.values["posts"]


# A ------------------------------------------------------------------------
def test_a_mock_workflow_completes_end_to_end(make_orch, brief, tmp_path):
    orch = make_orch()
    res = orch.run(brief=brief)
    assert res.status == RunStatus.COMPLETED.value
    out = tmp_path / "submission" / res.run_id
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["mock"] is True and manifest["run_status"] == "completed"
    assert (out / "MOCK_NOTICE.txt").is_file()
    assert manifest["total_estimated_cost_usd"] == 0
    for post in manifest["posts"]:
        assert post["status"] == "exported" and post["artifacts"]
        for a in post["artifacts"]:
            assert (out / a["exported_path"]).is_file()
            assert a["artifact"]["mock"] is True


# B ------------------------------------------------------------------------
def test_b_three_posts_have_distinct_state_and_artifacts(make_orch, brief):
    posts = posts_of(make_orch().run(brief=brief))
    assert sorted(posts) == ["01", "02", "03"]
    assert [posts[p]["format"] for p in sorted(posts)] == ["carousel", "hero", "reel"]
    assert len({p["spec_fingerprint"] for p in posts.values()}) == 3
    assert len({p["production_fingerprint"] for p in posts.values()}) == 3
    ids = [a["artifact_id"] for p in posts.values() for a in p["artifacts"]]
    assert len(ids) == len(set(ids))
    for pid, p in posts.items():
        assert all(a["post_id"] == pid for a in p["artifacts"])
        assert all(a["relpath"].startswith(f"artifacts/post_{pid}/") for a in p["artifacts"])
    assert len([a for a in posts["01"]["artifacts"] if a["kind"] == "image"]) == 5
    assert any(a["kind"] == "video_placeholder" for a in posts["03"]["artifacts"])


# C ------------------------------------------------------------------------
def test_c_resume_after_crash_does_not_repeat_completed_operations(make_orch, brief):
    crashing = make_orch(crash_post="03")
    with pytest.raises(SimulatedCrash):
        crashing.run("run-crash", brief=brief)
    with crashing.open("run-crash") as (svc, *_):
        before = svc.ledger.list("run-crash")
    done_before = {o.idempotency_key for o in before if o.status == OperationStatus.DONE}
    ids_before = {o.operation_id for o in before}
    assert done_before, "something must have completed before the crash"
    assert crashing.providers.video.calls, "the crash happened inside the video call"

    resumed = make_orch()  # new providers = new process
    res = resumed.run("run-crash")
    assert res.status == RunStatus.COMPLETED.value
    with resumed.open("run-crash") as (svc, *_):
        after = svc.ledger.list("run-crash")
    new_ops = [o for o in after if o.operation_id not in ids_before]
    assert new_ops
    assert not {o.idempotency_key for o in new_ops} & done_before  # nothing finished was redone
    dup_done = [o.idempotency_key for o in after if o.status == OperationStatus.DONE]
    assert len(dup_done) == len(set(dup_done))
    # the interrupted video call is recorded as unknown, never silently assumed done
    assert any(o.status == OperationStatus.UNKNOWN and o.node == "reel_producer" for o in after)
    assert len(resumed.providers.video.calls) == 1


# D ------------------------------------------------------------------------
def llm_tasks(orch):
    return {c["task"] for c in orch.providers.llm.calls}


def test_d_unchanged_input_is_fully_cached(make_orch, brief):
    make_orch().run("run-d0", brief=brief)
    again = make_orch()
    again.run("run-d0", brief=brief)
    assert again.providers.llm.calls == [] and again.providers.research.calls == []
    assert again.providers.image.calls == [] and again.providers.video.calls == []


def test_d_changed_goal_invalidates_plan_and_production_only(make_orch, brief):
    make_orch().run("run-d1", brief=brief)
    again = make_orch()
    again.run("run-d1", brief=brief.model_copy(update={"campaign_goal": "Promote a new flavour"}))
    tasks = llm_tasks(again)
    assert {"content_plan", "creative_spec"} <= tasks
    assert not tasks & {"research_policy", "brand_profile"}  # research + analysis stay cached
    assert again.providers.research.calls == []


def test_d_changed_audience_invalidates_analysis_but_not_research(make_orch, brief):
    make_orch().run("run-d2", brief=brief)
    again = make_orch()
    again.run("run-d2", brief=brief.model_copy(update={"audience": "Marathon runners"}))
    assert "brand_profile" in llm_tasks(again) and "research_policy" not in llm_tasks(again)
    assert again.providers.research.calls == []


def test_d_changed_brand_invalidates_research(make_orch, brief):
    make_orch().run("run-d3", brief=brief)
    again = make_orch()
    again.run("run-d3", brief=brief.model_copy(update={"brand_name": "OtherBrand"}))
    assert again.providers.research.calls


# E ------------------------------------------------------------------------
def test_e_repair_in_post_03_leaves_posts_01_and_02_untouched(make_orch, brief):
    base = posts_of(make_orch().run("run-e-base", brief=brief))
    fixed = posts_of(make_orch(fail_rounds={"03": 1}).run("run-e-fail", brief=brief))
    assert fixed["03"]["repair_attempts"] == 1 and fixed["03"]["status"] == PostStatus.EXPORTED.value
    for pid in ("01", "02"):
        assert fixed[pid]["production_fingerprint"] == base[pid]["production_fingerprint"]
        assert fixed[pid]["artifacts"] == base[pid]["artifacts"]
        assert fixed[pid]["repair_attempts"] == 0
    assert fixed["03"]["production_fingerprint"] != base["03"]["production_fingerprint"]
    assert len(fixed["03"]["production_history"]) == 2
    assert [a["sha256"] for a in fixed["03"]["artifacts"]] != [a["sha256"] for a in base["03"]["artifacts"]]


def test_e_redo_single_post_in_existing_run(make_orch, brief):
    first = make_orch()
    before = posts_of(first.run("run-e2", brief=brief))
    with first.open("run-e2") as (svc, *_):
        ops_before = {s: len(svc.ledger.list("run-e2", scope=s)) for s in ("01", "02", "03")}
    redo = make_orch(fail_rounds={"03": 1})
    after = posts_of(redo.run("run-e2", post="03"))
    assert after["01"] == before["01"] and after["02"] == before["02"]
    assert after["03"]["repair_attempts"] == 1
    with redo.open("run-e2") as (svc, *_):
        ops_after = {s: len(svc.ledger.list("run-e2", scope=s)) for s in ("01", "02", "03")}
    assert ops_after["01"] == ops_before["01"] and ops_after["02"] == ops_before["02"]
    assert ops_after["03"] > ops_before["03"]
    assert all(c.get("post_id") in (None, "03") for c in redo.providers.llm.calls)


def test_forced_redo_from_stage_makes_new_operations(make_orch, brief):
    make_orch().run("run-f", brief=brief)
    again = make_orch()
    again.run("run-f", from_stage="plan")
    assert "content_plan" in llm_tasks(again) and again.providers.image.calls  # not a silent replay
    assert again.providers.research.calls == []


# F ------------------------------------------------------------------------
def test_f_approval_replay_only_for_matching_hashes(make_orch, brief):
    manual = make_orch(auto=False)
    r = manual.run("run-f1", brief=brief)
    assert r.status == RunStatus.AWAITING_APPROVAL.value and r.paused_at["gate"] == "plan"
    manual.approve("run-f1", Gate.PLAN, approver="tester")
    r = manual.run("run-f1")
    assert r.paused_at["gate"] == "final"
    manual.approve("run-f1", Gate.FINAL, approver="tester")
    assert manual.run("run-f1").status == RunStatus.COMPLETED.value
    with manual.open("run-f1") as (svc, *_):
        recorded = svc.store.approvals("run-f1")
    assert {a.source.value for a in recorded} == {"human_cli"}

    # same content, different run: recorded approvals replay and nothing pauses
    replay = make_orch(auto=False, approvals=recorded)
    assert replay.run("run-f2", brief=brief).status == RunStatus.COMPLETED.value

    # changed brief -> different plan fingerprint -> stale approval is ignored, run pauses
    stale = make_orch(auto=False, approvals=recorded)
    r = stale.run("run-f3", brief=brief.model_copy(update={"campaign_goal": "Something else"}))
    assert r.status == RunStatus.AWAITING_APPROVAL.value and r.paused_at["gate"] == "plan"
    assert r.paused_at["stale_approvals_ignored"] is True

    # tampered hash is not honoured either
    tampered = [a.model_copy(update={"artifact_fingerprint": "0" * 64}) for a in recorded]
    r = make_orch(auto=False, approvals=tampered).run("run-f4", brief=brief)
    assert r.status == RunStatus.AWAITING_APPROVAL.value


def test_f_rejection_stops_the_run(make_orch, brief):
    orch = make_orch(auto=False)
    orch.run("run-rej", brief=brief)
    orch.approve("run-rej", Gate.PLAN, approver="tester", reject=True)
    assert orch.run("run-rej").status == RunStatus.REJECTED.value


def test_mock_auto_approval_is_labelled_and_mock_only(make_orch, brief):
    orch = make_orch()
    orch.run("run-auto", brief=brief)
    with orch.open("run-auto") as (svc, *_):
        recs = svc.store.approvals("run-auto")
    assert recs and all(r.source.value == "mock_auto" and r.mock for r in recs)


# G ------------------------------------------------------------------------
def test_g_escalate_after_two_failed_repairs(make_orch, brief, tmp_path):
    orch = make_orch(fail_rounds={"03": 99})
    res = orch.run("run-g", brief=brief)
    p = posts_of(res)
    assert p["03"]["status"] == PostStatus.ESCALATE.value and p["03"]["repair_attempts"] == 2
    assert [d["verdict"] for d in p["03"]["decisions"]] == ["repair", "repair", "escalate"]
    assert p["01"]["status"] == p["02"]["status"] == PostStatus.EXPORTED.value
    assert res.status == RunStatus.COMPLETED_WITH_ESCALATIONS.value
    out = tmp_path / "submission" / "run-g" / "post_03_reel"
    assert (out / "ESCALATED.json").is_file() and not (out / "reel.mock.json").exists()


def test_g_one_repair_is_enough_when_it_fixes_the_defect(make_orch, brief):
    p = posts_of(make_orch(fail_rounds={"03": 1}).run("run-g1", brief=brief))
    assert p["03"]["repair_attempts"] == 1 and p["03"]["status"] == PostStatus.EXPORTED.value


# I ------------------------------------------------------------------------
def test_i_parallel_branches_merge_state_correctly(make_orch, brief):
    orch = make_orch(fail_rounds={"02": 1, "03": 2})
    res = orch.run("run-i", brief=brief)
    posts = posts_of(res)
    assert sorted(posts) == ["01", "02", "03"]
    assert [posts[p]["repair_attempts"] for p in ("01", "02", "03")] == [0, 1, 2]
    for pid, p in posts.items():
        assert p["post_id"] == pid and all(a["post_id"] == pid for a in p["artifacts"])
    assert sum(e.startswith("post ") for e in res.values["events"]) == 3
    with orch.open("run-i") as (svc, *_):
        nodes = {s: {o.node for o in svc.ledger.list("run-i", scope=s)} for s in ("01", "02", "03")}
    assert {"brand_guardian", "creative_critic", "qa_judge"} <= nodes["01"]
    assert "video_critic" in nodes["03"] and "video_critic" not in nodes["01"] | nodes["02"]
