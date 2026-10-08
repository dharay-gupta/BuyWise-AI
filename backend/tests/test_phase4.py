"""
Phase 4 automated tests.

All tests use mocked or in-memory data — no SerpApi calls are made.
Existing Phase 1–3 tests remain in their original test files.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.intelligence import EnhancedProduct, MarketStats
from app.intelligence.intent_parser import parse_intent
from app.intelligence.market_analysis import analyze_market
from app.intelligence.scoring import score_product, DECISION_MODE_WEIGHTS, ALLOWED_MODES
from app.intelligence.recommendations import generate_recommendations
from app.intelligence.merchant_analysis import analyze_merchants
from app.intelligence.market_insight import generate_market_insights
from app.intelligence.tradeoffs import generate_savings_text

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_market(low: float, high: float) -> MarketStats:
    """Minimal market with two price anchors."""
    return analyze_market([
        EnhancedProduct(extracted_price=low),
        EnhancedProduct(extracted_price=high),
    ])


def _make_product(price=1000.0, rating=4.0, reviews=500) -> EnhancedProduct:
    return EnhancedProduct(
        product_id="test-1",
        title="Test Product",
        extracted_price=price,
        rating=rating,
        reviews=reviews,
    )


# ---------------------------------------------------------------------------
# 1. Decision mode validation — invalid mode returns 400
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_invalid_mode_returns_400(mock_serpapi):
    mock_serpapi.search_google_shopping.return_value = {"shopping_results": []}
    response = client.get("/api/search?q=headphones&mode=super_mode")
    assert response.status_code == 400
    assert "Invalid decision mode" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 2. Balanced scoring weights
# ---------------------------------------------------------------------------

def test_balanced_scoring_weights():
    w = DECISION_MODE_WEIGHTS["balanced"]
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["price"] == 0.35
    assert w["rating"] == 0.30
    assert w["review_confidence"] == 0.15
    assert w["market_position"] == 0.20


# ---------------------------------------------------------------------------
# 3. Cheapest scoring weights
# ---------------------------------------------------------------------------

def test_cheapest_scoring_weights():
    w = DECISION_MODE_WEIGHTS["cheapest"]
    assert abs(sum(w.values()) - 1.0) < 1e-9
    # Price should dominate
    assert w["price"] >= 0.55


# ---------------------------------------------------------------------------
# 4. Best Value scoring weights
# ---------------------------------------------------------------------------

def test_best_value_scoring_weights():
    w = DECISION_MODE_WEIGHTS["best_value"]
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["price"] == 0.40


# ---------------------------------------------------------------------------
# 5. Quality First scoring weights
# ---------------------------------------------------------------------------

def test_quality_first_scoring_weights():
    w = DECISION_MODE_WEIGHTS["quality_first"]
    assert abs(sum(w.values()) - 1.0) < 1e-9
    # Rating + review_confidence should dominate
    assert w["rating"] + w["review_confidence"] >= 0.70
    # Price should be minimal
    assert w["price"] <= 0.15


# ---------------------------------------------------------------------------
# 6. Natural-language budget extraction (extended patterns)
# ---------------------------------------------------------------------------

def test_budget_extraction_extended():
    cases = [
        ("wireless headphones under 3000", 3000.0),
        ("best headphones below ₹5000", 5000.0),
        ("cheap gaming mouse under 2k", 2000.0),
        ("premium laptop under 80000", 80000.0),
        ("best value earbuds under 2000", 2000.0),
        ("quality first headphones under 5000", 5000.0),
        ("laptop between 50000 and 80000", 80000.0),
        ("earbuds upto 1500", 1500.0),
        ("phones up to 15000", 15000.0),
    ]
    for query, expected_max in cases:
        i = parse_intent(query)
        assert i.budget_max == expected_max, (
            f"Query '{query}': expected budget_max={expected_max}, got {i.budget_max}"
        )


# ---------------------------------------------------------------------------
# 7. Natural-language priority extraction
# ---------------------------------------------------------------------------

def test_priority_extraction():
    cases = [
        ("quality first headphones", "quality_first"),
        ("quality-first laptop", "quality_first"),
        ("best value earbuds", "best_value"),
        ("value for money mouse", "best_value"),
        ("cheap gaming mouse", "cheap"),
        ("affordable laptop", "cheap"),
        ("premium headphones", "premium"),
        ("wireless headphones", "balanced"),  # no priority signal → balanced
    ]
    for query, expected_priority in cases:
        i = parse_intent(query)
        assert i.priority == expected_priority, (
            f"Query '{query}': expected priority={expected_priority}, got {i.priority}"
        )


# ---------------------------------------------------------------------------
# 8. Market savings calculation
# ---------------------------------------------------------------------------

def test_market_savings_text():
    market = _make_market(500.0, 2000.0)
    # median = 1250.0

    cheap_product = EnhancedProduct(extracted_price=500.0, title="Cheap")
    savings = generate_savings_text(cheap_product, market)
    assert savings is not None
    assert "below" in savings.lower()

    expensive_product = EnhancedProduct(extracted_price=2000.0, title="Expensive")
    savings2 = generate_savings_text(expensive_product, market)
    assert savings2 is not None
    assert "above" in savings2.lower()

    no_price = EnhancedProduct(title="No Price")
    assert generate_savings_text(no_price, market) is None


# ---------------------------------------------------------------------------
# 9. Merchant aggregation
# ---------------------------------------------------------------------------

def test_merchant_aggregation():
    products = [
        EnhancedProduct(source="Amazon.in", extracted_price=1000.0),
        EnhancedProduct(source="Amazon.in", extracted_price=1200.0),
        EnhancedProduct(source="Flipkart", extracted_price=900.0),
        EnhancedProduct(source="Flipkart", extracted_price=950.0),
        EnhancedProduct(source="Flipkart", extracted_price=1100.0),
        EnhancedProduct(source=None, extracted_price=800.0),  # source-less
    ]
    stats = analyze_merchants(products)
    assert len(stats.merchants) > 0

    # Flipkart has 3 listings — should be first (sorted by count desc)
    assert stats.merchants[0].name == "Flipkart"
    assert stats.merchants[0].count == 3

    # Amazon has 2
    amazon = next((m for m in stats.merchants if m.name == "Amazon.in"), None)
    assert amazon is not None
    assert amazon.count == 2
    assert amazon.avg_price == 1100.0
    assert amazon.lowest_price == 1000.0

    # Note is set
    assert "observed" in stats.note.lower()


# ---------------------------------------------------------------------------
# 10. Comparison data (product data shape for frontend comparison)
# ---------------------------------------------------------------------------

def test_comparison_data_fields():
    """
    Frontend comparison uses the enriched product objects returned by /api/search.
    Verify that all fields needed for comparison are present after scoring.
    """
    market = _make_market(500.0, 3000.0)
    intent = parse_intent("headphones")
    intent.priority = "balanced"

    p = _make_product(price=1000.0, rating=4.2, reviews=300)
    scored = score_product(p, market, intent)

    assert scored.buywise_score is not None
    assert scored.score_breakdown is not None
    assert scored.price_percentile is not None
    assert scored.review_confidence is not None
    assert scored.extracted_price is not None
    assert scored.rating is not None
    assert scored.reviews is not None


# ---------------------------------------------------------------------------
# 11. Missing rating — graceful handling
# ---------------------------------------------------------------------------

def test_missing_rating_graceful():
    market = _make_market(500.0, 2000.0)
    intent = parse_intent("headphones")
    intent.priority = "balanced"

    p = EnhancedProduct(extracted_price=1000.0, rating=None, reviews=None)
    scored = score_product(p, market, intent)

    # Has price data, so score should be computable (not None)
    assert scored.buywise_score is not None
    # Rating component should be 0
    assert scored.score_breakdown is not None
    assert scored.score_breakdown.rating == 0.0


# ---------------------------------------------------------------------------
# 12. Missing review count — graceful handling
# ---------------------------------------------------------------------------

def test_missing_reviews_graceful():
    market = _make_market(500.0, 2000.0)
    intent = parse_intent("headphones")
    intent.priority = "balanced"

    p = EnhancedProduct(extracted_price=1000.0, rating=4.5, reviews=None)
    scored = score_product(p, market, intent)

    assert scored.buywise_score is not None
    # review_confidence should be 0 when reviews is None
    assert scored.review_confidence == 0.0
    assert scored.score_breakdown.review_confidence == 0.0


# ---------------------------------------------------------------------------
# 13. Missing price — graceful handling
# ---------------------------------------------------------------------------

def test_missing_price_graceful():
    market = _make_market(500.0, 2000.0)
    intent = parse_intent("headphones")
    intent.priority = "balanced"

    p = EnhancedProduct(extracted_price=None, rating=4.5, reviews=200)
    scored = score_product(p, market, intent)

    # Has rating + reviews → score is computable
    assert scored.buywise_score is not None
    # Price and market_position should be 0
    assert scored.score_breakdown.price == 0.0
    assert scored.score_breakdown.market_position == 0.0


# ---------------------------------------------------------------------------
# 14. No products — graceful handling
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_no_products_graceful(mock_serpapi):
    mock_serpapi.search_google_shopping.return_value = {"shopping_results": []}
    response = client.get("/api/search?q=xyznonexistent1234")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["products"] == []


# ---------------------------------------------------------------------------
# 15. Valid modes accepted
# ---------------------------------------------------------------------------

@patch("app.services.search_service.serpapi_client")
def test_valid_modes_accepted(mock_serpapi):
    mock_serpapi.search_google_shopping.return_value = {
        "shopping_results": [
            {"title": "Test", "extracted_price": 999.0, "rating": 4.0, "reviews": 100}
        ]
    }
    for valid_mode in ["balanced", "cheapest", "best_value", "quality_first"]:
        response = client.get(f"/api/search?q=test&mode={valid_mode}")
        assert response.status_code == 200, f"Mode '{valid_mode}' should be accepted"
        data = response.json()
        assert data["decision_mode"] == valid_mode


# ---------------------------------------------------------------------------
# 16. Phase 3 behavior still intact (best_overall, cheapest, hidden_gem)
# ---------------------------------------------------------------------------

def test_phase3_recommendations_intact():
    """
    Ensures Phase 3 recommendation logic continues to work correctly after
    Phase 4 changes.
    """
    market = analyze_market([
        EnhancedProduct(extracted_price=1000.0),
        EnhancedProduct(extracted_price=5000.0),
    ])

    p1 = EnhancedProduct(
        product_id="1", title="Cheap Pick",
        extracted_price=1000.0, rating=4.0, reviews=500,
        buywise_score=85.0, review_confidence=0.3,
    )
    p2 = EnhancedProduct(
        product_id="2", title="Best Pick",
        extracted_price=2500.0, rating=4.8, reviews=5000,
        buywise_score=95.0, review_confidence=0.7,
    )
    p3 = EnhancedProduct(
        product_id="3", title="Hidden",
        extracted_price=2000.0, rating=4.5, reviews=20,
        buywise_score=80.0, review_confidence=0.15,
    )

    recs = generate_recommendations([p1, p2, p3], market)

    assert recs.best_overall is not None
    assert recs.best_overall.product_id == "2"
    assert recs.cheapest is not None
    assert recs.cheapest.product_id == "1"
    assert recs.hidden_gem is not None
    assert recs.hidden_gem.product_id == "3"
