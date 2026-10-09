import pytest
from app.schemas.intelligence import EnhancedProduct, MarketStats, SearchIntent
from app.intelligence.deal_analysis import analyze_deal


def test_valid_discount_calculation():
    product = EnhancedProduct(
        product_id="test-1",
        title="Sample Product",
        extracted_price=1000.0,
        extracted_old_price=1500.0,
    )
    market = MarketStats(
        products_analyzed=5,
        valid_prices_count=5,
        valid_ratings_count=5,
        median_price=1200.0,
    )
    intent = SearchIntent(product_query="sample")

    deal = analyze_deal(product, market, intent)
    assert deal.discount_pct == 33.3
    # 33.3% discount and below median (1000 < 1200) -> strong
    assert deal.deal_quality == "strong"


def test_old_price_equal_to_current_price_no_discount():
    product = EnhancedProduct(
        product_id="test-2",
        title="Sample Product",
        extracted_price=1000.0,
        extracted_old_price=1000.0,
    )
    market = MarketStats(
        products_analyzed=5,
        valid_prices_count=5,
        valid_ratings_count=5,
        median_price=1200.0,
    )
    intent = SearchIntent(product_query="sample")

    deal = analyze_deal(product, market, intent)
    assert deal.discount_pct is None
    assert deal.deal_quality is None


def test_old_price_lower_than_current_price_no_discount():
    product = EnhancedProduct(
        product_id="test-3",
        title="Sample Product",
        extracted_price=1500.0,
        extracted_old_price=1000.0,
    )
    market = MarketStats(
        products_analyzed=5,
        valid_prices_count=5,
        valid_ratings_count=5,
        median_price=1200.0,
    )
    intent = SearchIntent(product_query="sample")

    deal = analyze_deal(product, market, intent)
    assert deal.discount_pct is None
    assert deal.deal_quality is None


def test_missing_prices_handled_safely():
    market = MarketStats(
        products_analyzed=5,
        valid_prices_count=5,
        valid_ratings_count=5,
        median_price=1200.0,
    )
    intent = SearchIntent(product_query="sample")

    # Both missing
    p1 = EnhancedProduct(product_id="p1", extracted_price=None, extracted_old_price=None)
    d1 = analyze_deal(p1, market, intent)
    assert d1.discount_pct is None
    assert d1.deal_quality is None

    # Current price missing
    p2 = EnhancedProduct(product_id="p2", extracted_price=None, extracted_old_price=1200.0)
    d2 = analyze_deal(p2, market, intent)
    assert d2.discount_pct is None

    # Old price missing
    p3 = EnhancedProduct(product_id="p3", extracted_price=1000.0, extracted_old_price=None)
    d3 = analyze_deal(p3, market, intent)
    assert d3.discount_pct is None


def test_deal_classifications():
    market = MarketStats(
        products_analyzed=10,
        valid_prices_count=10,
        valid_ratings_count=10,
        median_price=1500.0,
    )
    intent = SearchIntent(product_query="test")

    # 1. Strong: >= 20% discount AND below market median
    p_strong = EnhancedProduct(extracted_price=1000.0, extracted_old_price=1500.0)  # 33.3%, below 1500
    d_strong = analyze_deal(p_strong, market, intent)
    assert d_strong.deal_quality == "strong"

    # 2. Moderate: >= 10% discount but NOT below market median
    p_mod_above = EnhancedProduct(extracted_price=1600.0, extracted_old_price=2000.0)  # 20%, above 1500
    d_mod_above = analyze_deal(p_mod_above, market, intent)
    assert d_mod_above.deal_quality == "moderate"

    # 3. Moderate: < 10% discount but below market median
    p_mod_below = EnhancedProduct(extracted_price=1425.0, extracted_old_price=1500.0)  # 5%, below 1500
    d_mod_below = analyze_deal(p_mod_below, market, intent)
    assert d_mod_below.deal_quality == "moderate"

    # 4. Minimal: < 10% discount AND NOT below market median
    p_minimal = EnhancedProduct(extracted_price=1900.0, extracted_old_price=2000.0)  # 5%, above 1500
    d_minimal = analyze_deal(p_minimal, market, intent)
    assert d_minimal.deal_quality == "minimal"


def test_missing_market_median_handled_safely():
    market_no_median = MarketStats(
        products_analyzed=2,
        valid_prices_count=0,
        valid_ratings_count=0,
        median_price=None,
    )
    intent = SearchIntent(product_query="test")

    # discount >= 10 falls back to moderate when median is missing
    p1 = EnhancedProduct(extracted_price=900.0, extracted_old_price=1000.0)  # 10%
    d1 = analyze_deal(p1, market_no_median, intent)
    assert d1.discount_pct == 10.0
    assert d1.deal_quality == "moderate"

    # discount < 10 falls back to minimal when median is missing
    p2 = EnhancedProduct(extracted_price=950.0, extracted_old_price=1000.0)  # 5%
    d2 = analyze_deal(p2, market_no_median, intent)
    assert d2.discount_pct == 5.0
    assert d2.deal_quality == "minimal"


def test_budget_utilisation_and_headroom():
    market = MarketStats(products_analyzed=1, valid_prices_count=1, valid_ratings_count=1)
    intent = SearchIntent(product_query="phone", budget_max=2000.0)

    # Under budget
    p_under = EnhancedProduct(extracted_price=1500.0)
    d_under = analyze_deal(p_under, market, intent)
    assert d_under.budget_utilisation_pct == 75.0
    assert "₹500 under budget (25% remaining)" in d_under.budget_headroom

    # Exactly at budget
    p_exact = EnhancedProduct(extracted_price=2000.0)
    d_exact = analyze_deal(p_exact, market, intent)
    assert d_exact.budget_utilisation_pct == 100.0
    assert d_exact.budget_headroom == "Exactly at budget"


def test_missing_or_invalid_budget_handled_safely():
    market = MarketStats(products_analyzed=1, valid_prices_count=1, valid_ratings_count=1)

    p = EnhancedProduct(extracted_price=1000.0)

    # Missing budget
    d_no_budget = analyze_deal(p, market, SearchIntent(product_query="test", budget_max=None))
    assert d_no_budget.budget_utilisation_pct is None
    assert d_no_budget.budget_headroom is None

    # Zero budget
    d_zero_budget = analyze_deal(p, market, SearchIntent(product_query="test", budget_max=0.0))
    assert d_zero_budget.budget_utilisation_pct is None
    assert d_zero_budget.budget_headroom is None

    # Missing product price with valid budget
    p_no_price = EnhancedProduct(extracted_price=None)
    d_no_price = analyze_deal(p_no_price, market, SearchIntent(product_query="test", budget_max=2000.0))
    assert d_no_price.budget_utilisation_pct is None
    assert d_no_price.budget_headroom is None


def test_prices_above_budget_reported_correctly():
    market = MarketStats(products_analyzed=1, valid_prices_count=1, valid_ratings_count=1)
    intent = SearchIntent(product_query="laptop", budget_max=50000.0)

    p_over = EnhancedProduct(extracted_price=65000.0)
    d_over = analyze_deal(p_over, market, intent)
    assert d_over.budget_utilisation_pct == 130.0
    assert d_over.budget_headroom == "₹15,000 over budget"


def test_deal_analysis_does_not_claim_unverified_genuineness():
    # Documentation and field naming must reflect observed merchant data, not unverified claims
    from app.intelligence.deal_analysis import analyze_deal as fn
    doc = fn.__doc__
    assert "NOT a guarantee" in doc
    assert "genuine" in doc
    assert "observed" in doc
