"""Per-post subgraph: produce -> gates -> reviewers -> judge -> (repair loop).

Each post runs this compiled subgraph with its own state, so a repair in one post can
never touch another post's state or artifacts.
"""
from langgraph.graph import END, START, StateGraph

from studio.contracts import PostFormat, PostState, PostStatus, QAFinding
from studio.fingerprint import fingerprint
from studio.nodes import gates, qa
from studio.nodes.producers import PRODUCER_NAME, make_producer
from studio.services import Services
from studio.state import PostWF

REVIEWERS_ALL = ["brand_guardian", "creative_critic"]


def build_post_graph(svc: Services):
    g = StateGraph(PostWF)
    for fmt, name in PRODUCER_NAME.items():
        g.add_node(name, make_producer(svc, fmt))
        g.add_edge(name, "technical_validation")
    g.add_node("technical_validation", lambda s: gates.technical_validation(svc, s))
    g.add_node("evidence_validation", lambda s: gates.evidence_validation(svc, s))
    g.add_node("brand_guardian", qa.make_reviewer(svc, "brand_guardian", "review_brand", set()))
    g.add_node("creative_critic", qa.make_reviewer(
        svc, "creative_critic", "review_creative", {"carousel", "hero"}, use_vision=True))
    g.add_node("video_critic", qa.make_reviewer(svc, "video_critic", "review_video", {"reel"}))
    g.add_node("qa_judge", qa.make_judge(svc))
    g.add_node("repair", qa.repair)

    g.add_conditional_edges(START, lambda s: PRODUCER_NAME[s["plan_post"]["format"]],
                            list(PRODUCER_NAME.values()))
    g.add_edge("technical_validation", "evidence_validation")

    def after_gates(s: dict) -> list[str]:
        if s.get("gate_findings"):  # deterministic failure: skip paid review, go straight to the judge
            return ["qa_judge"]
        return REVIEWERS_ALL + (["video_critic"] if s["plan_post"]["format"] == "reel" else [])

    g.add_conditional_edges("evidence_validation", after_gates,
                            [*REVIEWERS_ALL, "video_critic", "qa_judge"])
    for r in (*REVIEWERS_ALL, "video_critic"):
        g.add_edge(r, "qa_judge")

    g.add_conditional_edges(
        "qa_judge", lambda s: "repair" if s["decision"]["verdict"] == "repair" else END,
        {"repair": "repair", END: END})
    g.add_conditional_edges("repair", lambda s: PRODUCER_NAME[s["plan_post"]["format"]],
                            list(PRODUCER_NAME.values()))
    return g.compile()


def make_post_node(svc: Services):
    graph = build_post_graph(svc)

    def post_workflow(payload: dict) -> dict:
        """Parent-graph node, fanned out with ``Send`` once per post."""
        post_id = payload["post_id"]
        final = graph.invoke({
            "run_id": payload["run_id"], "post_id": post_id, "plan_post": payload["plan_post"],
            "spec_fp": fingerprint(payload["plan_post"]), "brand": payload["brand"],
            "evidence": payload["evidence"], "attempt": 0, "repair_instructions": [],
            "production_history": [], "decisions": [], "gate_findings": [], "reviews": {},
        })
        decision = final["decision"]
        ps = PostState(
            post_id=post_id, format=PostFormat(final["plan_post"]["format"]),
            status=PostStatus.PASSED if decision["verdict"] == "pass" else PostStatus.ESCALATE,
            spec_fingerprint=final["spec_fp"], production_fingerprint=final["production_fp"],
            creative_spec=final["creative_spec"], artifacts=final["artifacts"],
            findings=[QAFinding.model_validate(f) for f in final["findings"]],
            decisions=final["decisions"], repair_attempts=final["attempt"],
            production_history=final["production_history"], mock=svc.is_mock)
        return {"posts": {post_id: ps.dump()},
                "events": [f"post {post_id}: {ps.status.value} after {ps.repair_attempts} repair(s)"]}

    return post_workflow
