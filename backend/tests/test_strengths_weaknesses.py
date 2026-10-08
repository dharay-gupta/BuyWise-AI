import pytest
from app.schemas.intelligence import EnhancedProduct, MarketStats, SearchIntent
from app.intelligence.strengths_weaknesses import analyze_strengths_weaknesses

def test_strengths_weaknesses_strong_product():
    product = EnhancedProduct(
        product_id="123",
        title="Strong Phone",
        extracted_price=50000.0,
        rating=4.7,
        reviews=800,
        buywise_score=88.0
    )
    market = MarketStats(
        products_analyzed=10,
        valid_prices_count=10,
        valid_ratings_count=10,
        median_price=60000.0
    )
    intent = SearchIntent(product_query="phone", budget_max=70000.0)
    
    analysis = analyze_strengths_weaknesses(product, market, intent)
    
    assert len(analysis.strengths) == 5
    assert len(analysis.weaknesses) == 0
    assert "Price is 17% below the observed market median." in analysis.strengths

def test_strengths_weaknesses_weak_product():
    product = EnhancedProduct(
        product_id="456",
        title="Weak Phone",
        extracted_price=80000.0,
        rating=3.5,
        reviews=10,
        buywise_score=40.0
    )
    market = MarketStats(
        products_analyzed=10,
        valid_prices_count=10,
        valid_ratings_count=10,
        median_price=60000.0
    )
    intent = SearchIntent(product_query="phone", budget_max=70000.0)
    
    analysis = analyze_strengths_weaknesses(product, market, intent)
    
    assert len(analysis.strengths) == 0
    assert len(analysis.weaknesses) == 5
    assert "Price is 33% above the observed market median." in analysis.weaknesses
    assert "Exceeds stated budget of ₹70,000." in analysis.weaknesses

def test_strengths_weaknesses_missing_data():
    product = EnhancedProduct(
        product_id="789",
        title="Missing Phone",
        extracted_price=None,
        rating=None,
        reviews=None,
        buywise_score=None
    )
    market = MarketStats(
        products_analyzed=10,
        valid_prices_count=10,
        valid_ratings_count=10,
        median_price=60000.0
    )
    intent = SearchIntent(product_query="phone", budget_max=70000.0)
    
    analysis = analyze_strengths_weaknesses(product, market, intent)
    
    assert len(analysis.strengths) == 0
    assert len(analysis.weaknesses) == 0
    assert len(analysis.neutral) == 0
