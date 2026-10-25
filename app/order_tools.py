
from dataclasses import dataclass
from typing import Optional

from app.orders import OrderNotFoundError, OrderService


@dataclass(frozen=True)
class AuthenticatedCustomer:
    """Identity established by a trusted authentication layer."""

    customer_id: str


class OrderTools:
    def __init__(self, order_service: Optional[OrderService] = None):
        self.order_service = (
            order_service
            if order_service is not None
            else OrderService()
        )

    def get_order_status(
        self,
        order_id: str,
        customer: Optional[AuthenticatedCustomer],
    ) -> dict:
        if customer is None or not customer.customer_id:
            return {
                "status": "authentication_required",
                "message": "Sign in to view order information.",
            }

        try:
            order = self.order_service.get_order(
                order_id=order_id,
                authenticated_customer_id=customer.customer_id,
            )
        except OrderNotFoundError:
            return {
                "status": "not_found",
                "message": "Order not found.",
            }

        return {
            "status": "success",
            "order": order,
        }