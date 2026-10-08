import pytest
from app.schemas.intelligence import EnhancedProduct, MarketStats, SearchIntent
from app.intelligence.explainer import explain_recommendation

def test_explain_recommendation_full_data():
    product = EnhancedProduct(
        product_id="123",
        title="Test Phone",
        extracted_price=54999.0,
        rating=4.6,
        reviews=1200,
        buywise_score=85.0
    )
    market = MarketStats(
        products_analyzed=10,
        valid_prices_count=10,
        valid_ratings_count=10,
        median_price=59499.0
    )
    intent = SearchIntent(product_query="phone", budget_max=70000.0)
    
    explanation = explain_recommendation(product, market, intent, "best_value")
    
    assert explanation.summary.startswith("BuyWise recommends this as Best Value")
    assert len(explanation.factors) == 5
    names = [f.name for f in explanation.factors]
    assert "Price Advantage" in names
    assert "Rating Strength" in names
    assert "Budget Fit" in names
    assert "Strong Review Evidence" in names
    assert "Strong BuyWise Score" in names

def test_explain_recommendation_missing_data():
    product = EnhancedProduct(
        product_id="456",
        title="No Data Phone",
        extracted_price=None,
        rating=None,
        reviews=None,
        buywise_score=None
    )
    market = MarketStats(
        products_analyzed=10,
        valid_prices_count=10,
        valid_ratings_count=10,
        median_price=59499.0
    )
    intent = SearchIntent(product_query="phone", budget_max=70000.0)
    
    explanation = explain_recommendation(product, market, intent, "best_overall")
    
    assert explanation.summary.startswith("BuyWise recommends this as Best Overall")
    assert len(explanation.factors) == 0

def test_explain_recommendation_above_median():
    product = EnhancedProduct(
        product_id="789",
        title="Expensive Phone",
        extracted_price=80000.0,
        rating=4.2,
        reviews=30
    )
    market = MarketStats(
        products_analyzed=10,
        valid_prices_count=10,
        valid_ratings_count=10,
        median_price=59499.0
    )
    intent = SearchIntent(product_query="phone", budget_max=90000.0)
    
    explanation = explain_recommendation(product, market, intent, "premium_pick")
    
    names = [f.name for f in explanation.factors]
    assert "Premium Pricing" in names
    assert "Solid Rating" in names
    assert "Budget Fit" in names
    assert "Limited Review Evidence" in names
