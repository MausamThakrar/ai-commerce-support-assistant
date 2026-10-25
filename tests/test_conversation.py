
import pytest

from app.conversation import (
    ConversationStore,
    extract_order_ids,
)


def test_create_conversation():
    store = ConversationStore()

    conversation = store.create("cust-100")

    assert conversation.conversation_id
    assert conversation.customer_id == "cust-100"
    assert conversation.order_id is None


def test_customer_can_retrieve_own_conversation():
    store = ConversationStore()
    conversation = store.create("cust-100")

    result = store.get(
        conversation.conversation_id,
        "cust-100",
    )

    assert result is not None
    assert result.conversation_id == conversation.conversation_id


def test_other_customer_cannot_access_conversation():
    store = ConversationStore()
    conversation = store.create("cust-100")

    result = store.get(
        conversation.conversation_id,
        "cust-200",
    )

    assert result is None


def test_unknown_conversation():
    store = ConversationStore()

    assert store.get("unknown", "cust-100") is None


def test_update_order_context():
    store = ConversationStore()
    conversation = store.create("cust-100")

    updated = store.update_order(
        conversation.conversation_id,
        "cust-100",
        "ord-1004",
    )

    assert updated is True

    result = store.get(
        conversation.conversation_id,
        "cust-100",
    )

    assert result.order_id == "ORD-1004"


def test_other_customer_cannot_update_context():
    store = ConversationStore()
    conversation = store.create("cust-100")

    updated = store.update_order(
        conversation.conversation_id,
        "cust-200",
        "ORD-2001",
    )

    assert updated is False

    result = store.get(
        conversation.conversation_id,
        "cust-100",
    )

    assert result.order_id is None


def test_expired_conversation(monkeypatch):
    current_time = [100.0]

    monkeypatch.setattr(
        "app.conversation.time.monotonic",
        lambda: current_time[0],
    )

    store = ConversationStore(ttl_seconds=30)
    conversation = store.create("cust-100")

    current_time[0] = 131.0

    assert store.get(
        conversation.conversation_id,
        "cust-100",
    ) is None


def test_conversation_capacity_limit():
    store = ConversationStore(max_conversations=1)

    store.create("cust-100")

    with pytest.raises(RuntimeError):
        store.create("cust-200")


def test_extract_single_order():
    assert extract_order_ids(
        "Where is ORD-1004?"
    ) == {"ORD-1004"}


def test_extract_multiple_orders():
    assert extract_order_ids(
        "Compare ORD-1001 and ord-1004"
    ) == {"ORD-1001", "ORD-1004"}


def test_extract_repeated_order():
    assert extract_order_ids(
        "Is ORD-1004 the same as ord-1004?"
    ) == {"ORD-1004"}


def test_no_order_id():
    assert extract_order_ids(
        "Can I cancel the remaining item?"
    ) == set()