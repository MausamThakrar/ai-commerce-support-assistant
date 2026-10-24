
import pytest

from app.grounding import GroundingValidator


@pytest.fixture
def validator():
    return GroundingValidator()


@pytest.fixture
def sources():
    return [{"id": "returns-3", "source": "returns.md"}]


def test_valid_policy_answer(validator, sources):
    result = validator.validate(
        "Personalized products are excluded from "
        "standard returns [returns-3].",
        sources,
    )

    assert result.valid is True


def test_rejects_guaranteed_refund(validator, sources):
    result = validator.validate(
        "You can get a refund for your damaged item [returns-3].",
        sources,
    )

    assert result.valid is False
    assert result.reason == "unsupported_commitment"


def test_rejects_entitlement_claim(validator, sources):
    result = validator.validate(
        "You are entitled to a refund [returns-3].",
        sources,
    )

    assert result.valid is False


def test_rejects_store_action_promise(validator, sources):
    result = validator.validate(
        "We will refund your order [returns-3].",
        sources,
    )

    assert result.valid is False


def test_rejects_internal_context_language(validator, sources):
    result = validator.validate(
        "The knowledge context does not contain that information.",
        sources,
    )

    assert result.valid is False


def test_rejects_missing_sources(validator):
    result = validator.validate(
        "Express shipping costs €9.90.",
        [],
    )

    assert result.valid is False


def test_rejects_empty_answer(validator, sources):
    result = validator.validate("", sources)

    assert result.valid is False