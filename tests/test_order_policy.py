
import pytest

from app.order_policy import OrderPolicyService
from app.order_tools import AuthenticatedCustomer, OrderTools


class FakeRetriever:
    def __init__(self, results):
        self.results = results

    def search(self, question, top_k=3):
        return self.results[:top_k]


@pytest.fixture
def customer():
    return AuthenticatedCustomer("cust-100")


@pytest.fixture
def policy_results():
    return [
        {
            "id": "cancellations-before",
            "source": "cancellations.md",
            "heading": "Before Fulfillment",
            "text": (
                "Orders can be cancelled before "
                "fulfillment begins."
            ),
            "score": 0.9,
        },
        {
            "id": "cancellations-during",
            "source": "cancellations.md",
            "heading": "After Fulfillment Begins",
            "text": (
                "Once fulfillment has started, "
                "cancellation is not guaranteed."
            ),
            "score": 0.85,
        },
        {
            "id": "cancellations-shipped",
            "source": "cancellations.md",
            "heading": "Shipped Orders",
            "text": (
                "Orders that have already shipped "
                "cannot be cancelled."
            ),
            "score": 0.8,
        },
    ]


def make_service(results):
    return OrderPolicyService(
        order_tools=OrderTools(),
        retriever=FakeRetriever(results),
    )


def test_combines_order_and_policy(
    customer,
    policy_results,
):
    service = make_service(policy_results)

    result = service.answer_cancellation_question(
        "ORD-1004",
        customer,
    )

    assert result["status"] == "answered"
    assert "partially fulfilled" in result["answer"]
    assert "Trail Essentials First Aid Kit" in result["answer"]
    assert "before fulfillment begins" in result["answer"]
    assert "[cancellations-before]" in result["answer"]
    assert "[cancellations-during]" in result["answer"]
    assert "[cancellations-shipped]" in result["answer"]
    assert len(result["sources"]) == 3


def test_does_not_approve_cancellation(
    customer,
    policy_results,
):
    service = make_service(policy_results)

    result = service.answer_cancellation_question(
        "ORD-1004",
        customer,
    )

    answer = result["answer"].lower()

    assert "cannot confirm cancellation eligibility" in answer
    assert "no cancellation was performed" in answer
    assert "cancellation approved" not in answer


def test_rejects_other_customer_order(
    customer,
    policy_results,
):
    service = make_service(policy_results)

    result = service.answer_cancellation_question(
        "ORD-2001",
        customer,
    )

    assert result["status"] == "not_found"
    assert result["sources"] == []
    assert "Ridge" not in result["answer"]


def test_requires_authentication(policy_results):
    service = make_service(policy_results)

    result = service.answer_cancellation_question(
        "ORD-1004",
        None,
    )

    assert result["status"] == "authentication_required"
    assert result["sources"] == []


def test_policy_unavailable(customer):
    service = make_service([])

    result = service.answer_cancellation_question(
        "ORD-1004",
        customer,
    )

    assert result["status"] == "insufficient_policy_evidence"
    assert result["sources"] == []
    assert "could not be fully verified" in result["answer"]
    assert "No cancellation was performed" in result["answer"]

def test_unrelated_document_is_excluded(customer):
    service = make_service([
        {
            "id": "shipping-1",
            "source": "shipping.md",
            "heading": "Shipping",
            "text": "Shipping is free above €75.",
            "score": 0.99,
        }
    ])

    result = service.answer_cancellation_question(
        "ORD-1004",
        customer,
    )

    assert result["sources"] == []
    assert "Shipping is free" not in result["answer"]


def test_cancelled_order_still_reports_recorded_status(
    customer,
    policy_results,
):
    service = make_service(policy_results)

    result = service.answer_cancellation_question(
        "ORD-1005",
        customer,
    )

    assert "has already been cancelled" in result["answer"]
    assert "refunded" in result["answer"]