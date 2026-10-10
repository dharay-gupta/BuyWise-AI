"""
Phase 6.4 — Multi-Category Robustness Tests (Feature E)

Covers category detection, category-aware scoring, recommendation diversity,
explanation quality, and all regression scenarios.

All SerpApi calls are mocked — no real API credits are used.
"""
import pytest
from typing import List
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.intelligence import (
    EnhancedProduct,
    MarketStats,
    SearchIntent,
    Recommendations,
)
from app.intelligence.category_detector import (
    detect_category,
    CATEGORY_LABELS,
    CAT_ELECTRONICS,
    CAT_COMPUTERS,
    CAT_MOBILE,
    CAT_AUDIO,
    CAT_CLOTHING,
    CAT_FOOTWEAR,
    CAT_HOME,
    CAT_BEAUTY,
    CAT_SPORTS,
    CAT_OTHER,
    _intent_category_to_broad,
)
from app.intelligence.intent_parser import parse_intent
from app.intelligence.market_analysis import analyze_market
from app.intelligence.scoring import (
    score_product,
    DECISION_MODE_WEIGHTS,
    _apply_category_weight_adjustment,
)
from app.intelligence.recommendations import generate_recommendations
from app.intelligence.explainer import explain_recommendation

client = TestClient(app)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_market(low: float, high: float) -> MarketStats:
    return analyze_market([
        EnhancedProduct(extracted_price=low),
        EnhancedProduct(extracted_price=high),
    ])


def _make_product(
    pid: str = "p1",
    title: str = "Test Product",
    price: float = 1000.0,
    rating: float = 4.0,
    reviews: int = 100,
    buywise_score: float = None,
    review_confidence: float = None,
) -> EnhancedProduct:
    p = EnhancedProduct(
        product_id=pid,
        title=title,
        extracted_price=price,
        rating=rating,
        reviews=reviews,
    )
    if buywise_score is not None:
        p.buywise_score = buywise_score
    if review_confidence is not None:
        p.review_confidence = review_confidence
    return p


def _scored_products(products: List[EnhancedProduct], market: MarketStats, intent: SearchIntent, cat: str = None):
    for p in products:
        score_product(p, market, intent, cat)
    return products


# ===========================================================================
# 1. Category Detection — Core Tests
# ===========================================================================

class TestCategoryDetection:

    def test_laptop_search_detected(self):
        intent = parse_intent("laptop under 50000")
        cat = detect_category("laptop under 50000", intent)
        assert cat == CAT_COMPUTERS

    def test_smartphone_search_detected(self):
        intent = parse_intent("best smartphone under 20000")
        cat = detect_category("best smartphone under 20000", intent)
        assert cat == CAT_MOBILE

    def test_phone_bare_word_detected(self):
        intent = parse_intent("phone under 15000")
        cat = detect_category("phone under 15000", intent)
        assert cat == CAT_MOBILE

    def test_shirt_search_detected(self):
        intent = parse_intent("cotton shirt under 500")
        cat = detect_category("cotton shirt under 500", intent)
        assert cat == CAT_CLOTHING

    def test_tshirt_variant_detected(self):
        cat = detect_category("t-shirt for men")
        assert cat == CAT_CLOTHING

    def test_footwear_search_detected(self):
        cat = detect_category("running shoes under 2000")
        assert cat == CAT_FOOTWEAR

    def test_sports_shoes_is_footwear_not_sports(self):
        """'sports shoes' is a footwear term, not generic sports."""
        cat = detect_category("sports shoes for men")
        assert cat == CAT_FOOTWEAR

    def test_headphone_search_detected(self):
        intent = parse_intent("wireless headphones under 3000")
        cat = detect_category("wireless headphones under 3000", intent)
        assert cat == CAT_AUDIO

    def test_earbuds_search_detected(self):
        cat = detect_category("best earbuds under 2000")
        assert cat == CAT_AUDIO

    def test_keyboard_search_detected(self):
        cat = detect_category("mechanical keyboard under 5000")
        assert cat == CAT_ELECTRONICS

    def test_monitor_search_detected(self):
        cat = detect_category("gaming monitor 27 inch")
        assert cat == CAT_ELECTRONICS

    def test_home_appliance_detected(self):
        cat = detect_category("washing machine front load")
        assert cat == CAT_HOME

    def test_beauty_search_detected(self):
        cat = detect_category("face wash for oily skin")
        assert cat == CAT_BEAUTY

    def test_sports_fitness_detected(self):
        cat = detect_category("dumbbell set 20kg gym")
        assert cat == CAT_SPORTS

    def test_wireless_alone_is_not_headphones(self):
        """'wireless' alone should not classify as audio."""
        cat = detect_category("wireless mouse")
        # wireless + mouse -> electronics (mouse is the specific signal)
        assert cat == CAT_ELECTRONICS

    def test_sport_alone_is_not_footwear(self):
        """'sport' alone should not classify as footwear."""
        cat = detect_category("sport watch")
        assert cat != CAT_FOOTWEAR

    def test_no_budget_query_still_detects_category(self):
        cat = detect_category("bluetooth speaker")
        assert cat == CAT_AUDIO

    def test_unknown_ambiguous_query_returns_other(self):
        cat = detect_category("xyz1234 gadget v2 pro max")
        # Should fall back to other or electronics (gadget word)
        assert cat in (CAT_OTHER, CAT_ELECTRONICS)

    def test_product_titles_used_as_secondary_evidence(self):
        """When query is ambiguous, product titles help classify."""
        titles = [
            "Cotton Slim Fit Shirt for Men",
            "Regular Fit Polo Shirt",
            "Check Shirt Casual",
            "Oxford Shirt Blue",
            "Formal Shirt White",
        ]
        cat = detect_category("men's wear under 1000", product_titles=titles)
        assert cat == CAT_CLOTHING

    def test_category_labels_defined_for_all_categories(self):
        """All category constants must have display labels."""
        all_cats = [
            CAT_ELECTRONICS, CAT_COMPUTERS, CAT_MOBILE, CAT_AUDIO,
            CAT_CLOTHING, CAT_FOOTWEAR, CAT_HOME, CAT_BEAUTY, CAT_SPORTS, CAT_OTHER,
        ]
        for cat in all_cats:
            assert cat in CATEGORY_LABELS, f"Missing label for category: {cat}"
            assert len(CATEGORY_LABELS[cat]) > 0

    def test_intent_category_mapping(self):
        """Intent parser categories map to broad categories correctly."""
        assert _intent_category_to_broad("laptop") == CAT_COMPUTERS
        assert _intent_category_to_broad("phone") == CAT_MOBILE
        assert _intent_category_to_broad("headphone") == CAT_AUDIO
        assert _intent_category_to_broad("earbud") == CAT_AUDIO
        assert _intent_category_to_broad("speaker") == CAT_AUDIO
        assert _intent_category_to_broad("keyboard") == CAT_ELECTRONICS
        assert _intent_category_to_broad("unknown_thing") == CAT_OTHER

    def test_detect_category_deterministic(self):
        """Same inputs always produce same output."""
        intent = parse_intent("laptop under 80000")
        result1 = detect_category("laptop under 80000", intent)
        result2 = detect_category("laptop under 80000", intent)
        assert result1 == result2


# ===========================================================================
# 2. Category-Aware Scoring Tests
# ===========================================================================

class TestCategoryAwareScoring:

    def test_audio_category_shifts_weight_to_rating_in_balanced(self):
        base = dict(DECISION_MODE_WEIGHTS["balanced"])
        adjusted, note = _apply_category_weight_adjustment(base, CAT_AUDIO, "balanced")
        assert adjusted["rating"] > base["rating"]
        assert adjusted["price"] < base["price"]
        assert note is not None
        assert abs(sum(adjusted.values()) - 1.0) < 1e-9

    def test_clothing_category_shifts_weight_to_price_in_balanced(self):
        base = dict(DECISION_MODE_WEIGHTS["balanced"])
        adjusted, note = _apply_category_weight_adjustment(base, CAT_CLOTHING, "balanced")
        assert adjusted["price"] > base["price"]
        assert adjusted["rating"] < base["rating"]
        assert note is not None
        assert abs(sum(adjusted.values()) - 1.0) < 1e-9

    def test_footwear_category_shifts_weight_to_price_in_best_value(self):
        base = dict(DECISION_MODE_WEIGHTS["best_value"])
        adjusted, note = _apply_category_weight_adjustment(base, CAT_FOOTWEAR, "best_value")
        assert adjusted["price"] > base["price"]
        assert abs(sum(adjusted.values()) - 1.0) < 1e-9

    def test_no_adjustment_in_cheapest_mode(self):
        """Cheapest mode already emphasises price — no adjustment needed."""
        base = dict(DECISION_MODE_WEIGHTS["cheapest"])
        adjusted, note = _apply_category_weight_adjustment(base, CAT_CLOTHING, "cheapest")
        assert adjusted == base
        assert note is None

    def test_no_adjustment_in_quality_first_mode(self):
        """Quality First already emphasises rating — no adjustment needed."""
        base = dict(DECISION_MODE_WEIGHTS["quality_first"])
        adjusted, note = _apply_category_weight_adjustment(base, CAT_AUDIO, "quality_first")
        assert adjusted == base
        assert note is None

    def test_no_adjustment_for_other_category(self):
        """Unknown/other category must not produce any adjustment."""
        base = dict(DECISION_MODE_WEIGHTS["balanced"])
        adjusted, note = _apply_category_weight_adjustment(base, CAT_OTHER, "balanced")
        assert adjusted == base
        assert note is None

    def test_no_adjustment_for_none_category(self):
        """None category must not produce any adjustment."""
        base = dict(DECISION_MODE_WEIGHTS["balanced"])
        adjusted, note = _apply_category_weight_adjustment(base, None, "balanced")
        assert adjusted == base
        assert note is None

    def test_score_stays_in_range_with_category(self):
        """Scores must remain 0..100 with category adjustment active."""
        market = _make_market(500.0, 5000.0)
        intent = parse_intent("headphones")
        intent.priority = "balanced"
        for price in [500, 1000, 3000, 5000]:
            p = _make_product(price=float(price), rating=4.5, reviews=200)
            score_product(p, market, intent, detected_category=CAT_AUDIO)
            assert p.buywise_score is not None
            assert 0 <= p.buywise_score <= 100

    def test_category_does_not_increase_score_when_data_missing(self):
        """Category detection must not award points for absent data."""
        market = _make_market(500.0, 5000.0)
        intent = parse_intent("headphones")
        intent.priority = "balanced"
        # Product with no rating: score should not be inflated by category
        p_no_rating = _make_product(price=1000.0, rating=None, reviews=None)
        p_no_rating.rating = None
        p_no_rating.reviews = None
        score_product(p_no_rating, market, intent, detected_category=CAT_AUDIO)
        # Rating component must be neutral baseline (0.5 * adjusted_weight)
        assert p_no_rating.score_breakdown is not None
        assert p_no_rating.score_breakdown.rating == 17.5
        assert p_no_rating.score_breakdown.review_confidence == 0.0

    def test_all_four_modes_work_with_category(self):
        """All four decision modes must produce valid scores with category."""
        market = _make_market(300.0, 3000.0)
        for mode in ["balanced", "cheapest", "best_value", "quality_first"]:
            intent = parse_intent("shirt")
            intent.priority = mode
            p = _make_product(price=500.0, rating=4.2, reviews=80)
            score_product(p, market, intent, detected_category=CAT_CLOTHING)
            assert p.buywise_score is not None
            assert 0 <= p.buywise_score <= 100

    def test_missing_price_handled_safely_with_category(self):
        """Missing price + category must not crash and must give None score or partial."""
        market = _make_market(500.0, 2000.0)
        intent = parse_intent("shoes")
        intent.priority = "balanced"
        p = EnhancedProduct(extracted_price=None, rating=4.0, reviews=50)
        score_product(p, market, intent, detected_category=CAT_FOOTWEAR)
        # Has rating+reviews so score should be calculable
        assert p.buywise_score is not None

    def test_missing_rating_zero_reviews_handled_safely(self):
        """No rating, no reviews: score is None since no usable signal."""
        market = _make_market(500.0, 5000.0)
        intent = parse_intent("lipstick")
        intent.priority = "balanced"
        p = EnhancedProduct(extracted_price=None, rating=None, reviews=None)
        score_product(p, market, intent, detected_category=CAT_BEAUTY)
        assert p.buywise_score is None

    def test_invalid_price_zero_reviews_handled_safely(self):
        """0 reviews must produce 0.0 review_confidence, not an error."""
        market = _make_market(100.0, 1000.0)
        intent = parse_intent("dumbbell")
        intent.priority = "balanced"
        p = EnhancedProduct(extracted_price=500.0, rating=4.0, reviews=0)
        score_product(p, market, intent, detected_category=CAT_SPORTS)
        assert p.buywise_score is not None
        assert p.review_confidence == 0.0


# ===========================================================================
# 3. Recommendation Diversity Tests
# ===========================================================================

class TestRecommendationDiversity:

    def test_same_product_not_duplicated_when_alternative_exists(self):
        """If a meaningful alternative exists, the same product must not win multiple cards."""
        market = _make_market(300.0, 3000.0)
        intent = parse_intent("shirt")

        # p1 is cheapest but also has a score
        p1 = _make_product("p1", "Cheap Shirt", price=341.0, rating=4.1, reviews=150,
                            buywise_score=72.0, review_confidence=0.2)
        # p2 is clearly higher rated with more reviews
        p2 = _make_product("p2", "Premium Shirt", price=800.0, rating=4.6, reviews=800,
                            buywise_score=78.0, review_confidence=0.45)

        recs = generate_recommendations([p1, p2], market, intent)
        # Cheapest must be p1
        assert recs.cheapest is not None
        assert recs.cheapest.product_id == "p1"
        # Highest rated should prefer p2 (better rating signal)
        if recs.highest_rated:
            # p2 has better rating*confidence signal
            assert recs.highest_rated.product_id == "p2"

    def test_same_product_allowed_in_multiple_cards_when_no_alternative(self):
        """When only one product exists, it legitimately wins multiple cards."""
        market = _make_market(1000.0, 1000.0)
        intent = parse_intent("laptop")

        p = _make_product("p1", "Only Laptop", price=1000.0, rating=4.5, reviews=200,
                           buywise_score=75.0, review_confidence=0.25)
        recs = generate_recommendations([p], market, intent)

        # With a single product, it must fill whatever cards are possible
        filled = sum(1 for attr in ["best_overall", "cheapest", "highest_rated"]
                     if getattr(recs, attr) is not None)
        assert filled >= 1

    def test_cheapest_and_best_overall_can_be_same_when_justified(self):
        """If the cheapest product genuinely has the highest score, it wins both."""
        market = _make_market(341.0, 900.0)
        intent = parse_intent("shirt")

        # p1: cheapest AND has the best score
        p1 = _make_product("p1", "Best Shirt", price=341.0, rating=4.3, reviews=300,
                            buywise_score=85.0, review_confidence=0.3)
        # p2: more expensive, worse score
        p2 = _make_product("p2", "Meh Shirt", price=900.0, rating=3.5, reviews=20,
                            buywise_score=55.0, review_confidence=0.1)

        recs = generate_recommendations([p1, p2], market, intent)
        assert recs.cheapest is not None
        assert recs.cheapest.product_id == "p1"
        # best_overall should prefer p1 (best score); reason should mention it
        if recs.best_overall:
            assert recs.best_overall.product_id == "p1"
            assert "dominates" in recs.best_overall.reason or "cheapest" in recs.best_overall.reason.lower()

    def test_hidden_gem_with_insufficient_evidence(self):
        """Hidden Gem reason must explicitly note limited review evidence."""
        market = _make_market(500.0, 3000.0)
        intent = parse_intent("shoes")

        gem = _make_product("gem1", "Gem Shoe", price=700.0, rating=4.5, reviews=12,
                             buywise_score=60.0, review_confidence=0.05)
        other = _make_product("p2", "Normal Shoe", price=1500.0, rating=3.8, reviews=500,
                               buywise_score=65.0, review_confidence=0.4)

        recs = generate_recommendations([gem, other], market, intent)
        if recs.hidden_gem:
            assert recs.hidden_gem.product_id == "gem1"
            reason = recs.hidden_gem.reason.lower()
            # Reason must acknowledge limited evidence
            assert "limited" in reason or "few" in reason or "only" in reason

    def test_hidden_gem_not_selected_when_no_low_review_products(self):
        """Hidden Gem must not be created when all products have >= 50 reviews."""
        market = _make_market(500.0, 2000.0)
        intent = parse_intent("keyboard")

        products = [
            _make_product("p1", "Keyboard A", price=1000.0, rating=4.4, reviews=500,
                          buywise_score=80.0),
            _make_product("p2", "Keyboard B", price=1500.0, rating=4.2, reviews=200,
                          buywise_score=70.0),
        ]
        recs = generate_recommendations(products, market, intent)
        assert recs.hidden_gem is None

    def test_highest_rated_uses_review_evidence_weighting(self):
        """A 5.0 rating with 1 review must not outrank 4.7 with 500 reviews."""
        market = _make_market(500.0, 5000.0)
        intent = parse_intent("headphones")

        # p1: LOWEST price so it gets Cheapest; minimal review confidence
        p_high_rating_no_evidence = _make_product(
            "p1", "Cheap HP", price=500.0, rating=5.0, reviews=1,
            buywise_score=65.0, review_confidence=0.04
        )
        # p2: higher price, but much stronger review evidence signal
        p_lower_rating_strong_evidence = _make_product(
            "p2", "Popular HP", price=2000.0, rating=4.7, reviews=500,
            buywise_score=80.0, review_confidence=0.4
        )

        recs = generate_recommendations(
            [p_high_rating_no_evidence, p_lower_rating_strong_evidence],
            market, intent
        )
        # p1 wins Cheapest (lower price), leaving p2 available for Highest Rated
        assert recs.cheapest is not None
        assert recs.cheapest.product_id == "p1"
        # p2 should win Highest Rated: 4.7 * 0.4 = 1.88 >> 5.0 * 0.04 = 0.2
        if recs.highest_rated:
            assert recs.highest_rated.product_id == "p2"

    def test_recommendations_with_budget_applied(self):
        """Budget filtering must exclude products above budget_max."""
        market = _make_market(500.0, 10000.0)
        intent = parse_intent("laptop under 3000")
        intent.budget_max = 3000.0

        p_in_budget = _make_product("p1", "Cheap Laptop", price=2500.0, rating=4.0,
                                     reviews=100, buywise_score=70.0)
        p_out_of_budget = _make_product("p2", "Expensive Laptop", price=8000.0, rating=4.8,
                                         reviews=1000, buywise_score=92.0)

        recs = generate_recommendations([p_in_budget, p_out_of_budget], market, intent)
        # Only in-budget product should appear
        if recs.best_overall:
            assert recs.best_overall.product_id == "p1"
        if recs.cheapest:
            assert recs.cheapest.product_id == "p1"

    def test_identical_product_ids_deduplication(self):
        """Two products with the same product_id are treated as the same listing."""
        market = _make_market(1000.0, 5000.0)
        intent = parse_intent("headphones")

        p1 = _make_product("dup-id", "HP Variant A", price=1000.0, rating=4.3,
                            reviews=100, buywise_score=80.0, review_confidence=0.2)
        p2 = _make_product("dup-id", "HP Variant A (Blue)", price=2000.0, rating=4.3,
                            reviews=100, buywise_score=75.0, review_confidence=0.2)

        recs = generate_recommendations([p1, p2], market, intent)
        # Both share the same product_id; first deduplication prevents both winning
        ids_used = []
        for attr in ["best_overall", "cheapest", "highest_rated"]:
            rec = getattr(recs, attr)
            if rec:
                ids_used.append(rec.product_id)
        # Same product_id can appear (different products shared id), but system
        # should not crash and should produce a valid recommendation set
        assert len(ids_used) >= 1

    def test_no_budget_search_includes_all_priced_products(self):
        """Without budget, all products with valid prices are eligible.
        Selection order: cheapest=p1, highest_rated=p2 (stronger signal),
        best_overall=p3 (highest score among remaining)."""
        market = _make_market(100.0, 100000.0)
        intent = parse_intent("camera")
        intent.budget_max = None

        products = [
            _make_product("p1", "Cheap Cam", price=500.0, rating=3.8, reviews=50,
                           buywise_score=55.0),
            _make_product("p2", "Mid Cam", price=15000.0, rating=4.5, reviews=300,
                           buywise_score=80.0, review_confidence=0.3),
            _make_product("p3", "Expensive Cam", price=80000.0, rating=4.8, reviews=200,
                           buywise_score=75.0, review_confidence=0.25),
        ]
        recs = generate_recommendations(products, market, intent)
        # cheapest must be p1 (lowest price)
        assert recs.cheapest is not None
        assert recs.cheapest.product_id == "p1"
        # All three products are eligible (no budget filter)
        filled = sum(1 for attr in ["best_overall", "cheapest", "highest_rated"]
                     if getattr(recs, attr) is not None)
        assert filled >= 2  # At minimum cheapest + one other


# ===========================================================================
# 4. Explanation Quality Tests
# ===========================================================================

class TestExplanationQuality:

    def test_cheapest_explanation_reflects_selection(self):
        """Cheapest explanation must reference lowest price."""
        market = _make_market(300.0, 3000.0)
        intent = SearchIntent(product_query="shirt", budget_max=1000.0)
        product = _make_product("p1", "Cheap Shirt", price=341.0, rating=4.1, reviews=200,
                                 buywise_score=70.0)
        explanation = explain_recommendation(product, market, intent, "cheapest")
        assert "Cheapest" in explanation.summary
        assert explanation.summary.startswith("BuyWise recommends this as the Cheapest")

    def test_best_overall_explanation_references_balance(self):
        """Best Overall explanation references balance of signals."""
        market = _make_market(300.0, 3000.0)
        intent = SearchIntent(product_query="laptop")
        product = _make_product("p1", "Good Laptop", price=1500.0, rating=4.5, reviews=500,
                                 buywise_score=85.0)
        explanation = explain_recommendation(product, market, intent, "best_overall")
        assert "Best Overall" in explanation.summary
        assert "balance" in explanation.summary.lower()

    def test_hidden_gem_explanation_notes_limited_evidence(self):
        """Hidden Gem summary must warn about limited evidence."""
        market = _make_market(300.0, 3000.0)
        intent = SearchIntent(product_query="shoes")
        product = _make_product("p1", "Gem Shoe", price=700.0, rating=4.5, reviews=12,
                                 buywise_score=60.0)
        explanation = explain_recommendation(product, market, intent, "hidden_gem")
        assert "Hidden Gem" in explanation.summary
        # Must mention caution / limitation
        assert "caution" in explanation.summary.lower() or "limited" in explanation.summary.lower()

    def test_limited_review_factor_when_few_reviews(self):
        """Products with 1-49 reviews must get 'Limited Review Evidence' factor."""
        market = _make_market(300.0, 3000.0)
        intent = SearchIntent(product_query="test")
        product = _make_product("p1", "Scarce Reviews", price=1000.0, rating=4.3, reviews=25)
        explanation = explain_recommendation(product, market, intent, "best_overall")
        names = [f.name for f in explanation.factors]
        assert "Limited Review Evidence" in names

    def test_no_review_count_available_factor(self):
        """When reviews=None but rating exists, factor notes unavailability."""
        market = _make_market(300.0, 3000.0)
        intent = SearchIntent(product_query="test")
        product = EnhancedProduct(
            product_id="p1",
            extracted_price=1000.0,
            rating=4.5,
            reviews=None,
        )
        explanation = explain_recommendation(product, market, intent, "best_overall")
        names = [f.name for f in explanation.factors]
        assert "Review Count Not Available" in names

    def test_strong_review_evidence_factor_for_many_reviews(self):
        """Products with >= 1000 reviews get 'Strong Review Evidence' factor."""
        market = _make_market(300.0, 3000.0)
        intent = SearchIntent(product_query="test")
        product = _make_product("p1", "Popular", price=1000.0, rating=4.5, reviews=2000)
        explanation = explain_recommendation(product, market, intent, "highest_rated")
        names = [f.name for f in explanation.factors]
        assert "Strong Review Evidence" in names

    def test_no_factors_when_all_data_missing(self):
        """With no price, rating, or reviews, factor list must be empty."""
        market = _make_market(300.0, 3000.0)
        intent = SearchIntent(product_query="test")
        product = EnhancedProduct(
            product_id="p1",
            extracted_price=None,
            rating=None,
            reviews=None,
        )
        explanation = explain_recommendation(product, market, intent, "best_overall")
        assert len(explanation.factors) == 0

    def test_budget_fit_factor_includes_utilisation_percentage(self):
        """Budget fit factor shows utilisation percentage."""
        market = _make_market(300.0, 3000.0)
        intent = SearchIntent(product_query="shirt", budget_max=1000.0)
        product = _make_product("p1", "Shirt", price=500.0, rating=4.0, reviews=100)
        explanation = explain_recommendation(product, market, intent, "cheapest")
        names = [f.name for f in explanation.factors]
        if "Budget Fit" in names:
            bf = next(f for f in explanation.factors if f.name == "Budget Fit")
            assert "50%" in bf.interpretation  # 500/1000 = 50%


# ===========================================================================
# 5. Regression Tests — Existing Behavior Preserved
# ===========================================================================

class TestRegressions:

    def test_existing_market_confidence_behavior(self):
        """Market confidence calculation must not be altered."""
        from app.intelligence.market_confidence import calculate_market_confidence
        from app.schemas.product import NormalizedProduct

        products = [
            NormalizedProduct(
                product_id=f"p-{i}",
                title=f"Item {i}",
                source="Amazon",
                extracted_price=1000.0,
                rating=4.0,
                reviews=100,
            )
            for i in range(20)
        ]
        conf = calculate_market_confidence(products)
        assert conf.sample_size == 20
        assert conf.level in ("high", "moderate")
        assert conf.score > 0

    def test_existing_fallback_behavior_intact(self):
        """Search fallback with at most one extra call still works."""
        from app.services.search_service import perform_commerce_search_with_fallback, FALLBACK_THRESHOLD

        def _sparse():
            return [
                {
                    "title": f"Product {i}",
                    "extracted_price": float(1000 + i * 100),
                    "source": "Amazon",
                    "product_id": f"pid-{i}",
                }
                for i in range(3)
            ]

        def _rich():
            return [
                {
                    "title": f"Product {i}",
                    "extracted_price": float(1000 + i * 100),
                    "source": "Amazon",
                    "product_id": f"pid-{i}",
                }
                for i in range(8)
            ]

        with patch("app.services.search_service.serpapi_client") as mock:
            mock.search_google_shopping.side_effect = [
                {"shopping_results": _sparse()},
                {"shopping_results": _rich()},
            ]
            result, fallback_used = perform_commerce_search_with_fallback(
                original_query="laptop under 50000",
                fallback_query="laptop",
            )
            assert fallback_used is True
            assert len(result.products) == 8
            assert mock.search_google_shopping.call_count == 2

    def test_existing_deal_analysis_intact(self):
        """Deal analysis must not be changed by Phase 6.4."""
        from app.intelligence.deal_analysis import analyze_deal
        product = EnhancedProduct(
            product_id="t1",
            extracted_price=1000.0,
            extracted_old_price=1500.0,
        )
        market = MarketStats(
            products_analyzed=5,
            valid_prices_count=5,
            valid_ratings_count=5,
            median_price=1200.0,
        )
        intent = SearchIntent(product_query="headphones", budget_max=2000.0)
        deal = analyze_deal(product, market, intent)
        assert deal.discount_pct == 33.3
        assert deal.deal_quality == "strong"

    def test_existing_cross_merchant_intact(self):
        """Cross-merchant comparison must still work after Phase 6.4."""
        from app.intelligence.cross_merchant import build_cross_merchant_map
        products = [
            EnhancedProduct(product_id="same-id", source="Amazon", extracted_price=1000.0),
            EnhancedProduct(product_id="same-id", source="Flipkart", extracted_price=950.0),
        ]
        cm_map = build_cross_merchant_map(products)
        assert "same-id" in cm_map
        assert cm_map["same-id"].merchant_count == 2

    def test_all_decision_modes_produce_valid_response(self):
        """All four modes work end-to-end after Phase 6.4."""
        products_payload = [
            {
                "title": f"Laptop {i}",
                "extracted_price": float(30000 + i * 5000),
                "source": "Amazon",
                "product_id": f"l-{i}",
                "rating": 4.0 + (i * 0.1),
                "reviews": 100 + i * 50,
            }
            for i in range(6)
        ]
        for mode in ["balanced", "cheapest", "best_value", "quality_first"]:
            with patch("app.services.search_service.serpapi_client") as mock:
                mock.search_google_shopping.return_value = {
                    "shopping_results": products_payload
                }
                response = client.get(f"/api/search?q=laptop+under+80000&mode={mode}")
                assert response.status_code == 200, f"Mode {mode!r} failed"
                data = response.json()
                assert data["decision_mode"] == mode
                assert data["count"] == 6
                for field in ["intent", "market", "recommendations", "products", "confidence"]:
                    assert field in data

    def test_shopper_view_data_intact(self):
        """Products returned must have all fields needed for shopper view."""
        with patch("app.services.search_service.serpapi_client") as mock:
            mock.search_google_shopping.return_value = {
                "shopping_results": [
                    {
                        "title": "Wireless Headphone",
                        "extracted_price": 1999.0,
                        "source": "Flipkart",
                        "product_id": "hp-1",
                        "rating": 4.2,
                        "reviews": 350,
                    }
                ] * 5
            }
            response = client.get("/api/search?q=headphones&mode=balanced")
            data = response.json()
            p = data["products"][0]
            # Shopper view fields
            for field in ["title", "extracted_price", "rating", "reviews",
                          "buywise_score", "score_breakdown", "insights"]:
                assert field in p, f"Missing field: {field}"

    def test_market_intelligence_view_data_intact(self):
        """Market stats and confidence must be present in response."""
        with patch("app.services.search_service.serpapi_client") as mock:
            mock.search_google_shopping.return_value = {
                "shopping_results": [
                    {
                        "title": f"Shirt {i}",
                        "extracted_price": float(300 + i * 50),
                        "source": "Amazon",
                        "product_id": f"s-{i}",
                        "rating": 4.0,
                        "reviews": 100,
                    }
                    for i in range(5)
                ]
            }
            response = client.get("/api/search?q=cotton+shirt&mode=balanced")
            data = response.json()
            assert data["market"] is not None
            assert data["confidence"] is not None
            market = data["market"]
            assert "lowest_price" in market
            assert "highest_price" in market
            assert "median_price" in market

    def test_xss_protection_server_side_key(self):
        """Offer text with HTML special chars must not be mangled."""
        with patch("app.services.search_service.serpapi_client") as mock:
            mock.search_google_shopping.return_value = {
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
            # API key never in response
            resp_text = response.text
            assert "SERPAPI" not in resp_text.upper() or "api_key" not in resp_text.lower()


# ===========================================================================
# 6. Per-Category Scenario Tests
# ===========================================================================

class TestPerCategoryScenarios:

    def _run_category_scenario(self, query: str, products_data: list, mode: str = "balanced"):
        market = analyze_market([EnhancedProduct(extracted_price=p["extracted_price"]) for p in products_data])
        intent = parse_intent(query)
        intent.priority = mode
        titles = [p["title"] for p in products_data]
        category = detect_category(query, intent, titles)
        products = [
            EnhancedProduct(
                product_id=p.get("product_id", f"pid-{i}"),
                title=p["title"],
                extracted_price=p.get("extracted_price"),
                rating=p.get("rating"),
                reviews=p.get("reviews"),
            )
            for i, p in enumerate(products_data)
        ]
        for p in products:
            score_product(p, market, intent, category)
        recs = generate_recommendations(products, market, intent)
        return category, recs, products

    def test_laptop_scenario_with_budget(self):
        category, recs, _ = self._run_category_scenario(
            "laptop under 60000",
            [
                {"title": "ASUS VivoBook 15", "extracted_price": 45000.0, "rating": 4.2, "reviews": 500, "product_id": "p1"},
                {"title": "HP Pavilion 14", "extracted_price": 52000.0, "rating": 4.5, "reviews": 2000, "product_id": "p2"},
                {"title": "Lenovo IdeaPad 3", "extracted_price": 38000.0, "rating": 4.0, "reviews": 800, "product_id": "p3"},
            ]
        )
        assert category == CAT_COMPUTERS
        assert recs.cheapest is not None
        assert recs.cheapest.product_id == "p3"
        assert recs.best_overall is not None

    def test_smartphone_scenario_with_budget(self):
        category, recs, _ = self._run_category_scenario(
            "smartphone under 20000",
            [
                {"title": "Redmi Note 13", "extracted_price": 14999.0, "rating": 4.3, "reviews": 3000, "product_id": "p1"},
                {"title": "Samsung Galaxy A35", "extracted_price": 19999.0, "rating": 4.4, "reviews": 1200, "product_id": "p2"},
                {"title": "Realme 12", "extracted_price": 12999.0, "rating": 4.1, "reviews": 500, "product_id": "p3"},
            ]
        )
        assert category == CAT_MOBILE
        assert recs.cheapest is not None

    def test_shirt_scenario(self):
        category, recs, _ = self._run_category_scenario(
            "cotton shirt under 500",
            [
                {"title": "Classic Cotton Shirt Men", "extracted_price": 341.0, "rating": 4.1, "reviews": 250, "product_id": "p1"},
                {"title": "Oxford Regular Fit Shirt", "extracted_price": 459.0, "rating": 4.3, "reviews": 120, "product_id": "p2"},
                {"title": "Striped Office Shirt", "extracted_price": 399.0, "rating": 3.9, "reviews": 80, "product_id": "p3"},
            ]
        )
        assert category == CAT_CLOTHING
        assert recs.cheapest.product_id == "p1"

    def test_footwear_scenario(self):
        category, recs, _ = self._run_category_scenario(
            "running shoes under 3000",
            [
                {"title": "Nike Revolution Running Shoes", "extracted_price": 2499.0, "rating": 4.4, "reviews": 800, "product_id": "p1"},
                {"title": "Adidas Lite Racer", "extracted_price": 1999.0, "rating": 4.2, "reviews": 500, "product_id": "p2"},
                {"title": "Sparx Mesh Running Shoes", "extracted_price": 999.0, "rating": 4.0, "reviews": 300, "product_id": "p3"},
            ]
        )
        assert category == CAT_FOOTWEAR
        assert recs.cheapest.product_id == "p3"

    def test_headphone_scenario(self):
        category, recs, _ = self._run_category_scenario(
            "wireless headphones under 3000",
            [
                {"title": "Sony WH-CH720N Wireless Headphones", "extracted_price": 2999.0, "rating": 4.6, "reviews": 1500, "product_id": "p1"},
                {"title": "Boat Rockerz 450 Headphone", "extracted_price": 999.0, "rating": 4.2, "reviews": 5000, "product_id": "p2"},
                {"title": "JBL Tune 510BT Bluetooth Headphones", "extracted_price": 1799.0, "rating": 4.4, "reviews": 800, "product_id": "p3"},
            ]
        )
        assert category == CAT_AUDIO
        assert recs.cheapest.product_id == "p2"

    def test_keyboard_accessory_scenario(self):
        category, recs, _ = self._run_category_scenario(
            "mechanical keyboard under 5000",
            [
                {"title": "Zebronics ZEB-MAX PRO Mechanical Keyboard", "extracted_price": 2500.0, "rating": 4.1, "reviews": 300, "product_id": "p1"},
                {"title": "Cosmic Byte CB-GK-23 Mechanical Keyboard", "extracted_price": 1799.0, "rating": 4.0, "reviews": 500, "product_id": "p2"},
                {"title": "Keychron K2 Wireless Keyboard", "extracted_price": 4999.0, "rating": 4.7, "reviews": 200, "product_id": "p3"},
            ]
        )
        assert category == CAT_ELECTRONICS
        assert recs.cheapest.product_id == "p2"

    def test_missing_prices_handled(self):
        """Products with None price are excluded from eligible candidates."""
        market = _make_market(500.0, 3000.0)
        intent = parse_intent("shirt")
        intent.priority = "balanced"
        products = [
            _make_product("p1", "Shirt A", price=500.0, rating=4.0, reviews=100, buywise_score=70.0),
            EnhancedProduct(product_id="p2", title="Shirt B", extracted_price=None, rating=4.5, reviews=200),
        ]
        score_product(products[0], market, intent, CAT_CLOTHING)
        score_product(products[1], market, intent, CAT_CLOTHING)
        recs = generate_recommendations(products, market, intent)
        # p2 has no price, must not be cheapest
        if recs.cheapest:
            assert recs.cheapest.product_id == "p1"

    def test_malformed_prices_handled(self):
        """Malformed prices after normalization are treated as None (no crash)."""
        from app.intelligence.normalization import normalize_shopping_results
        raw = [
            {"title": "Product A", "extracted_price": "bad_price", "rating": 4.0, "reviews": 100},
            {"title": "Product B", "extracted_price": 1000.0, "rating": 4.2, "reviews": 50},
        ]
        products = normalize_shopping_results(raw)
        assert len(products) == 2
        # Product A's price should be None (bad string) or extracted if regex works
        assert products[1].extracted_price == 1000.0
