
import pytest

from app.demo_auth import (
    AuthenticationError,
    DemoAuthService,
)


@pytest.fixture
def auth():
    return DemoAuthService({
        "test-token-100": "cust-100",
        "test-token-200": "cust-200",
    })


def test_customer_100_authentication(auth):
    customer = auth.authenticate("test-token-100")
    assert customer.customer_id == "cust-100"


def test_customer_200_authentication(auth):
    customer = auth.authenticate("test-token-200")
    assert customer.customer_id == "cust-200"


def test_missing_session(auth):
    with pytest.raises(AuthenticationError):
        auth.authenticate(None)


def test_invalid_session(auth):
    with pytest.raises(AuthenticationError):
        auth.authenticate("invalid-token")


def test_auth_disabled_outside_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(RuntimeError):
        DemoAuthService.from_environment()


def test_load_sessions_from_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SESSION_100", "env-token-100")
    monkeypatch.setenv("DEMO_SESSION_200", "env-token-200")

    auth = DemoAuthService.from_environment()

    assert auth.authenticate("env-token-100").customer_id == "cust-100"
    assert auth.authenticate("env-token-200").customer_id == "cust-200"