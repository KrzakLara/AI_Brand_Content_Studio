"""LangGraph state schemas.

Only small JSON values live here (contract dumps, artifact references, fingerprints).
Media bytes stay on disk. ``posts`` is merged per key so parallel branches, each writing
only their own post, can never overwrite one another.
"""
import operator
from typing import Annotated, TypedDict


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    return {**(left or {}), **(right or {})}


class GraphState(TypedDict, total=False):
    run_id: str
    brief: dict
    only_posts: list[str] | None  # restrict (re)production to these posts
    research: dict  # {source_index, evidence, trace, fingerprint}
    brand_profile: dict  # {profile, fingerprint}
    plan: dict  # {plan, fingerprint}
    plan_approval: dict
    final_approval: dict
    posts: Annotated[dict, merge_dicts]  # post_id -> PostState dump
    events: Annotated[list, operator.add]
    status: str
    manifest: dict


class PostWF(TypedDict, total=False):
    """State of one post subgraph."""

    run_id: str
    post_id: str
    plan_post: dict
    spec_fp: str
    brand: dict
    evidence: dict
    attempt: int
    repair_instructions: list[str]
    creative_spec: dict
    artifacts: list[dict]
    production_fp: str
    production_history: list[str]
    gate_findings: list[dict]
    reviews: Annotated[dict, merge_dicts]  # reviewer -> findings (overwritten each round)
    decision: dict
    decisions: list[dict]
    findings: list[dict]
    status: str
