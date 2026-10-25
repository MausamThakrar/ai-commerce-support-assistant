
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo_auth import DemoAuthService
from app.order_api import get_demo_auth


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")

    app.dependency_overrides[get_demo_auth] = (
        lambda: DemoAuthService({
            "test-token-100": "cust-100",
            "test-token-200": "cust-200",
        })
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_demo_auth, None)


def test_authenticated_order_lookup(client):
    response = client.get(
        "/orders/ORD-1004",
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 200
    assert response.json()["order_id"] == "ORD-1004"
    assert response.json()["remaining_quantity"] == 1


def test_missing_authentication(client):
    response = client.get("/orders/ORD-1004")

    assert response.status_code == 401


def test_invalid_token(client):
    response = client.get(
        "/orders/ORD-1004",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_other_customer_order(client):
    response = client.get(
        "/orders/ORD-2001",
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 404


def test_unknown_order(client):
    response = client.get(
        "/orders/ORD-9999",
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 404


def test_customer_can_access_own_order(client):
    response = client.get(
        "/orders/ORD-2001",
        headers={"Authorization": "Bearer test-token-200"},
    )

    assert response.status_code == 200
    assert response.json()["order_id"] == "ORD-2001"


def test_other_customer_and_unknown_order_match(client):
    headers = {"Authorization": "Bearer test-token-100"}

    unauthorized = client.get(
        "/orders/ORD-2001",
        headers=headers,
    )
    unknown = client.get(
        "/orders/ORD-9999",
        headers=headers,
    )

    assert unauthorized.status_code == unknown.status_code == 404
    assert unauthorized.json() == unknown.json()


def test_order_endpoint_disabled_in_production(
    client,
    monkeypatch,
):
    monkeypatch.setenv("APP_ENV", "production")

    response = client.get(
        "/orders/ORD-1004",
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


def test_order_endpoint_disabled_without_environment(
    client,
    monkeypatch,
):
    monkeypatch.delenv("APP_ENV", raising=False)

    response = client.get(
        "/orders/ORD-1004",
        headers={"Authorization": "Bearer test-token-100"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}