
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo_auth import DemoAuthService
from app.order_api import get_demo_auth
from app.order_support_api import get_order_agent


class FakeOrderAgent:
    def answer(self, question, customer):
        return {
            "status": "answered",
            "answer": (
                f"Verified order response for {customer.customer_id}."
            ),
            "tool_result": {
                "internal": "must-not-be-exposed",
            },
        }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")

    app.dependency_overrides[get_demo_auth] = (
        lambda: DemoAuthService({
            "test-token-100": "cust-100",
            "test-token-200": "cust-200",
        })
    )

    app.dependency_overrides[get_order_agent] = (
        lambda: FakeOrderAgent()
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_demo_auth, None)
        app.dependency_overrides.pop(get_order_agent, None)


def test_authenticated_order_question(client):
    response = client.post(
        "/support/order-ask",
        json={"question": "Where is my order ORD-1004?"},
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "answered"
    assert "cust-100" in response.json()["answer"]


def test_missing_authentication(client):
    response = client.post(
        "/support/order-ask",
        json={"question": "Where is ORD-1004?"},
    )

    assert response.status_code == 401


def test_invalid_token(client):
    response = client.post(
        "/support/order-ask",
        json={"question": "Where is ORD-1004?"},
        headers={"Authorization": "Bearer invalid"},
    )

    assert response.status_code == 401


def test_rejects_empty_question(client):
    response = client.post(
        "/support/order-ask",
        json={"question": ""},
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 422


def test_internal_tool_data_not_exposed(client):
    response = client.post(
        "/support/order-ask",
        json={"question": "Check ORD-1004"},
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 200
    assert "tool_result" not in response.json()
    assert "must-not-be-exposed" not in response.text


def test_second_customer_context(client):
    response = client.post(
        "/support/order-ask",
        json={"question": "Check ORD-2001"},
        headers={"Authorization": "Bearer test-token-200"},
    )

    assert response.status_code == 200
    assert "cust-200" in response.json()["answer"]


def test_endpoint_disabled_in_production(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    response = client.post(
        "/support/order-ask",
        json={"question": "Check ORD-1004"},
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


def test_endpoint_disabled_without_environment(client, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)

    response = client.post(
        "/support/order-ask",
        json={"question": "Where is ORD-1004?"},
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


def test_production_rejects_before_authentication(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    response = client.post(
        "/support/order-ask",
        json={"question": "Where is ORD-1004?"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


def test_cancellation_routes_to_policy_service(client):
    response = client.post(
        "/support/order-ask",
        json={
            "question": (
                "Can I cancel the remaining item in ORD-1004?"
            )
        },
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "answered"
    assert "partially fulfilled" in data["answer"]
    assert "Trail Essentials First Aid Kit" in data["answer"]
    assert "No cancellation was performed" in data["answer"]
    assert len(data["sources"]) == 3