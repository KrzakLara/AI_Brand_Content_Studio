"""Parent LangGraph: research -> analysis -> plan -> approval -> posts (parallel) -> approval -> export."""
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from studio.contracts import POST_IDS, ContentPlan, RunStatus
from studio.nodes import approvals, export, research
from studio.nodes.post_workflow import make_post_node
from studio.services import Services
from studio.state import GraphState


def build_graph(svc: Services, checkpointer, until: str | None = None):
    """``until="analyst"`` cuts the graph after the research teams (the Phase 2 research workflow)."""
    g = StateGraph(GraphState)
    g.add_node("research_agent", lambda s: research.research_agent(svc, s))
    g.add_node("brand_product_analyst", lambda s: research.brand_product_analyst(svc, s))
    g.add_edge(START, "research_agent")
    g.add_edge("research_agent", "brand_product_analyst")
    if until == "analyst":
        g.add_edge("brand_product_analyst", END)
        return g.compile(checkpointer=checkpointer)
    g.add_node("content_planner", lambda s: research.content_planner(svc, s))
    g.add_node("approve_plan", lambda s: approvals.approve_plan(svc, s))
    g.add_node("post_workflow", make_post_node(svc))
    g.add_node("approve_final", lambda s: approvals.approve_final(svc, s))
    g.add_node("exporter", lambda s: export.exporter(svc, s))

    g.add_edge("brand_product_analyst", "content_planner")
    g.add_edge("content_planner", "approve_plan")

    def dispatch(s: GraphState):
        if s.get("status") == RunStatus.REJECTED.value:
            return END
        plan = ContentPlan.model_validate(s["plan"]["plan"])
        only = s.get("only_posts")
        return [
            Send("post_workflow", {
                "run_id": s["run_id"], "post_id": pid, "plan_post": plan.post(pid).dump(),
                "brand": s["brand_profile"]["profile"], "evidence": s["research"]["evidence"]})
            for pid in POST_IDS if only is None or pid in only
        ]

    g.add_conditional_edges("approve_plan", dispatch, ["post_workflow", END])
    # post_workflow branches run in one superstep; approve_final starts after all of them
    g.add_edge("post_workflow", "approve_final")
    g.add_conditional_edges(
        "approve_final", lambda s: END if s.get("status") == RunStatus.REJECTED.value else "exporter",
        {"exporter": "exporter", END: END})
    g.add_edge("exporter", END)
    return g.compile(checkpointer=checkpointer)
