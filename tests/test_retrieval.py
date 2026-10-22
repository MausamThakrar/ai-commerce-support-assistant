
import pytest

from app.retrieval import KnowledgeRetriever


@pytest.fixture(scope="module")
def retriever():
    return KnowledgeRetriever()


@pytest.mark.parametrize(
    "query,expected_source,expected_heading",
    [
        (
            "How much does express shipping cost?",
            "shipping.md",
            "Express Shipping",
        ),
        (
            "Can I return a personalized product?",
            "returns.md",
            "Non-Returnable Items",
        ),
        (
            "How long does a refund take?",
            "returns.md",
            "Refund Processing",
        ),
        (
            "Is the backpack water resistant?",
            "products.md",
            "Alpine Trail Backpack 28L",
        ),
        (
            "Can I cancel an already shipped order?",
            "cancellations.md",
            "Shipped Orders",
        ),
    ],
)
def test_retrieval_top_result(
    retriever, query, expected_source, expected_heading
):
    results = retriever.search(query, top_k=3)

    assert results
    assert results[0]["source"] == expected_source
    assert results[0]["heading"] == expected_heading


def test_empty_query(retriever):
    assert retriever.search("") == []


def test_top_k_limit(retriever):
    results = retriever.search("shipping", top_k=2)
    assert len(results) == 2


def test_result_contains_source_metadata(retriever):
    results = retriever.search("return policy", top_k=1)

    assert results
    assert "id" in results[0]
    assert "source" in results[0]
    assert "heading" in results[0]
    assert "text" in results[0]
    assert "score" in results[0]