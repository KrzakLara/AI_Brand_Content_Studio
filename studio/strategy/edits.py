"""Field-level human edits of a plan: exact-match, conflict-checked, atomic, fully re-validated, honestly attributed.

An edit file proposes replacements (or removal of a list element). Nothing is applied unless EVERY edit matches the current plan
exactly, no two edits touch the same field, every edit has been confirmed by a human, and the edited plan passes the same Pydantic
schema and evidence/safety validators as an AI-written plan (validation is never relaxed for edits). Evidence links, packshot
settings and claim bookkeeping are protected fields: edits can change words, not provenance.

Authorship is recorded as three separate facts: who PROPOSED the wording, who CONFIRMED it, and who APPLIED it. AI-proposed wording
is never recorded as human-authored; it becomes "AI suggestion confirmed by <human>" only after that human confirms it.
"""
import copy
import re
from typing import Literal

import yaml
from pydantic import Field, ValidationError, model_validator

from studio.contracts.base import Contract
from pydantic import TypeAdapter

from studio.contracts.strategy import BasisItem, CampaignPlan, CarouselProduct, Claim, DeferredClaim, PackshotUse, PeopleDecision, SlidePlan
from studio.strategy.dossier import Dossier
from studio.strategy.validate import errors, validate_plan

# words may change; provenance may not
PROTECTED = {"used", "claim_ids", "evidence_ids", "basis_quote", "as_of", "packshot_ref", "treatment", "crop_id", "status", "post_id", "claim_id",
             "address_form", "focal_product", "label_crops", "people_treatment", "product_treatment", "product_visible",
             "people_in_frame", "appear", "shot_ns", "sku", "hashtags"}
# claim_type may be corrected (the validators tie each type to the origin of its evidence); n may be renumbered after a removal
NUMERIC = {"duration_s", "total_duration_s", "n"}  # the validators still enforce sums, 12-30 s, <= 8 s per shot and 1..n numbering
NUMBER = re.compile(r"^\d+(\.\d+)?$")
PATH = re.compile(r"[A-Za-z_]\w*(\.[A-Za-z_]\w*|\[\d+\])*")
TOKEN = re.compile(r"([A-Za-z_]\w*)|\[(\d+)\]")
# structural carousel edits (the carousel concept changed from crop slides to a mixed-media story): they only accept complete blocks that pass the same
# schema + plan validators; packshot/people blocks can only take the schema's own values (selected_packshot / unaltered_cutout_composite).
BLOCKS = {"people": PeopleDecision, "packshot": PackshotUse, "product": CarouselProduct, "basis": TypeAdapter(list[BasisItem])}
ITEMS = {"claims": Claim, "deferred_claims": DeferredClaim}   # add_item appends one validated claim / deferred claim (campaign level)
STRUCTURAL = ("add_slide", "set_block", "add_item")
ACTOR = re.compile(r"^(ai|human):\S.*$")


class EditError(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


class EditItem(Contract):
    id: str
    op: Literal["replace", "remove", "add_slide", "set_block", "add_item"] = "replace"
    post: Literal["campaign", "01", "02", "03"]
    slide: int | None = None
    shot: int | None = None
    path: str
    expected: str = ""
    replacement: str | None = None
    value_json: dict | list | None = Field(default=None, description="add_slide: the complete new slide (validated as SlidePlan); set_block: the complete carousel "
                                                              "'people' (PeopleDecision) or 'packshot' (PackshotUse) block. Same schema and validators as an AI-written plan.")
    reason: str = Field(min_length=3)
    proposed_by: str = Field(description="'ai:<who>' or 'human:<who>' - who wrote the wording")
    requested_by: str | None = Field(default=None, description="optional: 'human:<who>' who asked for this change")
    confirmed_by: str | None = Field(default=None, description="the human who explicitly confirmed this edit; null = unconfirmed (preview only)")
    confirmation_source: str | None = Field(default=None, description="how/where the human confirmed or provided the wording")
    confirmation_scope: Literal["wording", "decision"] = Field(
        default="wording", description="'wording' = the human saw and confirmed these exact words; 'decision' = the human confirmed the DECISION, "
                                       "the words are AI-written and still need the human's review at the final plan approval")

    @model_validator(mode="after")
    def _shape(self):
        if not ACTOR.match(self.proposed_by):
            raise ValueError("proposed_by must look like 'ai:Claude Code' or 'human:Lara'")
        if self.requested_by and not ACTOR.match(self.requested_by):
            raise ValueError("requested_by must look like 'human:Lara'")
        numeric = re.split(r"[.\[]", self.path)[-1].rstrip("]") in NUMERIC  # a numeric edit may normalise a value's TYPE (5.0 -> 5) with the same text
        if self.op in STRUCTURAL:
            ok_path = {"add_slide": self.path == "slides", "set_block": self.path in BLOCKS, "add_item": self.path in ITEMS}[self.op]
            ok_post = self.post == ("campaign" if self.op == "add_item" else "01")
            if not (ok_post and ok_path) or self.value_json is None or self.replacement is not None:
                raise ValueError("add_slide: post '01', path 'slides'; set_block: post '01', path in " + str(sorted(BLOCKS)) + "; add_item: post 'campaign', path 'claims' or "
                                 "'deferred_claims'; all need value_json and no replacement")
            return self
        if self.value_json is not None:
            raise ValueError("value_json is only valid for add_slide / set_block / add_item")
        if self.op == "replace" and (self.replacement is None or (self.replacement == self.expected and not numeric) or not self.replacement.strip()):
            raise ValueError("replace needs a non-empty replacement that differs from expected")
        if self.op == "remove" and self.replacement is not None:
            raise ValueError("remove must not carry a replacement")
        if self.slide is not None and self.post != "01":
            raise ValueError("slide is only valid for post 01")
        if self.shot is not None and self.post != "03":
            raise ValueError("shot is only valid for post 03")
        return self


class EditFile(Contract):
    base_plan_hash: str = Field(min_length=12, description="hash of the plan these edits were prepared against (>= 12 characters)")
    edits: list[EditItem] = Field(min_length=1)


def load_edit_file(path) -> EditFile:
    try:
        return EditFile.model_validate(yaml.safe_load(open(path, encoding="utf-8").read()))
    except (OSError, yaml.YAMLError, ValidationError) as e:
        raise EditError([f"edit file is not valid: {e}"]) from e


def authorship(e: EditItem) -> str:
    human_proposed = e.proposed_by.startswith("human:")
    if e.confirmed_by is None:
        if e.op == "remove" and e.requested_by and e.requested_by.startswith("human:"):
            return "human_requested_removal_PENDING_CONFIRMATION"
        return "human_authored_UNCONFIRMED" if human_proposed else "ai_suggestion_UNCONFIRMED"
    if human_proposed:
        return "human_authored"
    if e.confirmation_scope == "decision":
        return "ai_wording_implementing_human_decision"
    if e.op == "remove" and e.requested_by and e.requested_by.startswith("human:"):
        return "human_requested_removal"
    return "ai_suggestion_confirmed_by_human"


def _tokens(path: str) -> list:
    if not PATH.fullmatch(path):
        raise EditError([f"bad path syntax {path!r} (use a.b[0].c)"])
    return [m.group(1) if m.group(1) else int(m.group(2)) for m in TOKEN.finditer(path)]


def _base(plan: dict, e: EditItem) -> list:
    head = {"campaign": [], "01": ["carousel"], "02": ["hero"], "03": ["reel"]}[e.post]
    if e.slide is not None:
        i = next((i for i, s in enumerate(plan["carousel"]["slides"]) if s["n"] == e.slide), None)
        if i is None:
            raise EditError([f"{e.id}: carousel has no slide {e.slide}"])
        return head + ["slides", i]
    if e.shot is not None:
        i = next((i for i, s in enumerate(plan["reel"]["shots"]) if s["n"] == e.shot), None)
        if i is None:
            raise EditError([f"{e.id}: reel has no shot {e.shot}"])
        return head + ["shots", i]
    return head


def _get(obj, toks):
    for t in toks:
        obj = obj[t]
    return obj


def resolve(plan: dict, e: EditItem) -> list:
    toks = _base(plan, e) + _tokens(e.path)
    bad = [t for t in toks if isinstance(t, str) and t in PROTECTED]
    if bad:
        raise EditError([f"{e.id}: field {bad[0]!r} is protected (provenance/structure cannot be edited)"])
    try:
        _get(plan, toks)
    except (KeyError, IndexError, TypeError):
        raise EditError([f"{e.id}: path {e.path!r} does not exist in the plan"]) from None
    return toks


def _current_text(value) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return f"{value:g}"
    if isinstance(value, str):
        return value
    if isinstance(value, dict):  # a list element that is an object: its text (copy line, claim), statement (basis item) or headline (slide)
        for k in ("text", "statement"):
            if isinstance(value.get(k), str):
                return value[k]
        if isinstance(value.get("headline"), dict) and isinstance(value["headline"].get("text"), str):
            return value["headline"]["text"]
    return None


def prepare(plan: dict, ef: EditFile, *, current_hash: str, require_confirmation: bool) -> list[tuple[EditItem, list, str]]:
    """Check EVERYTHING against the original plan; returns (edit, tokens, old text) or raises EditError listing all problems."""
    problems: list[str] = []
    if not current_hash.startswith(ef.base_plan_hash.strip().lower()):
        raise EditError([f"stale edit file: prepared for plan {ef.base_plan_hash[:12]}, the current plan is {current_hash[:12]}"])
    ids = [e.id for e in ef.edits]
    problems += [f"duplicate edit id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    out = []
    for e in ef.edits:
        if e.op in STRUCTURAL:  # slides are appended after all replacements/removals; blocks replace the whole carousel block
            model = SlidePlan if e.op == "add_slide" else (ITEMS[e.path] if e.op == "add_item" else BLOCKS[e.path])
            try:
                (model.validate_python if isinstance(model, TypeAdapter) else model.model_validate)(e.value_json)
            except ValidationError as x:
                problems.append(f"{e.id}: value_json is not valid for {e.op} {e.path}: {x.errors()[0]['loc']} {x.errors()[0]['msg']}")
            if require_confirmation and not (e.confirmed_by and e.confirmed_by.strip() and e.confirmation_source and e.confirmation_source.strip()):
                problems.append(f"{e.id}: not confirmed by a human (confirmed_by + confirmation_source required to apply; use --dry-run to preview)")
            out.append((e, {"add_slide": ["carousel", "slides", f"new:{e.id}"], "add_item": [e.path, f"new:{e.id}"]}.get(e.op, ["carousel", e.path]), ""))
            continue
        try:
            toks = resolve(plan, e)
        except EditError as x:
            problems += x.problems
            continue
        old = _current_text(_get(plan, toks))
        if old is None:
            problems.append(f"{e.id}: {e.path!r} is not a text field")
        elif old != e.expected:
            problems.append(f"{e.id}: stale/mismatched original - expected {e.expected!r} but the plan has {old!r}")
        if e.op == "remove" and not isinstance(toks[-1], int):
            problems.append(f"{e.id}: remove needs a list element path such as supporting_copy[0]")
        cur = _get(plan, toks)
        numeric = toks[-1] in NUMERIC
        if e.op == "replace" and not (isinstance(cur, str) or numeric):
            problems.append(f"{e.id}: replace targets a text value, not {e.path!r}'s object (use .text)")
        if numeric and e.op == "replace" and not NUMBER.match(e.replacement or ""):
            problems.append(f"{e.id}: {toks[-1]} needs a plain number such as 1.5")
        if require_confirmation:
            if not (e.confirmed_by and e.confirmed_by.strip() and e.confirmation_source and e.confirmation_source.strip()):
                problems.append(f"{e.id}: not confirmed by a human (confirmed_by + confirmation_source required to apply; use --dry-run to preview)")
            elif e.proposed_by.startswith("human:") and e.confirmed_by.strip().lower() != e.proposed_by[6:].strip().lower():
                problems.append(f"{e.id}: human-authored wording must be confirmed by the same human ({e.proposed_by[6:]!r}), not {e.confirmed_by!r}")
        out.append((e, toks, old or ""))
    for i, (_, a, _) in enumerate(out):  # conflicts: same field twice, or an edit inside a removed element
        for _, b, _ in out[i + 1:]:
            if a == b or a[:len(b)] == b or b[:len(a)] == a:
                problems.append(f"conflicting edits touch the same field: {'.'.join(map(str, a))} / {'.'.join(map(str, b))}")
    if problems:
        raise EditError(problems)
    return out


def apply_all(plan: dict, prepared) -> dict:
    """Atomic by construction: works on a copy; the caller only persists the returned plan after validation."""
    new = copy.deepcopy(plan)
    for e, toks, _ in prepared:  # replacements first: they address the ORIGINAL positions
        if e.op == "replace":
            _get(new, toks[:-1])[toks[-1]] = (int(float(e.replacement)) if toks[-1] == "n" else float(e.replacement)) if toks[-1] in NUMERIC else e.replacement
    removes = [t for e, t, _ in prepared if e.op == "remove"]
    for toks in sorted(removes, key=lambda t: (".".join(map(str, t[:-1])), t[-1]), reverse=True):  # highest index first within a list
        del _get(new, toks[:-1])[toks[-1]]
    for e, _, _ in prepared:
        if e.op == "add_slide":
            new["carousel"]["slides"].append(copy.deepcopy(e.value_json))
        elif e.op == "set_block":
            new["carousel"][e.path] = copy.deepcopy(e.value_json)
        elif e.op == "add_item":
            new[e.path].append(copy.deepcopy(e.value_json))
    return new


def validated(new_plan: dict, d: Dossier) -> tuple[CampaignPlan, list[str]]:
    """Same schema + same validators as an AI-written plan. Raises EditError on any blocking problem; returns non-blocking flags."""
    try:
        plan = CampaignPlan.model_validate(new_plan)
    except ValidationError as e:
        raise EditError([f"edited plan violates the schema: {e.errors()[0]['loc']} {e.errors()[0]['msg']}"]) from e
    allp = validate_plan(plan, d)
    if errors(allp):
        raise EditError([f"edited plan fails validation: {p}" for p in errors(allp)])
    return plan, [str(p) for p in allp if p.severity == "flag"]


def records(prepared, new_plan: dict) -> list[dict]:
    out = []
    for e, toks, old in prepared:
        out.append({"id": e.id, "op": e.op, "post": e.post, "slide": e.slide, "shot": e.shot, "path": e.path, "old_value": old,
                    "new_value": e.replacement if e.op == "replace" else (e.value_json if e.op in STRUCTURAL else None), "reason": e.reason, "proposed_by": e.proposed_by,
                    "requested_by": e.requested_by, "confirmed_by": e.confirmed_by, "confirmation_source": e.confirmation_source,
                    "confirmation_scope": e.confirmation_scope,
                    "authorship": authorship(e)})
    return out
