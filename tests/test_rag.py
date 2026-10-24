
import json
from unittest.mock import Mock

import httpx
import pytest

from app.rag import RAGService
from app.structured_output import ANSWER_SCHEMA


def mock_answer(
    answer="Personalized products cannot be returned [returns-3].",
    source_ids=None,
    status="answered",
    claims=None,
):
    if source_ids is None:
        source_ids = ["returns-3"]

    if claims is None:
        claims = (
            [
                {
                    "text": (
                        "Personalized products and gift cards "
                        "are not eligible for standard returns"
                    ),
                    "source_ids": source_ids,
                }
            ]
            if status == "answered"
            else []
        )

    return {
        "message": {
            "content": json.dumps({
                "status": status,
                "answer": answer,
                "claims": claims,
            })
        }
    }


@pytest.fixture
def rag_service():
    retriever = Mock()
    client = Mock()

    retriever.search.return_value = [
        {
            "id": "returns-3",
            "source": "returns.md",
            "heading": "Non-Returnable Items",
            "text": (
                "Personalized products and gift cards "
                "are not eligible for standard returns."
            ),
            "score": 0.5253,
        }
    ]

    response = Mock()
    response.json.return_value = mock_answer()
    client.post.return_value = response

    return RAGService(
        retriever=retriever,
        client=client,
    )


def test_grounded_answer(rag_service):
    result = rag_service.answer(
        "Can I return a personalized product?"
    )

    assert "not eligible for standard returns" in result["answer"]
    assert "[returns-3]" in result["answer"]
    assert result["sources"][0]["id"] == "returns-3"


def test_correct_model_configuration(rag_service):
    rag_service.answer("Can I return a personalized product?")

    payload = rag_service.client.post.call_args.kwargs["json"]

    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["format"] == ANSWER_SCHEMA
    assert payload["options"]["temperature"] == 0.2
    assert payload["options"]["num_predict"] == 600


def test_retrieved_context_is_provided(rag_service):
    rag_service.answer("Can I return a personalized product?")

    payload = rag_service.client.post.call_args.kwargs["json"]
    user_message = payload["messages"][1]["content"]

    assert "returns-3" in user_message
    assert "Personalized products" in user_message


def test_empty_question(rag_service):
    with pytest.raises(ValueError):
        rag_service.answer("   ")

    rag_service.client.post.assert_not_called()


def test_no_retrieval_results(rag_service):
    rag_service.retriever.search.return_value = []

    result = rag_service.answer("Unknown question")

    assert "don't have enough information" in result["answer"]
    assert result["sources"] == []
    rag_service.client.post.assert_not_called()


def test_empty_model_response(rag_service):
    rag_service.client.post.return_value.json.return_value = {
        "message": {"content": ""}
    }

    with pytest.raises(RuntimeError, match="empty answer"):
        rag_service.answer("Return policy?")


def test_model_http_error(rag_service):
    rag_service.client.post.side_effect = httpx.ConnectError(
        "Ollama unavailable"
    )

    with pytest.raises(httpx.ConnectError):
        rag_service.answer("Return policy?")


def test_rejects_fabricated_citation(rag_service):
    rag_service.client.post.return_value.json.return_value = mock_answer(
        answer="Express shipping costs €9.90 [tracking-1].",
        source_ids=["tracking-1"],
    )

    result = rag_service.answer(
        "How much does express shipping cost?"
    )

    assert result["sources"] == []
    assert "couldn't verify" in result["answer"]
    rag_service.client.post.assert_called_once()


def test_generates_citation_from_verified_claim(rag_service):
    rag_service.client.post.return_value.json.return_value = mock_answer(
        answer="Personalized products cannot be returned."
    )

    result = rag_service.answer("Can I return this?")

    assert "[returns-3]" in result["answer"]
    assert "not eligible for standard returns" in result["answer"]
    assert result["sources"][0]["id"] == "returns-3"


def test_only_returns_cited_sources(rag_service):
    rag_service.retriever.search.return_value.append({
        "id": "shipping-2",
        "source": "shipping.md",
        "heading": "Standard Shipping",
        "text": "Standard shipping costs €4.90.",
        "score": 0.4,
    })

    result = rag_service.answer("Can I return this?")

    assert [source["id"] for source in result["sources"]] == [
        "returns-3"
    ]


def test_unknown_order_uses_safe_fallback(rag_service):
    result = rag_service.answer(
        "Where is my order ORD-9999?"
    )

    assert "can't access your order details" in result["answer"]
    assert result["sources"] == []
    rag_service.client.post.assert_not_called()


def test_rag_rejects_unsupported_refund(rag_service):
    rag_service.client.post.return_value.json.return_value = mock_answer(
        answer=(
            "You can get a refund for your damaged "
            "personalized item [returns-3]."
        ),
        claims=[
            {
                "text": "A refund is guaranteed",
                "source_ids": ["returns-3"],
            }
        ],
    )

    result = rag_service.answer(
        "My personalized item arrived damaged."
    )

    assert result["sources"] == []
    assert "couldn't verify" in result["answer"]


def test_rag_preserves_supported_answer(rag_service):
    result = rag_service.answer(
        "Can I return a personalized product?"
    )

    assert "not eligible for standard returns" in result["answer"]
    assert "[returns-3]" in result["answer"]
    assert result["sources"][0]["id"] == "returns-3"


def test_insufficient_evidence_response(rag_service):
    rag_service.client.post.return_value.json.return_value = mock_answer(
        answer="This information is unavailable.",
        status="insufficient_evidence",
    )

    result = rag_service.answer(
        "Who won the 2022 FIFA World Cup?"
    )

    assert "don't have enough" in result["answer"]
    assert result["sources"] == []


def test_rejects_claim_source_mismatch(rag_service):
    rag_service.retriever.search.return_value.append({
        "id": "returns-1",
        "source": "returns.md",
        "heading": "Return Window",
        "text": "Eligible products can be returned within 30 days.",
        "score": 0.4,
    })

    rag_service.client.post.return_value.json.return_value = mock_answer(
        claims=[
            {
                "text": (
                    "Personalized products and gift cards "
                    "are not eligible for standard returns"
                ),
                "source_ids": ["returns-1"],
            }
        ]
    )

    result = rag_service.answer("Can I return this?")

    assert result["sources"] == []
    assert "couldn't verify" in result["answer"]


def test_rejects_invalid_structured_json(rag_service):
    rag_service.client.post.return_value.json.return_value = {
        "message": {
            "content": "{invalid JSON"
        }
    }

    result = rag_service.answer("Can I return this?")

    assert result["sources"] == []
    assert "couldn't verify" in result["answer"]


def test_rejects_claim_not_present_in_source(rag_service):
    rag_service.client.post.return_value.json.return_value = mock_answer(
        answer="All products have lifetime warranties.",
        claims=[
            {
                "text": "All products have lifetime warranties",
                "source_ids": ["returns-3"],
            }
        ],
    )

    result = rag_service.answer(
        "Do products have lifetime warranties?"
    )

    assert result["sources"] == []
    assert "couldn't verify" in result["answer"]


def test_excludes_unsupported_freeform_statement(rag_service):
    rag_service.client.post.return_value.json.return_value = mock_answer(
        answer=(
            "All products have lifetime warranties. "
            "Personalized products cannot be returned."
        )
    )

    result = rag_service.answer(
        "Can I return a personalized product?"
    )

    assert "lifetime warranties" not in result["answer"]
    assert "not eligible for standard returns" in result["answer"]
    assert "[returns-3]" in result["answer"]