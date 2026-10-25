
import re
from functools import lru_cache

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.order_api import (
    get_authenticated_customer,
    require_development_environment,
)
from app.order_tools import AuthenticatedCustomer
from app.ollama_tools import OllamaOrderAgent, OllamaToolError
from app.order_policy import OrderPolicyService

from typing import Optional

from app.conversation import ConversationStore, extract_order_ids
from app.order_api import get_order_tools
from app.order_tools import OrderTools

router = APIRouter(
    prefix="/support",
    tags=["Order Support"],
)


class OrderQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@lru_cache
def get_order_agent() -> OllamaOrderAgent:
    return OllamaOrderAgent()


@lru_cache
def get_order_policy_service() -> OrderPolicyService:
    return OrderPolicyService()


@router.post(
    "/order-ask",
    dependencies=[Depends(require_development_environment)],
)
def ask_order_support(
    request: OrderQuestion,
    customer: AuthenticatedCustomer = Depends(
        get_authenticated_customer
    ),
    agent: OllamaOrderAgent = Depends(get_order_agent),
    policy_service: OrderPolicyService = Depends(
        get_order_policy_service
    ),
):
    try:
        question = request.question

        order_ids = {
            match.upper()
            for match in re.findall(
                r"\bORD-\d{1,12}\b",
                question,
                flags=re.IGNORECASE,
            )
        }

        cancellation_intent = bool(
            re.search(
                r"\b(cancel|cancelled|canceled|cancellation)\b",
                question,
                flags=re.IGNORECASE,
            )
        )

        if cancellation_intent and len(order_ids) == 1:
            order_id = next(iter(order_ids))

            result = policy_service.answer_cancellation_question(
                order_id=order_id,
                customer=customer,
            )
        else:
            result = agent.answer(
                question=question,
                customer=customer,
            )

    except OllamaToolError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to verify the order request",
        ) from exc

    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Order assistant temporarily unavailable",
        ) from exc

    return {
        "status": result["status"],
        "answer": result["answer"],
        "sources": result.get("sources", []),
    }

@lru_cache
def get_conversation_store() -> ConversationStore:
    return ConversationStore(
        ttl_seconds=1800,
        max_conversations=1000,
    )


class ConversationQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[str] = None


@router.post(
    "/order-chat",
    dependencies=[Depends(require_development_environment)],
)
def ask_order_chat(
    request: ConversationQuestion,
    customer: AuthenticatedCustomer = Depends(
        get_authenticated_customer
    ),
    store: ConversationStore = Depends(
        get_conversation_store
    ),
    tools: OrderTools = Depends(get_order_tools),
    agent: OllamaOrderAgent = Depends(get_order_agent),
    policy_service: OrderPolicyService = Depends(
        get_order_policy_service
    ),
):
    # Conversation access is always scoped to
    # the authenticated customer.
    if request.conversation_id:
        conversation = store.get(
            request.conversation_id,
            customer.customer_id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )
    else:
        try:
            conversation = store.create(customer.customer_id)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail="Conversation capacity reached",
            ) from exc

    question = request.question
    explicit_ids = extract_order_ids(question)

    if len(explicit_ids) > 1:
        return {
            "conversation_id": conversation.conversation_id,
            "status": "ambiguous_order",
            "answer": "Specify one order at a time.",
            "sources": [],
        }

    order_id = (
        next(iter(explicit_ids))
        if explicit_ids
        else conversation.order_id
    )

    if order_id is None:
        return {
            "conversation_id": conversation.conversation_id,
            "status": "missing_order_id",
            "answer": (
                "Provide your order number to check its status."
            ),
            "sources": [],
        }

    # Conversation history never grants order access.
    # Verify ownership again on every request.
    lookup = tools.get_order_status(
        order_id=order_id,
        customer=customer,
    )

    if lookup["status"] != "success":
        return {
            "conversation_id": conversation.conversation_id,
            "status": lookup["status"],
            "answer": (
                "Sign in to view order information."
                if lookup["status"] == "authentication_required"
                else "Order not found."
            ),
            "sources": [],
        }

    cancellation_intent = bool(
        re.search(
            r"\b(cancel|cancelled|canceled|cancellation)\b",
            question,
            flags=re.IGNORECASE,
        )
    )

    try:
        if cancellation_intent:
            result = policy_service.answer_cancellation_question(
                order_id=order_id,
                customer=customer,
            )
        else:
            # Add the verified order ID to the question
            # when a follow-up does not contain one.
            resolved_question = (
                question
                if explicit_ids
                else f"{question}\nOrder reference: {order_id}"
            )

            result = agent.answer(
                question=resolved_question,
                customer=customer,
            )

    except OllamaToolError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to verify the order request",
        ) from exc

    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Order assistant temporarily unavailable",
        ) from exc

    # Save context only after a successful,
    # authorized order lookup and response.
    if result["status"] == "answered":
        store.update_order(
            conversation.conversation_id,
            customer.customer_id,
            order_id,
        )

    return {
        "conversation_id": conversation.conversation_id,
        "status": result["status"],
        "answer": result["answer"],
        "sources": result.get("sources", []),
    }
