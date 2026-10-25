
import pytest

from app.order_responses import build_order_response
from app.orders import OrderService


@pytest.fixture
def service():
    return OrderService()


def test_partial_fulfillment_response(service):
    order = service.get_order("ORD-1004", "cust-100")

    answer = build_order_response(order)

    assert "partially fulfilled" in answer
    assert "Ridge Outdoor Rain Jacket" in answer
    assert "Trail Essentials First Aid Kit" in answer
    assert "1 remaining" in answer
    assert "in transit" in answer


def test_delivered_order_response(service):
    order = service.get_order("ORD-1002", "cust-100")

    answer = build_order_response(order)

    assert "fully fulfilled" in answer
    assert "delivered" in answer
    assert "DHL" in answer


def test_unfulfilled_order_response(service):
    order = service.get_order("ORD-1001", "cust-100")

    answer = build_order_response(order)

    assert "not yet fulfilled" in answer
    assert "1 remaining" in answer


def test_cancelled_order_response(service):
    order = service.get_order("ORD-1005", "cust-100")

    answer = build_order_response(order)

    assert "has been cancelled" in answer
    assert "refunded" in answer


def test_response_does_not_invent_commitments(service):
    order = service.get_order("ORD-1004", "cust-100")

    answer = build_order_response(order).lower()

    forbidden = [
        "guaranteed",
        "refund approved",
        "cancellation approved",
        "arriving tomorrow",
        "will arrive",
    ]

    for phrase in forbidden:
        assert phrase not in answer