
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.conversation import ConversationStore
from app.demo_auth import DemoAuthService
from app.order_api import get_demo_auth
from app.order_support_api import get_conversation_store


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")

    # Create one conversation store per test.
    # Reuse it across requests within that test.
    conversation_store = ConversationStore()

    app.dependency_overrides[get_demo_auth] = (
        lambda: DemoAuthService({
            "test-token-100": "cust-100",
            "test-token-200": "cust-200",
        })
    )

    app.dependency_overrides[get_conversation_store] = (
        lambda: conversation_store
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_demo_auth, None)
        app.dependency_overrides.pop(
            get_conversation_store,
            None,
        )

def send(client, question, token, conversation_id=None):
    payload = {"question": question}

    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    return client.post(
        "/support/order-chat",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def test_first_message_creates_conversation(client):
    response = send(
        client, "Where is ORD-1004?", "test-token-100"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "answered"
    assert data["conversation_id"]
    assert "partially fulfilled" in data["answer"]


def test_followup_reuses_verified_order(client):
    first = send(
        client, "Where is ORD-1004?", "test-token-100"
    ).json()

    second = send(
        client,
        "Can I cancel the remaining item?",
        "test-token-100",
        first["conversation_id"],
    )

    assert second.status_code == 200
    data = second.json()

    assert data["status"] == "answered"
    assert "Trail Essentials First Aid Kit" in data["answer"]
    assert "No cancellation was performed" in data["answer"]
    assert len(data["sources"]) == 3


def test_conversation_isolation(client):
    first = send(
        client, "Where is ORD-1004?", "test-token-100"
    ).json()

    response = send(
        client,
        "Where is my order?",
        "test-token-200",
        first["conversation_id"],
    )

    assert response.status_code == 404


def test_unknown_conversation(client):
    response = send(
        client,
        "Where is my order?",
        "test-token-100",
        "unknown-conversation",
    )

    assert response.status_code == 404


def test_missing_order_reference(client):
    response = send(
        client,
        "Where is my order?",
        "test-token-100",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "missing_order_id"


def test_explicit_order_switch(client):
    first = send(
        client, "Where is ORD-1004?", "test-token-100"
    ).json()

    second = send(
        client,
        "Where is ORD-1002?",
        "test-token-100",
        first["conversation_id"],
    )

    assert second.status_code == 200
    assert "fully fulfilled" in second.json()["answer"]


def test_unauthorized_order_does_not_replace_context(client):
    first = send(
        client, "Where is ORD-1004?", "test-token-100"
    ).json()

    conversation_id = first["conversation_id"]

    denied = send(
        client,
        "Where is ORD-2001?",
        "test-token-100",
        conversation_id,
    )

    assert denied.json()["status"] == "not_found"

    followup = send(
        client,
        "Can I cancel the remaining item?",
        "test-token-100",
        conversation_id,
    )

    assert followup.json()["status"] == "answered"
    assert "ORD-1004" in followup.json()["answer"]


def test_production_access_blocked(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    response = send(
        client, "Where is ORD-1004?", "test-token-100"
    )

    assert response.status_code == 404