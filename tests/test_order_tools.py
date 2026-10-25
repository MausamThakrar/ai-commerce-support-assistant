
import pytest

from app.order_tools import AuthenticatedCustomer, OrderTools


@pytest.fixture
def tools():
    return OrderTools()


def test_authenticated_customer_gets_own_order(tools):
    result = tools.get_order_status(
        "ORD-1004",
        AuthenticatedCustomer(customer_id="cust-100"),
    )

    assert result["status"] == "success"
    assert result["order"]["order_id"] == "ORD-1004"
    assert result["order"]["fulfillment_status"] == "partial"
    assert result["order"]["remaining_quantity"] == 1


def test_unauthenticated_request_is_rejected(tools):
    result = tools.get_order_status(
        "ORD-1004",
        None,
    )

    assert result["status"] == "authentication_required"
    assert "order" not in result


def test_customer_cannot_access_another_order(tools):
    result = tools.get_order_status(
        "ORD-2001",
        AuthenticatedCustomer(customer_id="cust-100"),
    )

    assert result["status"] == "not_found"
    assert "order" not in result


def test_unknown_order_is_not_found(tools):
    result = tools.get_order_status(
        "ORD-9999",
        AuthenticatedCustomer(customer_id="cust-100"),
    )

    assert result["status"] == "not_found"


def test_unknown_and_unauthorized_responses_match(tools):
    customer = AuthenticatedCustomer(customer_id="cust-100")

    unknown = tools.get_order_status("ORD-9999", customer)
    unauthorized = tools.get_order_status("ORD-2001", customer)

    assert unknown == unauthorized


def test_delivered_order_tracking(tools):
    result = tools.get_order_status(
        "ORD-1002",
        AuthenticatedCustomer(customer_id="cust-100"),
    )

    assert result["status"] == "success"
    assert result["order"]["fulfillments"][0]["status"] == "delivered"
    assert result["order"]["fulfillments"][0]["carrier"] == "DHL"


def test_cancelled_order(tools):
    result = tools.get_order_status(
        "ORD-1005",
        AuthenticatedCustomer(customer_id="cust-100"),
    )

    assert result["status"] == "success"
    assert result["order"]["cancelled"] is True
    assert result["order"]["financial_status"] == "refunded"