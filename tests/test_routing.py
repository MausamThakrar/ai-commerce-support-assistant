
import pytest

from app.routing import detect_order_query


@pytest.mark.parametrize(
    "question,expected_id",
    [
        ("Where is my order ORD-9999?", "ORD-9999"),
        ("Track my order ORD-1004", "ORD-1004"),
        ("What is my order status?", None),
        ("Can you refund my order?", None),
    ],
)
def test_order_detection(question, expected_id):
    result = detect_order_query(question)

    assert result["requires_order_lookup"] is True
    assert result["order_id"] == expected_id


def test_general_policy_query():
    result = detect_order_query(
        "What is your return policy?"
    )

    assert result["requires_order_lookup"] is False
    assert result["order_id"] is None