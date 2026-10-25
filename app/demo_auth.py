
import os
import secrets
from typing import Optional

from app.order_tools import AuthenticatedCustomer


class AuthenticationError(Exception):
    pass


class DemoAuthService:
    def __init__(self, sessions=None):
        self.sessions = sessions if sessions is not None else {}

    def authenticate(
        self,
        token: Optional[str],
    ) -> AuthenticatedCustomer:
        if not token:
            raise AuthenticationError("Authentication required")

        for known_token, customer_id in self.sessions.items():
            if secrets.compare_digest(token, known_token):
                return AuthenticatedCustomer(customer_id=customer_id)

        raise AuthenticationError("Invalid session")

    @classmethod
    def from_environment(cls):
        if os.getenv("APP_ENV", "development") != "development":
            raise RuntimeError(
                "Demo authentication is disabled outside development"
            )

        sessions = {}

        for suffix, customer_id in (
            ("100", "cust-100"),
            ("200", "cust-200"),
        ):
            token = os.getenv(f"DEMO_SESSION_{suffix}")

            if token:
                sessions[token] = customer_id

        return cls(sessions=sessions)