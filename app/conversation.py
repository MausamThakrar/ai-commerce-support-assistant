
import re
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional


ORDER_ID_PATTERN = re.compile(
    r"\bORD-\d{1,12}\b",
    flags=re.IGNORECASE,
)


@dataclass
class Conversation:
    conversation_id: str
    customer_id: str
    order_id: Optional[str]
    expires_at: float


class ConversationStore:
    def __init__(
        self,
        ttl_seconds: int = 1800,
        max_conversations: int = 1000,
    ):
        if ttl_seconds <= 0:
            raise ValueError("TTL must be positive")

        if max_conversations <= 0:
            raise ValueError("Maximum conversations must be positive")

        self.ttl_seconds = ttl_seconds
        self.max_conversations = max_conversations
        self._conversations: Dict[str, Conversation] = {}
        self._lock = threading.RLock()

    def _cleanup(self):
        now = time.monotonic()

        expired = [
            conversation_id
            for conversation_id, conversation
            in self._conversations.items()
            if conversation.expires_at <= now
        ]

        for conversation_id in expired:
            del self._conversations[conversation_id]

    def create(self, customer_id: str) -> Conversation:
        if not customer_id:
            raise ValueError("Authenticated customer required")

        with self._lock:
            self._cleanup()

            if len(self._conversations) >= self.max_conversations:
                raise RuntimeError("Conversation capacity reached")

            conversation_id = secrets.token_urlsafe(24)

            conversation = Conversation(
                conversation_id=conversation_id,
                customer_id=customer_id,
                order_id=None,
                expires_at=time.monotonic() + self.ttl_seconds,
            )

            self._conversations[conversation_id] = conversation

            return Conversation(**vars(conversation))

    def get(
        self,
        conversation_id: str,
        customer_id: str,
    ) -> Optional[Conversation]:
        with self._lock:
            self._cleanup()

            conversation = self._conversations.get(conversation_id)

            if conversation is None:
                return None

            if not customer_id or conversation.customer_id != customer_id:
                return None

            return Conversation(**vars(conversation))

    def update_order(
        self,
        conversation_id: str,
        customer_id: str,
        order_id: str,
    ) -> bool:
        with self._lock:
            conversation = self.get(
                conversation_id,
                customer_id,
            )

            if conversation is None:
                return False

            stored = self._conversations[conversation_id]

            stored.order_id = order_id.upper()
            stored.expires_at = (
                time.monotonic() + self.ttl_seconds
            )

            return True


def extract_order_ids(question: str) -> set:
    return {
        match.upper()
        for match in ORDER_ID_PATTERN.findall(question)
    }