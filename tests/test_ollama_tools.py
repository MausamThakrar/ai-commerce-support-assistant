
import httpx
import pytest

from app.ollama_tools import OllamaOrderAgent, OllamaToolError
from app.order_tools import AuthenticatedCustomer


def make_agent(responses):
    def handler(request):
        return httpx.Response(
            200,
            json={"message": responses.pop(0)},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    return OllamaOrderAgent(client=client)


def tool_call(arguments):
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [{
            "function": {
                "name": "get_order_status",
                "arguments": arguments,
            }
        }],
    }

def test_own_order_lookup():
    agent = make_agent([
        tool_call({"order_id": "ORD-1004"}),
    ])

    result = agent.answer(
        "Where is ORD-1004?",
        AuthenticatedCustomer("cust-100"),
    )

    assert result["status"] == "answered"
    assert result["tool_result"]["status"] == "success"
    assert result["tool_result"]["order"]["order_id"] == "ORD-1004"
    assert "partially fulfilled" in result["answer"]

def test_unauthenticated_lookup():
    agent = make_agent([
        tool_call({"order_id": "ORD-1004"}),
    ])

    result = agent.answer("Where is ORD-1004?", None)

    assert result["status"] == "authentication_required"
    assert result["tool_result"] is None


def test_other_customer_order_is_not_exposed():
    agent = make_agent([
        tool_call({"order_id": "ORD-2001"}),
    ])

    result = agent.answer(
        "Where is ORD-2001?",
        AuthenticatedCustomer("cust-100"),
    )

    assert result["status"] == "not_found"
    assert result["tool_result"] is None

def test_reject_customer_id_injection():
    agent = make_agent([
        tool_call({
            "order_id": "ORD-2001",
            "customer_id": "cust-200",
        }),
    ])

    with pytest.raises(
        OllamaToolError,
        match="Unexpected tool arguments",
    ):
        agent.answer(
            "Check my recent order",
            AuthenticatedCustomer("cust-100"),
        )

def test_reject_unknown_tool():
    agent = make_agent([{
        "role": "assistant",
        "tool_calls": [{
            "function": {
                "name": "cancel_order",
                "arguments": {"order_id": "ORD-1004"},
            }
        }],
    }])

    with pytest.raises(
        OllamaToolError,
        match="Unauthorized tool",
    ):
        agent.answer(
            "Cancel my recent order",
            AuthenticatedCustomer("cust-100"),
        )

def test_no_tool_call_does_not_invent_order():
    agent = make_agent([{
        "role": "assistant",
        "content": "Your order has shipped.",
    }])

    result = agent.answer(
        "Where is my order?",
        AuthenticatedCustomer("cust-100"),
    )

    assert result["status"] == "no_tool_call"
    assert result["tool_result"] is None
    assert "couldn't verify" in result["answer"]


def test_reject_invalid_order_id():
    agent = make_agent([
        tool_call({"order_id": "../../secrets"}),
    ])

    with pytest.raises(
        OllamaToolError,
        match="Invalid order ID",
    ):
        agent.answer(
            "Check my order",
            AuthenticatedCustomer("cust-100"),
        )


def test_reject_multiple_tool_calls():
    message = tool_call({"order_id": "ORD-1004"})
    message["tool_calls"].append(
        message["tool_calls"][0].copy()
    )

    agent = make_agent([message])

    with pytest.raises(
        OllamaToolError,
        match="Unexpected number",
    ):
        agent.answer(
            "Check my order",
            AuthenticatedCustomer("cust-100"),
        )

def test_explicit_order_id_bypasses_llm():
    def handler(request):
        raise AssertionError("Ollama must not be called")

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    agent = OllamaOrderAgent(client=client)

    result = agent.answer(
        "Cancel ORD-1004 and refund me.",
        AuthenticatedCustomer("cust-100"),
    )

    assert result["status"] == "answered"
    assert "partially fulfilled" in result["answer"]
    assert "refund approved" not in result["answer"].lower()


def test_multiple_explicit_orders_rejected():
    agent = make_agent([])

    result = agent.answer(
        "Compare ORD-1001 and ORD-1004",
        AuthenticatedCustomer("cust-100"),
    )

    assert result["status"] == "ambiguous_order"
    assert result["tool_result"] is None