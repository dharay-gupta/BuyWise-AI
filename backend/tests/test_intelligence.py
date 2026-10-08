import pytest
from app.intelligence.intent_parser import parse_intent
from app.schemas.intelligence import EnhancedProduct
from app.intelligence.market_analysis import analyze_market
from app.intelligence.scoring import score_product
from app.intelligence.recommendations import generate_recommendations

def test_intent_budget_extraction():
    intents = [
        ("wireless headphones under ₹5000", 5000.0, "balanced"),
        ("laptops below 80000", 80000.0, "balanced"),
        ("cheap gaming mouse under 2k", 2000.0, "cheap"),
        ("best phone under 30k", 30000.0, "highest_rated"),
        ("laptop between 50000 and 80000", 80000.0, "balanced"),  # Max budget is 80k
        ("premium headphones", None, "premium"),
        ("best value laptop", None, "best_value")
    ]
    for query, expected_max, expected_prio in intents:
        i = parse_intent(query)
        assert i.budget_max == expected_max
        assert i.priority == expected_prio

def test_market_analysis():
    products = [
        EnhancedProduct(extracted_price=100.0, rating=4.0),
        EnhancedProduct(extracted_price=200.0, rating=5.0),
        EnhancedProduct(extracted_price=300.0, rating=None),
        EnhancedProduct(extracted_price=None, rating=3.0)
    ]
    market = analyze_market(products)
    assert market.products_analyzed == 4
    assert market.valid_prices_count == 3
    assert market.valid_ratings_count == 3
    assert market.lowest_price == 100.0
    assert market.highest_price == 300.0
    assert market.average_price == 200.0
    assert market.median_price == 200.0

def test_scoring_logic():
    intent = parse_intent("headphones")
    market = analyze_market([
        EnhancedProduct(extracted_price=1000.0),
        EnhancedProduct(extracted_price=5000.0)
    ])
    
    p = EnhancedProduct(extracted_price=1000.0, rating=5.0, reviews=10000)
    scored_p = score_product(p, market, intent)
    assert scored_p.buywise_score is not None
    assert scored_p.buywise_score > 0
    assert scored_p.price_percentile == 0.0
    
    p_high = EnhancedProduct(extracted_price=5000.0, rating=3.0, reviews=1)
    scored_high = score_product(p_high, market, intent)
    assert scored_high.buywise_score < scored_p.buywise_score
    assert scored_high.price_percentile == 100.0

def test_recommendations_and_tradeoffs():
    market = analyze_market([
        EnhancedProduct(extracted_price=1000.0),
        EnhancedProduct(extracted_price=5000.0)
    ])
    
    p1 = EnhancedProduct(product_id="1", title="Cheap Pick", extracted_price=1000.0, rating=4.0, reviews=500, buywise_score=85.0)
    p2 = EnhancedProduct(product_id="2", title="Best Pick", extracted_price=2500.0, rating=4.8, reviews=5000, buywise_score=95.0)
    p3 = EnhancedProduct(product_id="3", title="Hidden", extracted_price=2000.0, rating=4.5, reviews=20, buywise_score=80.0)
    
    recs = generate_recommendations([p1, p2, p3], market)
    assert recs.best_overall is not None
    assert recs.best_overall.product_id == "2"
    assert recs.cheapest is not None
    assert recs.cheapest.product_id == "1"
    assert recs.hidden_gem is not None
    assert recs.hidden_gem.product_id == "3"

def test_missing_values_graceful_handling():
    market = analyze_market([])
    p = EnhancedProduct(title="No Info")
    intent = parse_intent("query")
    scored = score_product(p, market, intent)
    assert scored.buywise_score is None # Expecting None when no active weights can be calculated
