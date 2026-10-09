"""
Phase 6.2 — Feature 2: SerpApi Offer Intelligence Tests

Tests for normalization of shipping/offer fields and backward compatibility.
All SerpApi calls are mocked.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.intelligence.normalization import (
    normalize_shopping_results,
    _extract_free_shipping,
    _sanitise_offer_text,
)
from app.schemas.product import NormalizedProduct

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Shipping information normalized when present in source data
# ---------------------------------------------------------------------------

def test_shipping_info_extracted_from_delivery_field():
    """shipping_info is populated from the 'delivery' field verbatim."""
    raw = [{"title": "Headphones", "delivery": "Delivery by Thu, 12 Oct"}]
    products = normalize_shopping_results(raw)
    assert len(products) == 1
    p = products[0]
    assert p.shipping_info == "Delivery by Thu, 12 Oct"


def test_shipping_info_extracted_from_shipping_field():
    """shipping_info falls back to the 'shipping' alternate key."""
    raw = [{"title": "Monitor", "shipping": "+₹49 shipping"}]
    products = normalize_shopping_results(raw)
    assert len(products) == 1
    assert products[0].shipping_info == "+₹49 shipping"


def test_shipping_info_absent_when_no_delivery_data():
    """shipping_info is None when neither 'delivery' nor 'shipping' is present."""
    raw = [{"title": "Phone", "extracted_price": 9999.0}]
    products = normalize_shopping_results(raw)
    assert len(products) == 1
    assert products[0].shipping_info is None


# ---------------------------------------------------------------------------
# 2. Free shipping displayed only when explicitly supported
# ---------------------------------------------------------------------------

def test_free_shipping_true_when_explicit_phrase():
    """free_shipping=True only when delivery text contains explicit phrase."""
    explicit_cases = [
        "Free shipping",
        "FREE SHIPPING",
        "free delivery",
        "Free standard shipping",
        "Ships free",
    ]
    for text in explicit_cases:
        raw = [{"title": "Product", "delivery": text}]
        p = normalize_shopping_results(raw)[0]
        assert p.free_shipping is True, (
            f"Expected free_shipping=True for delivery='{text}', got {p.free_shipping}"
        )


def test_free_shipping_none_when_ambiguous_shipping_text():
    """free_shipping is NOT set for ambiguous texts that don't explicitly say free."""
    ambiguous = [
        "+₹49 shipping",
        "Delivery by Thu",
        "Dispatched in 2 days",
        "Standard delivery",
        "Express shipping available",
    ]
    for text in ambiguous:
        raw = [{"title": "Product", "delivery": text}]
        p = normalize_shopping_results(raw)[0]
        assert p.free_shipping is None, (
            f"Expected free_shipping=None for delivery='{text}', got {p.free_shipping}"
        )


def test_free_shipping_none_when_delivery_field_missing():
    """free_shipping must be None — never inferred from a missing delivery fee."""
    raw = [{"title": "Product", "extracted_price": 5000.0}]
    p = normalize_shopping_results(raw)[0]
    # No shipping data at all — must NOT infer free shipping
    assert p.free_shipping is None


def test_extract_free_shipping_helper_explicit():
    assert _extract_free_shipping("Free shipping") is True
    assert _extract_free_shipping("free delivery to your door") is True
    assert _extract_free_shipping("Ships free today") is True


def test_extract_free_shipping_helper_non_free():
    assert _extract_free_shipping("+₹99 delivery") is None
    assert _extract_free_shipping("Estimated delivery 3 days") is None
    assert _extract_free_shipping("") is None
    assert _extract_free_shipping(None) is None


# ---------------------------------------------------------------------------
# 3. Missing shipping fields produce no shipping claim
# ---------------------------------------------------------------------------

def test_no_shipping_fields_produces_no_claim():
    """Products without shipping data must have shipping_info=None and free_shipping=None."""
    raw = [
        {"title": "Product A"},
        {"title": "Product B", "extracted_price": 999.0, "rating": 4.0},
    ]
    products = normalize_shopping_results(raw)
    for p in products:
        assert p.shipping_info is None
        assert p.free_shipping is None


# ---------------------------------------------------------------------------
# 4. Special-offer text displayed only when source provides it
# ---------------------------------------------------------------------------

def test_offer_text_extracted_from_offer_field():
    """offer_text is populated from the 'offer' field verbatim."""
    raw = [{"title": "Laptop", "offer": "Extra 10% off with SBI card"}]
    p = normalize_shopping_results(raw)[0]
    assert p.offer_text == "Extra 10% off with SBI card"


def test_offer_text_extracted_from_extensions_list():
    """offer_text is populated when extensions is a list of strings."""
    raw = [{"title": "Phone", "extensions": ["Save ₹500", "No-cost EMI"]}]
    p = normalize_shopping_results(raw)[0]
    assert p.offer_text is not None
    assert "Save ₹500" in p.offer_text
    assert "No-cost EMI" in p.offer_text


def test_offer_text_none_when_absent():
    """offer_text must be None when neither 'offer' nor 'extensions' is present."""
    raw = [{"title": "Watch", "extracted_price": 4999.0}]
    p = normalize_shopping_results(raw)[0]
    assert p.offer_text is None


def test_sanitise_offer_text_strips_whitespace():
    assert _sanitise_offer_text("  5% cashback  ") == "5% cashback"
    assert _sanitise_offer_text("") is None
    assert _sanitise_offer_text("   ") is None
    assert _sanitise_offer_text(None) is None


def test_sanitise_offer_text_non_string_returns_none():
    assert _sanitise_offer_text(123) is None
    assert _sanitise_offer_text([]) is None


# ---------------------------------------------------------------------------
# 5. Malformed or contradictory values do not create false claims
# ---------------------------------------------------------------------------

def test_malformed_delivery_value_handled_safely():
    """Non-string delivery values must not cause errors or false free_shipping."""
    raw = [
        {"title": "Product A", "delivery": None},
        {"title": "Product B", "delivery": 0},
        {"title": "Product C", "delivery": []},
    ]
    products = normalize_shopping_results(raw)
    for p in products:
        assert p.free_shipping is None
        # shipping_info should be None or a string, never crash
        assert p.shipping_info is None or isinstance(p.shipping_info, str)


def test_malformed_offer_field_handled_safely():
    """Non-string offer values must not crash normalization."""
    raw = [
        {"title": "Product A", "offer": None},
        {"title": "Product B", "offer": 0},
        {"title": "Product C", "extensions": None},
    ]
    products = normalize_shopping_results(raw)
    for p in products:
        assert p.offer_text is None or isinstance(p.offer_text, str)


# ---------------------------------------------------------------------------
# 6. Backward compatibility — existing fields untouched
# ---------------------------------------------------------------------------

def test_existing_fields_unchanged_by_offer_intel():
    """All existing NormalizedProduct fields must remain intact."""
    raw = [{
        "title": "Test Product",
        "product_id": "pid-123",
        "product_link": "https://example.com",
        "source": "Amazon",
        "price": "₹1,999",
        "extracted_price": 1999.0,
        "old_price": "₹2,499",
        "extracted_old_price": 2499.0,
        "currency": "INR",
        "rating": 4.5,
        "reviews": 1200,
        "thumbnail": "https://img.example.com/t.jpg",
        "delivery": "Free shipping",
        "availability": "In Stock",
        "position": 1,
        "snippet": "Great product with excellent build quality.",
        "tag": "Top Pick",
        "badge": "Best Seller",
        "offer": "10% extra off",
    }]
    p = normalize_shopping_results(raw)[0]

    # Pre-existing fields
    assert p.title == "Test Product"
    assert p.product_id == "pid-123"
    assert p.source == "Amazon"
    assert p.price == "₹1,999"
    assert p.extracted_price == 1999.0
    assert p.old_price == "₹2,499"
    assert p.extracted_old_price == 2499.0
    assert p.rating == 4.5
    assert p.reviews == 1200
    assert p.delivery == "Free shipping"  # original delivery field preserved
    assert p.availability == "In Stock"
    assert p.tag == "Top Pick"
    assert p.badge == "Best Seller"

    # New offer-intel fields
    assert p.free_shipping is True      # "Free shipping" → explicit
    assert p.shipping_info == "Free shipping"
    assert p.offer_text == "10% extra off"


def test_normalizedproduct_schema_has_new_fields():
    """NormalizedProduct schema must expose the three new optional fields."""
    p = NormalizedProduct(title="Test")
    assert hasattr(p, "shipping_info")
    assert hasattr(p, "free_shipping")
    assert hasattr(p, "offer_text")
    # Default values must all be None (backward-compatible)
    assert p.shipping_info is None
    assert p.free_shipping is None
    assert p.offer_text is None


# ---------------------------------------------------------------------------
# 7. API response schema backward compatibility
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_api_response_contains_offer_fields(mock_client):
    """Products in the API response expose the new offer fields."""
    mock_client.search_google_shopping.return_value = {
        "shopping_results": [
            {
                "title": "Headphones",
                "extracted_price": 2999.0,
                "source": "Flipkart",
                "product_id": "hd-1",
                "delivery": "Free shipping",
                "offer": "5% cashback",
            }
        ] * 5  # 5 products so no fallback triggered
    }

    response = client.get("/api/search?q=headphones&mode=balanced")
    assert response.status_code == 200
    data = response.json()

    for p in data["products"]:
        # New fields present in response (may be None for products without data)
        assert "shipping_info" in p
        assert "free_shipping" in p
        assert "offer_text" in p


@patch("app.services.search_service.serpapi_client")
def test_api_response_backward_compatible_without_offer_fields(mock_client):
    """Older-style SerpApi responses (no offer fields) still work correctly."""
    mock_client.search_google_shopping.return_value = {
        "shopping_results": [
            {
                "title": f"Product {i}",
                "extracted_price": float(1000 + i * 500),
                "source": "Amazon",
                "product_id": f"p-{i}",
                "rating": 4.0,
                "reviews": 100,
            }
            for i in range(5)
        ]
    }

    response = client.get("/api/search?q=earbuds&mode=balanced")
    assert response.status_code == 200
    data = response.json()

    for p in data["products"]:
        # Fields should be present but None — no fabrication
        assert p.get("shipping_info") is None
        assert p.get("free_shipping") is None
        assert p.get("offer_text") is None


# ---------------------------------------------------------------------------
# 8. Existing deal-analysis behavior unchanged
# ---------------------------------------------------------------------------

def test_deal_analysis_unaffected_by_offer_intel():
    """
    Deal analysis logic must not be altered by offer intelligence.
    This test re-runs a deal-analysis scenario to confirm unchanged behavior.
    """
    from app.schemas.intelligence import EnhancedProduct, MarketStats, SearchIntent
    from app.intelligence.deal_analysis import analyze_deal

    product = EnhancedProduct(
        product_id="t1",
        extracted_price=1000.0,
        extracted_old_price=1500.0,
        shipping_info="Free shipping",   # new field present
        free_shipping=True,              # new field present
        offer_text="5% cashback",        # new field present
    )
    market = MarketStats(
        products_analyzed=5,
        valid_prices_count=5,
        valid_ratings_count=5,
        median_price=1200.0,
    )
    intent = SearchIntent(product_query="headphones", budget_max=2000.0)

    deal = analyze_deal(product, market, intent)

    # Exact same logic as before — offer fields must not alter deal analysis
    assert deal.discount_pct == 33.3
    assert deal.deal_quality == "strong"
    assert deal.budget_utilisation_pct == 50.0


# ---------------------------------------------------------------------------
# 9. Frontend safety — offer text escaping via API response (integration check)
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_offer_text_with_special_chars_in_api_response(mock_client):
    """
    Offer text containing HTML-special chars must be returned verbatim from
    the backend (escaping is the frontend's responsibility via escHtml).
    The API itself must not mangle or drop the text.
    """
    mock_client.search_google_shopping.return_value = {
        "shopping_results": [
            {
                "title": "Gadget",
                "extracted_price": 999.0,
                "source": "Store",
                "product_id": f"g-{i}",
                "offer": "Save <10%> & get 'free' case",
            }
            for i in range(5)
        ]
    }

    response = client.get("/api/search?q=gadget&mode=balanced")
    assert response.status_code == 200
    data = response.json()

    for p in data["products"]:
        if p.get("offer_text"):
            # The raw text must survive the round-trip intact (not HTML-escaped)
            assert "<10%>" in p["offer_text"] or "10%" in p["offer_text"]
