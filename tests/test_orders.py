
import pytest

from app.orders import (
    OrderDataError,
    OrderNotFoundError,
    OrderService,
)


@pytest.fixture
def order_service():
    return OrderService()


def test_get_own_order(order_service):
    order = order_service.get_order(
        "ORD-1001",
        authenticated_customer_id="cust-100",
    )

    assert order["order_id"] == "ORD-1001"
    assert order["fulfillment_status"] == "unfulfilled"


def test_reject_other_customer_order(order_service):
    with pytest.raises(OrderNotFoundError):
        order_service.get_order(
            "ORD-2001",
            authenticated_customer_id="cust-100",
        )


def test_unknown_order(order_service):
    with pytest.raises(OrderNotFoundError):
        order_service.get_order(
            "ORD-9999",
            authenticated_customer_id="cust-100",
        )


def test_authentication_required(order_service):
    with pytest.raises(PermissionError):
        order_service.get_order(
            "ORD-1001",
            authenticated_customer_id=None,
        )


def test_partial_fulfillment(order_service):
    order = order_service.get_order(
        "ORD-1004",
        authenticated_customer_id="cust-100",
    )

    assert order["fulfillment_status"] == "partial"
    assert order["fulfilled_quantity"] == 1
    assert order["remaining_quantity"] == 1

    assert order["items"][0]["remaining_quantity"] == 0
    assert order["items"][1]["remaining_quantity"] == 1


def test_delivered_order(order_service):
    order = order_service.get_order(
        "ORD-1002",
        authenticated_customer_id="cust-100",
    )

    assert order["fulfillments"][0]["status"] == "delivered"
    assert order["fulfillments"][0]["carrier"] == "DHL"


def test_cancelled_order(order_service):
    order = order_service.get_order(
        "ORD-1005",
        authenticated_customer_id="cust-100",
    )

    assert order["cancelled"] is True
    assert order["financial_status"] == "refunded"


def test_invalid_fulfillment_quantity(order_service):
    order = {
        "id": "ORD-TEST",
        "financial_status": "paid",
        "fulfillment_status": "unfulfilled",
        "cancelled_at": None,
        "currency": "EUR",
        "fulfillments": [],
        "items": [
            {
                "line_id": "line-1",
                "title": "Test Product",
                "sku": "TEST-1",
                "quantity": 1,
                "fulfilled_quantity": 2,
            }
        ],
    }

    with pytest.raises(OrderDataError):
        order_service._build_order_summary(order)