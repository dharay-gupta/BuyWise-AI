import math
from typing import Dict, Optional
from app.schemas.intelligence import ScoreBreakdown, EnhancedProduct, MarketStats, SearchIntent


# ---------------------------------------------------------------------------
# Decision Mode Weight Configuration
# Single location to configure all mode weights.
# All four weights in each mode must sum to 1.0.
# ---------------------------------------------------------------------------
DECISION_MODE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "balanced": {
        "price": 0.35,
        "rating": 0.30,
        "review_confidence": 0.15,
        "market_position": 0.20,
    },
    "cheapest": {
        "price": 0.60,
        "rating": 0.10,
        "review_confidence": 0.05,
        "market_position": 0.25,
    },
    "best_value": {
        "price": 0.40,
        "rating": 0.30,
        "review_confidence": 0.15,
        "market_position": 0.15,
    },
    "quality_first": {
        "price": 0.10,
        "rating": 0.45,
        "review_confidence": 0.30,
        "market_position": 0.15,
    },
    # Legacy priority aliases (Phase 3 backward compat)
    "cheap": {
        "price": 0.60,
        "rating": 0.15,
        "review_confidence": 0.10,
        "market_position": 0.15,
    },
    "premium": {
        "price": 0.10,
        "rating": 0.45,
        "review_confidence": 0.35,
        "market_position": 0.10,
    },
    "highest_rated": {
        "price": 0.20,
        "rating": 0.50,
        "review_confidence": 0.30,
        "market_position": 0.00,
    },
}

# Canonical display labels for each mode
DECISION_MODE_LABELS: Dict[str, str] = {
    "balanced": "Balanced",
    "cheapest": "Cheapest",
    "best_value": "Best Value",
    "quality_first": "Quality First",
    "cheap": "Budget",
    "premium": "Premium",
    "highest_rated": "Highest Rated",
}

# Allowed frontend-facing modes (validated in route)
ALLOWED_MODES = {"balanced", "cheapest", "best_value", "quality_first"}


def _calculate_review_confidence(reviews: Optional[int]) -> float:
    """
    Calculates review confidence between 0 and 1 using logarithmic diminishing returns.
    Assumes 10,000 reviews corresponds to ~1.0 confidence.
    Returns 0.0 for None or zero reviews.
    """
    if reviews is None or reviews == 0:
        return 0.0

    threshold = 10_000.0
    confidence = math.log(reviews + 1) / math.log(threshold + 1)
    return min(1.0, confidence)


def _get_base_weights(priority: str) -> Dict[str, float]:
    """
    Returns the scoring weights for the given mode/priority.
    Falls back to 'balanced' for unknown values.
    All four weights always sum to 1.0.
    """
    return DECISION_MODE_WEIGHTS.get(priority, DECISION_MODE_WEIGHTS["balanced"])


def score_product(
    product: EnhancedProduct,
    market: MarketStats,
    intent: SearchIntent,
) -> EnhancedProduct:
    """
    Calculates the deterministic BuyWise Score and populates ScoreBreakdown.

    Design rules:
    - Missing data gives 0 for that component — products without ratings or prices
      cannot score artificially high.
    - If *no* meaningful data is available at all (no price, no rating, no reviews),
      buywise_score is left as None so downstream code can distinguish "unscored"
      from "scored zero".
    - The final score is calculated exactly once and clamped to [0, 100].
    - price_percentile and review_confidence are populated on the product object.
    - ScoreBreakdown includes *_max fields so the UI can display "X / max".
    """
    weights = _get_base_weights(intent.priority)
    components: Dict[str, float] = {
        "price": 0.0,
        "rating": 0.0,
        "review_confidence": 0.0,
        "market_position": 0.0,
    }
    has_data = False  # track whether at least one meaningful signal exists

    # ------------------------------------------------------------------
    # 1. Price Competitiveness & Market Position
    # ------------------------------------------------------------------
    if (
        product.extracted_price is not None
        and market.highest_price is not None
        and market.lowest_price is not None
    ):
        has_data = True
        price_range = market.highest_price - market.lowest_price

        if price_range > 0:
            price_norm = 1.0 - (
                (product.extracted_price - market.lowest_price) / price_range
            )
            product.price_percentile = (
                (product.extracted_price - market.lowest_price) / price_range
            ) * 100
        else:
            price_norm = 0.5
            product.price_percentile = 50.0

        components["price"] = max(0.0, min(1.0, price_norm))

        if market.median_price and market.median_price > 0:
            pos = 1.0 - (product.extracted_price / (market.median_price * 2))
            components["market_position"] = max(0.0, min(1.0, pos))
        else:
            components["market_position"] = components["price"]

    # ------------------------------------------------------------------
    # 2. Rating Quality
    # ------------------------------------------------------------------
    if product.rating is not None:
        has_data = True
        components["rating"] = max(0.0, min(1.0, product.rating / 5.0))

    # ------------------------------------------------------------------
    # 3. Review Confidence
    # ------------------------------------------------------------------
    if product.reviews is not None:
        confidence = _calculate_review_confidence(product.reviews)
        components["review_confidence"] = confidence
        product.review_confidence = confidence
        if product.reviews > 0:
            has_data = True
    else:
        product.review_confidence = 0.0

    # ------------------------------------------------------------------
    # 4. Final BuyWise Score — computed exactly once
    # ------------------------------------------------------------------
    if not has_data:
        # No usable signals: leave score as None to distinguish from a scored 0
        return product

    final_score = 0.0
    breakdown = ScoreBreakdown(
        price_max=round(weights["price"] * 100, 1),
        rating_max=round(weights["rating"] * 100, 1),
        review_confidence_max=round(weights["review_confidence"] * 100, 1),
        market_position_max=round(weights["market_position"] * 100, 1),
    )

    for key, weight in weights.items():
        component_score = components[key] * 100.0
        weighted_val = component_score * weight
        final_score += weighted_val
        setattr(breakdown, key, round(weighted_val, 1))

    product.buywise_score = round(max(0.0, min(100.0, final_score)), 1)
    product.score_breakdown = breakdown

    return product
