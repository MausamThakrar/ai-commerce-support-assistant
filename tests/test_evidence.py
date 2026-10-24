
from app.evidence import render_verified_answer


SOURCES = {
    "shipping-3": {
        "text": (
            "Express Shipping\n"
            "Express shipping costs €9.90.\n"
            "Estimated delivery is 1–2 business days "
            "after dispatch."
        )
    },
    "faq-6": {
        "text": (
            "Some products include a manufacturing warranty. "
            "Check the individual product information "
            "for warranty duration."
        )
    },
}


def test_multiple_supported_claims():
    claims = [
        {
            "text": "Express shipping costs €9.90",
            "source_ids": ["shipping-3"],
        },
        {
            "text": (
                "Estimated delivery is 1–2 business days "
                "after dispatch"
            ),
            "source_ids": ["shipping-3"],
        },
    ]

    result = render_verified_answer(claims, SOURCES)

    assert result.valid is True
    assert "€9.90" in result.answer
    assert "1–2 business days" in result.answer
    assert "[shipping-3]" in result.answer


def test_rejects_invented_warranty_claim():
    claims = [
        {
            "text": (
                "Northstar Goods does not offer "
                "lifetime warranties"
            ),
            "source_ids": ["faq-6"],
        }
    ]

    result = render_verified_answer(claims, SOURCES)

    assert result.valid is False
    assert result.reason == "claim_not_found_in_evidence"


def test_supported_warranty_claim():
    claims = [
        {
            "text": "Some products include a manufacturing warranty",
            "source_ids": ["faq-6"],
        }
    ]

    result = render_verified_answer(claims, SOURCES)

    assert result.valid is True
    assert "manufacturing warranty" in result.answer


def test_rejects_unknown_source():
    claims = [
        {
            "text": "Express shipping costs €9.90",
            "source_ids": ["invented-1"],
        }
    ]

    result = render_verified_answer(claims, SOURCES)

    assert result.valid is False
    assert result.reason == "unknown_source"