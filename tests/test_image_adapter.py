"""OpenAI image-edit adapter: spend guard and accounting, recorded transport only (no network, no key, no cost)."""
import base64
import json

import pytest

from studio.cost import BudgetExceeded
from studio.providers.live import OPENAI_IMAGE_EDIT_URL, OpenAIImageEdit, RequestLimitExceeded
from studio.tools.transport import RecordedTransport

PNG = base64.b64encode(b"png-bytes").decode()
REPLY = {"data": [{"b64_json": PNG}], "usage": {"input_tokens": 3000, "output_tokens": 10000,
                                                "input_tokens_details": {"text_tokens": 500, "image_tokens": 2500}}}


def adapter(tmp_path, **kw):
    t = RecordedTransport().add(OPENAI_IMAGE_EDIT_URL, method="POST", body=json.dumps(REPLY), content_type="application/json",
                                headers={"x-request-id": "req_1"})
    return OpenAIImageEdit("gpt-image-2.5-sunburst", t, api_key="sk-SECRET", budget_usd=5.0, max_requests=2,
                           usage_path=tmp_path / "u.jsonl", **kw), t


def call(a):
    return a.edit(image=b"i", mask=b"m", prompt="p", size="1600x2000", quality="xhigh")


def test_actual_cost_comes_from_the_usage_block_and_the_key_is_never_logged(tmp_path):
    a, t = adapter(tmp_path)
    r = call(a)
    assert r["png"] == b"png-bytes"
    assert r["cost_usd"] == pytest.approx(500 * 5e-6 + 2500 * 8e-6 + 10000 * 30e-6)  # 0.3225
    assert a.remaining_usd() == pytest.approx(5.0 - 0.3225)
    assert "sk-SECRET" not in (tmp_path / "u.jsonl").read_text()


def test_the_guard_refuses_when_the_worst_case_does_not_fit_and_when_the_request_cap_is_reached(tmp_path):
    a, t = adapter(tmp_path)
    a.budget_usd = 1.0  # worst case 2.12 USD
    with pytest.raises(BudgetExceeded):
        call(a)
    assert t.calls == []  # nothing was sent
    b, t2 = adapter(tmp_path / "b")
    call(b), call(b)
    with pytest.raises(RequestLimitExceeded):
        call(b)
    assert len(t2.calls) == 2


def test_a_second_request_must_fit_with_1_5x_the_largest_cost_seen(tmp_path):
    a, _ = adapter(tmp_path, worst_in_tokens=0, worst_out_tokens=0)
    a.budget_usd = 0.4
    call(a)  # costs 0.3225
    with pytest.raises(BudgetExceeded):
        call(a)


def test_an_api_error_never_echoes_a_key_shaped_string(tmp_path):
    from studio.providers.base import ProviderResponseError
    t = RecordedTransport().add(OPENAI_IMAGE_EDIT_URL, method="POST", status=401, content_type="application/json",
                                body=json.dumps({"error": {"message": "Incorrect API key provided: sk-proj-*****abc-. Find it at ..."}}))
    a = OpenAIImageEdit("m", t, api_key="sk-SECRET", budget_usd=5.0, max_requests=2)
    with pytest.raises(ProviderResponseError) as e:
        call(a)
    assert "sk-" not in str(e.value) and "401" in str(e.value)
