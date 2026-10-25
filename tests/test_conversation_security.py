
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.conversation import ConversationStore
from app.demo_auth import DemoAuthService
from app.order_api import get_demo_auth
from app.order_support_api import get_conversation_store


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")

    store = ConversationStore(ttl_seconds=1800)

    app.dependency_overrides[get_demo_auth] = (
        lambda: DemoAuthService({
            "token-100": "cust-100",
            "token-200": "cust-200",
        })
    )
    app.dependency_overrides[get_conversation_store] = (
        lambda: store
    )

    try:
        with TestClient(app) as client:
            yield client, store
    finally:
        app.dependency_overrides.pop(get_demo_auth, None)
        app.dependency_overrides.pop(get_conversation_store, None)


def ask(client, question, token="token-100", conversation_id=None):
    payload = {"question": question}

    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    return client.post(
        "/support/order-chat",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def test_expired_context_is_rejected(setup, monkeypatch):
    client, store = setup

    first = ask(client, "Where is ORD-1004?").json()
    conversation_id = first["conversation_id"]

    # Expire the stored conversation deterministically.
    with store._lock:
        store._conversations[conversation_id].expires_at = 0

    response = ask(
        client,
        "Can I cancel the remaining item?",
        conversation_id=conversation_id,
    )

    assert response.status_code == 404


def test_customer_switch_rejected(setup):
    client, _ = setup

    first = ask(client, "Where is ORD-1004?").json()

    response = ask(
        client,
        "Where is my order?",
        token="token-200",
        conversation_id=first["conversation_id"],
    )

    assert response.status_code == 404


def test_denied_order_does_not_replace_context(setup):
    client, _ = setup

    first = ask(client, "Where is ORD-1004?").json()
    conversation_id = first["conversation_id"]

    denied = ask(
        client,
        "Where is ORD-2001?",
        conversation_id=conversation_id,
    )

    assert denied.json()["status"] == "not_found"

    followup = ask(
        client,
        "Can I cancel the remaining item?",
        conversation_id=conversation_id,
    )

    assert followup.status_code == 200
    assert "ORD-1004" in followup.json()["answer"]


def test_authorized_order_switch_updates_context(setup):
    client, _ = setup

    first = ask(client, "Where is ORD-1004?").json()
    conversation_id = first["conversation_id"]

    switched = ask(
        client,
        "Where is ORD-1002?",
        conversation_id=conversation_id,
    )

    assert switched.json()["status"] == "answered"

    followup = ask(
        client,
        "Where is it now?",
        conversation_id=conversation_id,
    )

    assert followup.status_code == 200
    assert "ORD-1002" in followup.json()["answer"]


def test_multiple_order_ids_do_not_replace_context(setup):
    client, _ = setup

    first = ask(client, "Where is ORD-1004?").json()
    conversation_id = first["conversation_id"]

    ambiguous = ask(
        client,
        "Compare ORD-1001 and ORD-1002",
        conversation_id=conversation_id,
    )

    assert ambiguous.json()["status"] == "ambiguous_order"

    followup = ask(
        client,
        "Can I cancel the remaining item?",
        conversation_id=conversation_id,
    )

    assert "ORD-1004" in followup.json()["answer"]