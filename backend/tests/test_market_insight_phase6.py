import pytest
from app.schemas.intelligence import EnhancedProduct, MarketStats, CrossMerchantInfo
from app.intelligence.market_insight import generate_market_insights

def test_cross_merchant_insight_generated():
    products = [
        EnhancedProduct(
            title="Test Product 1",
            extracted_price=100.0,
            cross_merchant=CrossMerchantInfo(merchant_count=2, merchants=[])
        ),
        EnhancedProduct(
            title="Test Product 2",
            extracted_price=150.0,
            cross_merchant=CrossMerchantInfo(merchant_count=1, merchants=[])
        )
    ]
    market = MarketStats(products_analyzed=2, valid_prices_count=2, valid_ratings_count=0)
    insights = generate_market_insights(products, market)
    
    assert any("offered by multiple observed merchants" in insight for insight in insights)

def test_cross_merchant_insight_not_generated_when_no_duplicates():
    products = [
        EnhancedProduct(
            title="Test Product 1",
            extracted_price=100.0,
            cross_merchant=CrossMerchantInfo(merchant_count=1, merchants=[])
        )
    ]
    market = MarketStats(products_analyzed=1, valid_prices_count=1, valid_ratings_count=0)
    insights = generate_market_insights(products, market)
    
    assert not any("offered by multiple observed merchants" in insight for insight in insights)
