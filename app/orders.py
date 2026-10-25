
import json
from pathlib import Path
from typing import Optional


ORDERS_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "orders.json"
)


class OrderNotFoundError(Exception):
    """Order is unavailable to the authenticated customer."""


class OrderDataError(Exception):
    """Stored order data is invalid or inconsistent."""


class OrderService:
    def __init__(self, orders_file: Path = ORDERS_FILE):
        with open(orders_file, encoding="utf-8") as file:
            data = json.load(file)

        self.orders = {
            order["id"]: order
            for order in data["orders"]
        }

    def get_order(
        self,
        order_id: str,
        authenticated_customer_id: Optional[str],
    ) -> dict:
        if not authenticated_customer_id:
            raise PermissionError(
                "Authentication required"
            )

        order = self.orders.get(order_id.upper())

        if (
            order is None
            or order["customer_id"] != authenticated_customer_id
        ):
            raise OrderNotFoundError(
                "Order not found"
            )

        return self._build_order_summary(order)

    def _build_order_summary(self, order: dict) -> dict:
        items = []
        fulfilled_total = 0
        remaining_total = 0

        for item in order["items"]:
            quantity = item["quantity"]
            fulfilled = item["fulfilled_quantity"]

            if (
                not isinstance(quantity, int)
                or isinstance(quantity, bool)
                or not isinstance(fulfilled, int)
                or isinstance(fulfilled, bool)
                or quantity <= 0
                or not 0 <= fulfilled <= quantity
            ):
                raise OrderDataError(
                    "Invalid item fulfillment quantities"
                )

            remaining = quantity - fulfilled

            fulfilled_total += fulfilled
            remaining_total += remaining

            items.append({
                "line_id": item["line_id"],
                "title": item["title"],
                "sku": item["sku"],
                "quantity": quantity,
                "fulfilled_quantity": fulfilled,
                "remaining_quantity": remaining,
            })

            self._validate_order_consistency(order)

        return {
            "order_id": order["id"],
            "financial_status": order["financial_status"],
            "fulfillment_status": order["fulfillment_status"],
            "cancelled": order["cancelled_at"] is not None,
            "currency": order["currency"],
            "items": items,
            "fulfilled_quantity": fulfilled_total,
            "remaining_quantity": remaining_total,
            "fulfillments": order["fulfillments"],
        }


    def _validate_order_consistency(self, order: dict) -> None:
        items = order["items"]
        fulfillments = order["fulfillments"]

        item_map = {}

        for item in items:
            line_id = item["line_id"]

            if line_id in item_map:
                raise OrderDataError("Duplicate order line ID")

            item_map[line_id] = item

        shipped_quantities = {
            line_id: 0 for line_id in item_map
        }

        fulfillment_ids = set()

        for fulfillment in fulfillments:
            fulfillment_id = fulfillment["id"]

            if fulfillment_id in fulfillment_ids:
                raise OrderDataError("Duplicate fulfillment ID")

            fulfillment_ids.add(fulfillment_id)

            for shipped_item in fulfillment["items"]:
                line_id = shipped_item["line_id"]
                quantity = shipped_item["quantity"]

                if line_id not in item_map:
                    raise OrderDataError(
                        "Fulfillment references unknown order line"
                    )

                if (
                    not isinstance(quantity, int)
                    or isinstance(quantity, bool)
                    or quantity <= 0
                ):
                    raise OrderDataError(
                        "Invalid fulfillment quantity"
                    )

                shipped_quantities[line_id] += quantity

        for line_id, item in item_map.items():
            if (
                shipped_quantities[line_id]
                != item["fulfilled_quantity"]
            ):
                raise OrderDataError(
                    "Fulfillment quantity mismatch"
                )

        total_quantity = sum(
            item["quantity"] for item in items
        )

        fulfilled_quantity = sum(
            item["fulfilled_quantity"] for item in items
        )

        if total_quantity <= 0:
            raise OrderDataError("Order has no valid items")

        if fulfilled_quantity == 0:
            expected_status = "unfulfilled"
        elif fulfilled_quantity == total_quantity:
            expected_status = "fulfilled"
        else:
            expected_status = "partial"

        if order["fulfillment_status"] != expected_status:
            raise OrderDataError(
                "Order fulfillment status mismatch"
            )