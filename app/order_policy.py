
from typing import Optional

from app.order_tools import AuthenticatedCustomer, OrderTools
from app.retrieval import KnowledgeRetriever


REQUIRED_RULES = {
    "before fulfillment": (
        "Orders can be cancelled before fulfillment begins."
    ),
    "after fulfillment begins": (
        "Once fulfillment has started, cancellation is not guaranteed."
    ),
    "shipped orders": (
        "Orders that have already shipped cannot be cancelled."
    ),
}


class OrderPolicyService:
    def __init__(
        self,
        order_tools: Optional[OrderTools] = None,
        retriever: Optional[KnowledgeRetriever] = None,
    ):
        self.order_tools = (
            order_tools if order_tools is not None else OrderTools()
        )
        self.retriever = (
            retriever if retriever is not None
            else KnowledgeRetriever()
        )

    def _get_policy_rules(self):
        matches = self.retriever.search(
            "Order cancellation before fulfillment, "
            "after fulfillment begins, and shipped orders",
            top_k=10,
        )

        rules = {}

        for match in matches:
            if match.get("source") != "cancellations.md":
                continue

            heading = match.get("heading", "").strip().lower()

            if heading not in REQUIRED_RULES:
                continue

            expected_text = REQUIRED_RULES[heading]

            if expected_text not in match.get("text", ""):
                continue

            if heading in rules:
                continue

            rules[heading] = match

        return rules

    def answer_cancellation_question(
        self,
        order_id: str,
        customer: Optional[AuthenticatedCustomer],
    ) -> dict:
        result = self.order_tools.get_order_status(
            order_id=order_id,
            customer=customer,
        )

        if result["status"] != "success":
            return {
                "status": result["status"],
                "answer": (
                    "Sign in to view order information."
                    if result["status"] == "authentication_required"
                    else "Order not found."
                ),
                "sources": [],
            }

        order = result["order"]

        if order["cancelled"]:
            return {
                "status": "answered",
                "answer": (
                    f"Order {order['order_id']} has already "
                    f"been cancelled. Recorded payment status: "
                    f"{order['financial_status']}. "
                    "No additional cancellation was performed."
                ),
                "sources": [],
            }

        rules = self._get_policy_rules()

        # Never issue a partial or unsupported policy
        # interpretation when required rules are missing.
        if set(rules) != set(REQUIRED_RULES):
            return {
                "status": "insufficient_policy_evidence",
                "answer": (
                    f"Order {order['order_id']} was located, "
                    "but its cancellation policy could not "
                    "be fully verified. Contact support to "
                    "check cancellation eligibility. "
                    "No cancellation was performed."
                ),
                "sources": [],
            }

        before = rules["before fulfillment"]
        during = rules["after fulfillment begins"]
        shipped = rules["shipped orders"]

        sources = [
            {
                "id": rule["id"],
                "source": rule["source"],
                "heading": rule["heading"],
            }
            for rule in (before, during, shipped)
        ]

        status_labels = {
            "unfulfilled": "not yet fulfilled",
            "partial": "partially fulfilled",
            "fulfilled": "fully fulfilled",
        }

        status_label = status_labels.get(
            order["fulfillment_status"],
            "status unavailable",
        )

        paragraphs = [
            f"Order {order['order_id']} is {status_label}."
        ]

        # Link individual order lines to recorded shipments.
        shipped_line_ids = set()

        for fulfillment in order["fulfillments"]:
            if fulfillment["status"] in (
                "in_transit",
                "out_for_delivery",
                "delivered",
            ):
                for shipped_item in fulfillment["items"]:
                    shipped_line_ids.add(shipped_item["line_id"])

        for item in order["items"]:
            title = item["title"]
            remaining = item["remaining_quantity"]

            if item["line_id"] in shipped_line_ids:
                paragraphs.append(
                    f"{title}: a shipment is recorded for "
                    "this item. Shipped items cannot be "
                    f"cancelled. [{shipped['id']}]"
                )

            if remaining > 0:
                paragraphs.append(
                    f"{title}: {remaining} "
                    f"{'unit remains' if remaining == 1 else 'units remain'} "
                    "unfulfilled. Orders can be cancelled "
                    "before fulfillment begins "
                    f"[{before['id']}], but cancellation "
                    "is not guaranteed once processing "
                    f"has started [{during['id']}]. "
                    "The available order data does not "
                    "confirm whether processing has started "
                    "for these units."
                )

        paragraphs.append(
            "This assistant cannot confirm cancellation eligibility "
            "for individual items or execute cancellations. "
            "No cancellation was performed."
        )

        return {
            "status": "answered",
            "answer": "\n\n".join(paragraphs),
            "sources": sources,
        }