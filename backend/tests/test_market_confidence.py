import pytest
from app.schemas.product import NormalizedProduct
from app.schemas.intelligence import EnhancedProduct, MarketStats
from app.intelligence.market_confidence import calculate_market_confidence


def test_complete_diverse_dataset():
    # 20 products, all priced, all rated and reviewed, across 4 merchants
    merchants = ["Amazon", "Flipkart", "Croma", "Reliance Digital"]
    products = [
        NormalizedProduct(
            product_id=f"p-{i}",
            title=f"Headphone {i}",
            source=merchants[i % len(merchants)],
            extracted_price=1500.0 + i * 50,
            rating=4.2 + (i % 5) * 0.1,
            reviews=100 + i * 20,
        )
        for i in range(20)
    ]

    conf = calculate_market_confidence(products)
    assert conf.sample_size == 20
    assert conf.price_coverage_pct == 100.0
    assert conf.rating_coverage_pct == 100.0
    assert conf.merchant_diversity_count == 4
    assert conf.score == 100.0
    assert conf.level == "high"
    assert any("Substantial observed sample" in r for r in conf.reasons)
    assert any("100% of observed listings include valid price data" in r for r in conf.reasons)
    assert any("Multi-store representation" in r for r in conf.reasons)


def test_fewer_than_five_products_strictly_limited():
    # Even if 4 products have 100% prices, ratings, and merchants, must be marked 'limited'
    products = [
        NormalizedProduct(
            product_id=f"p-{i}",
            title=f"Item {i}",
            source=f"Store {i}",
            extracted_price=1000.0,
            rating=4.5,
            reviews=500,
        )
        for i in range(4)
    ]

    conf = calculate_market_confidence(products)
    assert conf.sample_size == 4
    assert conf.level == "limited"
    assert any("Small observed sample size" in r for r in conf.reasons)


def test_missing_prices_reduces_score():
    # 10 products, but only 3 have valid positive prices
    products = [
        NormalizedProduct(
            product_id=f"p-{i}",
            title=f"Item {i}",
            source="Amazon",
            extracted_price=1000.0 if i < 3 else None,
            rating=4.0,
            reviews=50,
        )
        for i in range(10)
    ]

    conf = calculate_market_confidence(products)
    assert conf.sample_size == 10
    assert conf.price_coverage_pct == 30.0
    # Price score should be 30% of 25 = 7.5
    assert conf.level in ["moderate", "limited"]
    assert any("Only 30% of listings have prices (7 missing)" in r for r in conf.reasons)


def test_sparse_ratings_and_reviews_reduces_score():
    # 10 products, all with prices and merchants, but none have ratings or reviews
    products = [
        NormalizedProduct(
            product_id=f"p-{i}",
            title=f"Item {i}",
            source="Amazon",
            extracted_price=1000.0,
            rating=None,
            reviews=None,
        )
        for i in range(10)
    ]

    conf = calculate_market_confidence(products)
    assert conf.sample_size == 10
    assert conf.rating_coverage_pct == 0.0
    assert any("Sparse customer rating data" in r for r in conf.reasons)


def test_empty_dataset_handled_safely():
    conf = calculate_market_confidence([])
    assert conf.score == 0.0
    assert conf.level == "limited"
    assert conf.sample_size == 0
    assert conf.price_coverage_pct == 0.0
    assert conf.rating_coverage_pct == 0.0
    assert conf.merchant_diversity_count == 0
    assert "No observed products returned" in conf.reasons[0]


def test_missing_merchant_information():
    # 10 products, all priced and rated, but source is None or whitespace
    products = [
        NormalizedProduct(
            product_id=f"p-{i}",
            title=f"Item {i}",
            source=None if i % 2 == 0 else "   ",
            extracted_price=1000.0,
            rating=4.5,
            reviews=100,
        )
        for i in range(10)
    ]

    conf = calculate_market_confidence(products)
    assert conf.merchant_diversity_count == 0
    assert any("No merchant source attribution available" in r for r in conf.reasons)


def test_moderate_confidence_tier():
    # 8 products, all priced, 50% rated, across 2 merchants
    products = [
        NormalizedProduct(
            product_id=f"p-{i}",
            title=f"Item {i}",
            source="Amazon" if i < 4 else "Flipkart",
            extracted_price=2000.0,
            rating=4.0 if i < 4 else None,
            reviews=50 if i < 4 else None,
        )
        for i in range(8)
    ]

    conf = calculate_market_confidence(products)
    assert conf.sample_size == 8
    assert conf.level == "moderate"
    assert 45.0 <= conf.score < 75.0


def test_confidence_indicator_disclaimer_present():
    conf = calculate_market_confidence([])
    assert hasattr(conf, "disclaimer")
    assert "Reflects completeness and breadth" in conf.disclaimer
    assert "statistical guarantee" in conf.disclaimer
