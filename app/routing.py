
import re


ORDER_ID_PATTERN = re.compile(
    r"\bORD-\d+\b",
    re.IGNORECASE,
)

ORDER_INTENT_PATTERN = re.compile(
    r"\b("
    r"where is my order|"
    r"track my order|"
    r"order status|"
    r"tracking number|"
    r"cancel my order|"
    r"refund my order"
    r")\b",
    re.IGNORECASE,
)


def detect_order_query(question: str) -> dict:
    order_match = ORDER_ID_PATTERN.search(question)
    intent_match = ORDER_INTENT_PATTERN.search(question)

    return {
        "requires_order_lookup": bool(order_match or intent_match),
        "order_id": (
            order_match.group(0).upper()
            if order_match
            else None
        ),
    }