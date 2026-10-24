
import json

import pytest

from app.structured_output import parse_structured_answer


ALLOWED = {"shipping-3", "returns-3"}


def build_response(source_id="shipping-3"):
    return json.dumps({
        "status": "answered",
        "answer": "Express shipping costs €9.90.",
        "claims": [
            {
                "text": "Express shipping costs €9.90.",
                "source_ids": [source_id],
            }
        ],
    })


def test_valid_structured_answer():
    result = parse_structured_answer(
        build_response(),
        ALLOWED,
    )

    assert result.status == "answered"
    assert result.answer == "Express shipping costs €9.90."
    assert result.claims[0]["source_ids"] == ["shipping-3"]


def test_rejects_invalid_json():
    with pytest.raises(ValueError, match="Invalid model JSON"):
        parse_structured_answer("not json", ALLOWED)


def test_rejects_unknown_source():
    with pytest.raises(ValueError, match="unknown source"):
        parse_structured_answer(
            build_response("invented-99"),
            ALLOWED,
        )


def test_rejects_missing_evidence():
    payload = json.loads(build_response())
    payload["claims"][0]["source_ids"] = []

    with pytest.raises(ValueError, match="no evidence"):
        parse_structured_answer(
            json.dumps(payload),
            ALLOWED,
        )


def test_rejects_empty_claims_for_answered_status():
    payload = json.loads(build_response())
    payload["claims"] = []

    with pytest.raises(ValueError, match="No supported claims"):
        parse_structured_answer(
            json.dumps(payload),
            ALLOWED,
        )


def test_rejects_invalid_claim_text():
    payload = json.loads(build_response())
    payload["claims"][0]["text"] = ""

    with pytest.raises(ValueError, match="Invalid claim text"):
        parse_structured_answer(
            json.dumps(payload),
            ALLOWED,
        )


def test_allows_insufficient_evidence_without_claims():
    payload = {
        "status": "insufficient_evidence",
        "answer": "I don't have that information.",
        "claims": [],
    }

    result = parse_structured_answer(
        json.dumps(payload),
        ALLOWED,
    )

    assert result.status == "insufficient_evidence"
    assert result.claims == []


def test_rejects_claims_for_insufficient_evidence():
    payload = json.loads(build_response())
    payload["status"] = "insufficient_evidence"

    with pytest.raises(
        ValueError,
        match="Unsupported answer must not contain claims",
    ):
        parse_structured_answer(
            json.dumps(payload),
            ALLOWED,
        )


def test_rejects_missing_status():
    payload = json.loads(build_response())
    del payload["status"]

    with pytest.raises(ValueError, match="Invalid answer status"):
        parse_structured_answer(
            json.dumps(payload),
            ALLOWED,
        )