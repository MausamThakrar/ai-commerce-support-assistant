
from typing import Dict


FULFILLMENT_LABELS = {
    "unfulfilled": "not yet fulfilled",
    "partial": "partially fulfilled",
    "fulfilled": "fully fulfilled",
}

SHIPMENT_LABELS = {
    "in_transit": "in transit",
    "delivered": "delivered",
    "pending": "pending shipment",
    "out_for_delivery": "out for delivery",
    "failed": "delivery exception",
}


def build_order_response(order: Dict) -> str:
    """Build a factual response from a validated order summary."""

    order_id = order["order_id"]

    if order["cancelled"]:
        answer = (
            f"Order {order_id} has been cancelled. "
            f"Recorded payment status: {order['financial_status']}."
        )
    else:
        status = FULFILLMENT_LABELS.get(
            order["fulfillment_status"],
            "status unavailable",
        )
        answer = f"Order {order_id} is {status}."

    details = []

    for item in order["items"]:
        fulfilled = item["fulfilled_quantity"]
        remaining = item["remaining_quantity"]
        quantity = item["quantity"]

        details.append(
            f"{item['title']}: "
            f"{fulfilled} of {quantity} fulfilled, "
            f"{remaining} remaining."
        )

    for fulfillment in order["fulfillments"]:
        shipment_status = SHIPMENT_LABELS.get(
            fulfillment["status"],
            "status unavailable",
        )

        carrier = fulfillment.get("carrier")
        description = f"Shipment status: {shipment_status}"

        if carrier:
            description += f" ({carrier})"

        description += "."

        if fulfillment["status"] == "delivered":
            delivered_at = fulfillment.get("delivered_at")
            if delivered_at:
                description += (
                    f" Recorded delivery timestamp: {delivered_at}."
                )

        details.append(description)

    return " ".join([answer] + details)