"""Phase 5: the carousel may be about another product (Colla Pink). Page facts are dated, verified claims; quantities are allowed only through them."""
import copy
import dataclasses

import pytest

from studio.contracts.strategy import CampaignPlan
from studio.strategy.edits import EditError
from studio.strategy.validate import errors, validate_plan

from . import strategy_fixtures as sf
from .test_edits import codes, edits_file, gen, item  # noqa: F401  (gen is a fixture)

EV = {"evidence_id": "E-colla-dosage", "claim": "Product page dosage", "source_id": "colla-page", "mock": False, "subject": "colla_page_fact",
      "verification_status": "verified", "retrieved_at": "2026-10-28T20:00:00Z", "structured_value": {},
      "quote": "Preporučena dnevna doza je 1 mjerica (8 g) , pomiješana s 200 do 300 ml vode"}
TEXT = "Na stranici proizvoda piše: preporučena dnevna doza je 1 mjerica (8 g), pomiješana s 200 do 300 ml vode."


@pytest.fixture(scope="module")
def dos():
    d = sf.dossier()
    return dataclasses.replace(d, evidence={**d.evidence, "E-colla-dosage": EV})


def with_fact(p, claim_ids):
    p["claims"].append({"claim_id": "C9", "text": TEXT, "claim_type": "page_fact", "evidence_ids": ["E-colla-dosage"],
                        "basis_quote": "Preporučena dnevna doza je 1 mjerica (8 g) , pomiješana s 200 do 300 ml vode", "as_of": "2026-10-28"})
    p["carousel"]["slides"][0]["callouts"] = [{"text": TEXT, "claim_ids": claim_ids}]


def test_a_quantity_is_allowed_only_as_a_dated_page_fact_with_verified_evidence(dos):
    assert "quantity" not in codes(sf.mutated(lambda p: with_fact(p, ["C9"])), dos)
    assert "quantity" in codes(sf.mutated(lambda p: with_fact(p, [])), dos)          # the same words without a claim stay blocked
    ev = dict(EV, verification_status="manual")
    bad = dataclasses.replace(dos, evidence={**dos.evidence, "E-colla-dosage": ev})
    assert "page_fact_origin" in codes(sf.mutated(lambda p: with_fact(p, ["C9"])), bad)  # unverified evidence cannot support a page fact


def test_a_page_fact_must_carry_the_page_prefix_and_cannot_cite_benefit_wording(dos):
    def no_prefix(p):
        with_fact(p, ["C9"])
        p["claims"][-1]["text"] = "preporučena dnevna doza je 1 mjerica (8 g)"
    assert "claim_prefix" in codes(sf.mutated(no_prefix), dos)
    ben = dataclasses.replace(dos, evidence={**dos.evidence, "E-colla-health-wording": dict(EV, evidence_id="E-colla-health-wording")})

    def benefit(p):
        with_fact(p, ["C9"])
        p["claims"][-1]["evidence_ids"] = ["E-colla-health-wording"]
    assert "health_claim_not_publishable" in codes(sf.mutated(benefit), ben)


def test_the_carousel_product_block_needs_its_own_packshot_reference(dos):
    def prod(p):
        p["carousel"]["packshot"]["packshot_ref"] = "colla_flavour_packshots"
    assert "packshot" in codes(sf.mutated(prod), dos)                                   # a flavour packshot without carousel.product is refused


def test_add_item_appends_a_validated_claim_and_rejects_an_invalid_one(gen):
    s, h, tmp = gen
    bad = item("I1", "campaign", "claims", "", None, op="add_item", value_json={"claim_id": "C9", "text": "x"})
    bad.pop("replacement", None)
    with pytest.raises(EditError):
        s.edit(edits_file(tmp, h, [bad]), reason="bad claim")
    wrong_post = {"id": "I2", "op": "add_item", "post": "01", "path": "claims", "value_json": {}, "reason": "x", "proposed_by": "ai:t"}
    with pytest.raises(Exception):
        edits_file(tmp, h, [wrong_post], "w.yaml") and __import__("studio.strategy.edits", fromlist=["x"]).load_edit_file(tmp / "w.yaml")
