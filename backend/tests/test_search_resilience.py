"""
Phase 6.2 — Feature 1: Smart Search Resilience Tests

All tests mock SerpApi via the serpapi_client so no real API credits are used.
"""
import pytest
from unittest.mock import patch, MagicMock, call
from fastapi.testclient import TestClient

from app.main import app
from app.services.search_service import (
    perform_commerce_search_with_fallback,
    FALLBACK_THRESHOLD,
)
from app.intelligence.intent_parser import parse_intent

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_products(n: int) -> list:
    """Return n minimal SerpApi shopping-result dicts."""
    return [
        {
            "title": f"Product {i}",
            "price": f"₹{1000 + i * 100}",
            "extracted_price": float(1000 + i * 100),
            "source": "Amazon",
            "product_id": f"pid-{i}",
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# 1. Sufficient initial results — exactly one SerpApi request
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_sufficient_results_no_fallback(mock_client):
    """If initial search returns >= FALLBACK_THRESHOLD products, no fallback."""
    mock_client.search_google_shopping.return_value = {
        "shopping_results": _make_products(FALLBACK_THRESHOLD)
    }

    intent = parse_intent("wireless headphones")
    result, fallback_used = perform_commerce_search_with_fallback(
        original_query="wireless headphones",
        fallback_query=intent.product_query,
    )

    assert len(result.products) == FALLBACK_THRESHOLD
    assert fallback_used is False
    # Only one call to the API
    mock_client.search_google_shopping.assert_called_once()


@patch("app.services.search_service.serpapi_client")
def test_more_than_threshold_no_fallback(mock_client):
    """10 results — no fallback, single API call."""
    mock_client.search_google_shopping.return_value = {
        "shopping_results": _make_products(10)
    }

    intent = parse_intent("laptop under 50000")
    result, fallback_used = perform_commerce_search_with_fallback(
        original_query="laptop under 50000",
        fallback_query=intent.product_query,
    )

    assert len(result.products) == 10
    assert fallback_used is False
    mock_client.search_google_shopping.assert_called_once()


# ---------------------------------------------------------------------------
# 2. Sparse initial results — fallback triggered (at most ONE extra request)
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_sparse_initial_triggers_fallback(mock_client):
    """3 initial products triggers exactly one fallback."""
    sparse_results = _make_products(3)
    fallback_results = _make_products(8)

    mock_client.search_google_shopping.side_effect = [
        {"shopping_results": sparse_results},
        {"shopping_results": fallback_results},
    ]

    intent = parse_intent("cheap wireless headphones under 5000")
    result, fallback_used = perform_commerce_search_with_fallback(
        original_query="cheap wireless headphones under 5000",
        fallback_query=intent.product_query,
    )

    assert fallback_used is True
    assert len(result.products) == 8
    # Exactly two API calls total (initial + one fallback)
    assert mock_client.search_google_shopping.call_count == 2


@patch("app.services.search_service.serpapi_client")
def test_zero_initial_results_triggers_fallback(mock_client):
    """Zero initial results triggers fallback when fallback query is distinct."""
    mock_client.search_google_shopping.side_effect = [
        {"shopping_results": []},
        {"shopping_results": _make_products(6)},
    ]

    intent = parse_intent("best gaming laptop under 60000")
    result, fallback_used = perform_commerce_search_with_fallback(
        original_query="best gaming laptop under 60000",
        fallback_query=intent.product_query,
    )

    assert fallback_used is True
    assert len(result.products) == 6
    assert mock_client.search_google_shopping.call_count == 2


# ---------------------------------------------------------------------------
# 3. Fallback query is distinct from the normalized original
# ---------------------------------------------------------------------------

def test_fallback_query_differs_from_original():
    """Intent parser strips budget phrases — fallback query must differ."""
    query = "wireless headphones under 5000"
    intent = parse_intent(query)
    fallback = intent.product_query

    norm_original = " ".join(query.strip().lower().split())
    norm_fallback = " ".join(fallback.strip().lower().split())
    # "under 5000" is stripped, so queries must differ
    assert norm_fallback != norm_original
    assert "5000" not in norm_fallback
    assert "under" not in norm_fallback
    assert "headphones" in norm_fallback


def test_fallback_query_differs_budget_phrases():
    """All budget-phrase variants are stripped from the fallback query."""
    cases = [
        ("laptop below 80000", "laptop"),
        ("earbuds upto 2000", "earbuds"),
        ("phone between 15000 and 25000", "phone"),
        ("gaming mouse above 500", "gaming mouse"),
    ]
    for query, expected_core in cases:
        intent = parse_intent(query)
        assert expected_core in intent.product_query.lower(), (
            f"Expected '{expected_core}' in product_query for '{query}', "
            f"got '{intent.product_query}'"
        )
        # No budget numbers should remain
        for digit in ["80000", "2000", "15000", "25000", "500"]:
            assert digit not in intent.product_query, (
                f"Budget number '{digit}' should not appear in product_query "
                f"for '{query}', got '{intent.product_query}'"
            )


# ---------------------------------------------------------------------------
# 4. Empty or equivalent fallback query — no additional request
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_empty_fallback_query_no_extra_request(mock_client):
    """Empty fallback_query skips the fallback, even with sparse initial."""
    mock_client.search_google_shopping.return_value = {
        "shopping_results": _make_products(2)
    }

    result, fallback_used = perform_commerce_search_with_fallback(
        original_query="laptop",
        fallback_query="",  # empty
    )

    assert fallback_used is False
    # Only one API call — no fallback
    mock_client.search_google_shopping.assert_called_once()


@patch("app.services.search_service.serpapi_client")
def test_identical_fallback_query_no_extra_request(mock_client):
    """Fallback identical to original (after normalisation) → no extra request."""
    mock_client.search_google_shopping.return_value = {
        "shopping_results": _make_products(1)
    }

    result, fallback_used = perform_commerce_search_with_fallback(
        original_query="laptop",
        fallback_query="laptop",  # same after normalisation
    )

    assert fallback_used is False
    mock_client.search_google_shopping.assert_called_once()


@patch("app.services.search_service.serpapi_client")
def test_whitespace_equivalent_fallback_no_extra_request(mock_client):
    """Fallback that differs only in whitespace/case → treated as identical."""
    mock_client.search_google_shopping.return_value = {
        "shopping_results": _make_products(2)
    }

    result, fallback_used = perform_commerce_search_with_fallback(
        original_query="laptop",
        fallback_query="  LAPTOP  ",
    )

    assert fallback_used is False
    mock_client.search_google_shopping.assert_called_once()


# ---------------------------------------------------------------------------
# 5. Budget constraints preserved after fallback
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_budget_preserved_through_fallback(mock_client):
    """
    When a fallback is triggered, the original intent (including budget_max)
    must be intact in the final IntelligenceResponse.
    """
    sparse = _make_products(2)
    rich = _make_products(7)
    mock_client.search_google_shopping.side_effect = [
        {"shopping_results": sparse},
        {"shopping_results": rich},
    ]

    response = client.get("/api/search?q=headphones+under+5000&mode=balanced")
    assert response.status_code == 200
    data = response.json()

    # Budget must be present in the parsed intent
    assert data["intent"] is not None
    assert data["intent"]["budget_max"] == 5000.0
    # Fallback diagnostic should indicate it was used
    assert data.get("search_used_fallback") is True


# ---------------------------------------------------------------------------
# 6. Fallback returns useful results — processed correctly
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_fallback_results_processed_by_pipeline(mock_client):
    """Fallback products go through scoring, market analysis, etc."""
    sparse = _make_products(2)
    rich = _make_products(6)
    mock_client.search_google_shopping.side_effect = [
        {"shopping_results": sparse},
        {"shopping_results": rich},
    ]

    response = client.get("/api/search?q=best+earbuds+under+3000&mode=balanced")
    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 6
    assert data["market"] is not None
    assert data["confidence"] is not None
    # All products should have been scored
    for p in data["products"]:
        assert p["buywise_score"] is not None or p["extracted_price"] is None


# ---------------------------------------------------------------------------
# 7. Fallback fails after successful initial — initial results retained
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_fallback_failure_retains_initial_results(mock_client):
    """If fallback raises an error, sparse initial results are returned safely."""
    from fastapi import HTTPException

    sparse = _make_products(2)

    mock_client.search_google_shopping.side_effect = [
        {"shopping_results": sparse},
        HTTPException(status_code=502, detail="Search provider error"),
    ]

    result, fallback_used = perform_commerce_search_with_fallback(
        original_query="cheap tablet",
        fallback_query="tablet",
    )

    # Fallback was attempted (used=True) but failed; original retained
    assert fallback_used is True
    assert len(result.products) == 2  # original 2 products intact
    assert result.query == "cheap tablet"


@patch("app.services.search_service.serpapi_client")
def test_fallback_unexpected_exception_retains_initial(mock_client):
    """Unexpected exception during fallback must not propagate; retain original."""
    sparse = _make_products(3)

    mock_client.search_google_shopping.side_effect = [
        {"shopping_results": sparse},
        RuntimeError("Unexpected network failure"),
    ]

    result, fallback_used = perform_commerce_search_with_fallback(
        original_query="wireless earbuds",
        fallback_query="earbuds",
    )

    assert fallback_used is True
    assert len(result.products) == 3  # sparse but preserved


# ---------------------------------------------------------------------------
# 8. Initial search failure — existing error handling intact
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_initial_search_failure_propagates(mock_client):
    """If the initial search fails (HTTPException), the error propagates normally."""
    from fastapi import HTTPException

    mock_client.search_google_shopping.side_effect = HTTPException(
        status_code=502, detail="Search provider error"
    )

    response = client.get("/api/search?q=headphones&mode=balanced")
    # The HTTPException from the initial search should cause a 502
    assert response.status_code == 502


# ---------------------------------------------------------------------------
# 9. Decision mode and response structure compatibility
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_decision_mode_compatible_with_fallback(mock_client):
    """All decision modes work correctly when fallback is triggered."""
    sparse = _make_products(3)
    rich = _make_products(6)

    for mode in ["balanced", "cheapest", "best_value", "quality_first"]:
        mock_client.search_google_shopping.reset_mock()
        mock_client.search_google_shopping.side_effect = [
            {"shopping_results": sparse},
            {"shopping_results": rich},
        ]

        response = client.get(f"/api/search?q=headphones+under+5000&mode={mode}")
        assert response.status_code == 200, f"Mode {mode!r} failed"
        data = response.json()
        assert data["decision_mode"] == mode
        assert data["count"] == 6
        # Standard response fields all present
        for field in ["intent", "market", "recommendations", "products", "confidence"]:
            assert field in data, f"Field '{field}' missing for mode {mode!r}"


@patch("app.services.search_service.serpapi_client")
def test_search_used_fallback_field_absent_when_not_needed(mock_client):
    """search_used_fallback should be None/absent when no fallback occurred."""
    mock_client.search_google_shopping.return_value = {
        "shopping_results": _make_products(FALLBACK_THRESHOLD)
    }

    response = client.get("/api/search?q=headphones&mode=balanced")
    assert response.status_code == 200
    data = response.json()
    # When no fallback, the field should be absent or falsy
    assert not data.get("search_used_fallback")


# ---------------------------------------------------------------------------
# 10. No live SerpApi calls — verify all tests use mocks
# ---------------------------------------------------------------------------

def test_fallback_threshold_constant():
    """FALLBACK_THRESHOLD should be 5 (matches specification)."""
    assert FALLBACK_THRESHOLD == 5
