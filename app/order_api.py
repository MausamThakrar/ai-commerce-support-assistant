
import os
from functools import lru_cache

from fastapi import APIRouter, Depends, Header, HTTPException

from app.demo_auth import AuthenticationError, DemoAuthService
from app.order_tools import AuthenticatedCustomer, OrderTools


router = APIRouter(prefix="/orders", tags=["Orders"])


def require_development_environment():
    if os.getenv("APP_ENV") != "development":
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )


@lru_cache
def get_demo_auth() -> DemoAuthService:
    return DemoAuthService.from_environment()


@lru_cache
def get_order_tools() -> OrderTools:
    return OrderTools()


def get_authenticated_customer(
    authorization: str = Header(default=""),
    auth: DemoAuthService = Depends(get_demo_auth),
) -> AuthenticatedCustomer:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    token = authorization.removeprefix("Bearer ").strip()

    try:
        return auth.authenticate(token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid session",
        ) from exc


@router.get(
    "/{order_id}",
    dependencies=[Depends(require_development_environment)],
)
def get_order(
    order_id: str,
    customer: AuthenticatedCustomer = Depends(
        get_authenticated_customer
    ),
    tools: OrderTools = Depends(get_order_tools),
):
    result = tools.get_order_status(
        order_id=order_id,
        customer=customer,
    )

    if result["status"] == "not_found":
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    if result["status"] != "success":
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    return result["order"]