from copy import deepcopy

import pytest

from app.orders import OrderDataError, OrderService


@pytest.fixture
def service():
    return OrderService()


def get_test_order(service, order_id="ORD-1004"):
    return deepcopy(service.orders[order_id])


def test_valid_partial_order(service):
    order = get_test_order(service)

    result = service._build_order_summary(order)

    assert result["fulfillment_status"] == "partial"


def test_rejects_incorrect_order_status(service):
    order = get_test_order(service)
    order["fulfillment_status"] = "fulfilled"

    with pytest.raises(
        OrderDataError,
        match="status mismatch",
    ):
        service._build_order_summary(order)


def test_rejects_shipment_quantity_mismatch(service):
    order = get_test_order(service)
    order["fulfillments"][0]["items"][0]["quantity"] = 2

    with pytest.raises(
        OrderDataError,
        match="quantity mismatch",
    ):
        service._build_order_summary(order)


def test_rejects_unknown_shipment_item(service):
    order = get_test_order(service)
    order["fulfillments"][0]["items"][0]["line_id"] = "unknown"

    with pytest.raises(
        OrderDataError,
        match="unknown order line",
    ):
        service._build_order_summary(order)


def test_rejects_duplicate_line_ids(service):
    order = get_test_order(service)
    order["items"][1]["line_id"] = "line-1"

    with pytest.raises(
        OrderDataError,
        match="Duplicate order line",
    ):
        service._build_order_summary(order)


def test_rejects_duplicate_fulfillment_ids(service):
    order = get_test_order(service)
    order["fulfillments"].append(
        deepcopy(order["fulfillments"][0])
    )

    with pytest.raises(
        OrderDataError,
        match="Duplicate fulfillment",
    ):
        service._build_order_summary(order)


def test_rejects_invalid_shipment_quantity(service):
    order = get_test_order(service)
    order["fulfillments"][0]["items"][0]["quantity"] = -1

    with pytest.raises(
        OrderDataError,
        match="Invalid fulfillment quantity",
    ):
        service._build_order_summary(order)