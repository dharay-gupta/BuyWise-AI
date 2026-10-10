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





# ---------------------------------------------------------------------------

# Category-aware weight adjustment (Phase 6.4 - Feature B)

# ---------------------------------------------------------------------------



# Categories where rating+review evidence is especially diagnostic.

# Adjustment: shift weight slightly toward rating quality.

_RATING_EMPHASIS_CATEGORIES = {

    "audio_accessories",      # rating matters greatly for headphones/speakers

    "beauty_personal_care",   # user-reported satisfaction is primary signal

    "sports_fitness",         # product quality highly reviewer-dependent

}



# Categories where price is especially salient for purchase decisions.

# Adjustment: shift weight slightly toward price / market_position.

_PRICE_EMPHASIS_CATEGORIES = {

    "clothing",   # price is a primary filter for most shoppers

    "footwear",   # competitive market; price is highly salient

}



# Adjustment magnitudes: deliberately conservative (<=0.05 each)

# so the category never dominates the chosen decision mode.

_RATING_SHIFT = 0.05    # move from price -> rating

_PRICE_SHIFT = 0.05     # move from rating -> price





def _apply_category_weight_adjustment(

    base_weights: Dict[str, float],

    detected_category: Optional[str],

    mode: str,

) -> tuple:

    """

    Returns an adjusted weight dict (copy) and a human-readable note explaining

    the adjustment.  Returns the original weights and None when no adjustment

    is applicable or desirable.



    Rules:

    - No adjustment in 'cheapest' mode (price already dominates).

    - No adjustment in 'quality_first' mode (rating already dominates).

    - Adjustments are capped so weights stay in (0, 1) and still sum to 1.0.

    - Missing data (detected_category is None or 'other') -> no adjustment.

    - The returned dict always sums to 1.0 within floating-point precision.

    """

    if detected_category is None or detected_category == "other":

        return base_weights, None

    if mode in ("cheapest", "quality_first"):

        # Those modes already emphasise the relevant dimension heavily.

        return base_weights, None



    weights = dict(base_weights)  # shallow copy - values are floats

    note = None



    if detected_category in _RATING_EMPHASIS_CATEGORIES:

        # Shift _RATING_SHIFT from price -> rating (clamped)

        shift = min(_RATING_SHIFT, weights["price"] - 0.01)

        if shift > 0:

            weights["price"] -= shift

            weights["rating"] += shift

            note = (

                "For {} searches, rating evidence receives a small additional "

                "weighting ({:.0f}pp transferred from price).".format(

                    detected_category.replace("_", " "), shift * 100

                )

            )



    elif detected_category in _PRICE_EMPHASIS_CATEGORIES:

        # Shift _PRICE_SHIFT from rating -> price (clamped)

        shift = min(_PRICE_SHIFT, weights["rating"] - 0.01)

        if shift > 0:

            weights["rating"] -= shift

            weights["price"] += shift

            note = (

                "For {} searches, price competitiveness receives a small "

                "additional weighting ({:.0f}pp transferred from rating).".format(

                    detected_category.replace("_", " "), shift * 100

                )

            )



    # Verify sum is still 1.0 (floating-point guard)

    total = sum(weights.values())

    if abs(total - 1.0) > 1e-9:

        # Rebalance the largest component to absorb any drift

        largest = max(weights, key=lambda k: weights[k])

        weights[largest] += 1.0 - total



    return weights, note





def score_product(

    product: EnhancedProduct,

    market: MarketStats,

    intent: SearchIntent,

    detected_category: Optional[str] = None,

) -> EnhancedProduct:

    """

    Calculates the deterministic BuyWise Score and populates ScoreBreakdown.



    Design rules:

    - Missing data gives 0 for that component - products without ratings or prices

      cannot score artificially high.

    - If *no* meaningful data is available at all (no price, no rating, no reviews),

      buywise_score is left as None so downstream code can distinguish "unscored"

      from "scored zero".

    - The final score is calculated exactly once and clamped to [0, 100].

    - price_percentile and review_confidence are populated on the product object.

    - ScoreBreakdown includes *_max fields so the UI can display "X / max".

    - Category-aware weight adjustment applied when detected_category is provided

      and falls into a known emphasis group (Phase 6.4).

    """

    base_weights = _get_base_weights(intent.priority)

    weights, _category_note = _apply_category_weight_adjustment(

        base_weights, detected_category, intent.priority

    )



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

    else:

        # Give unrated products a neutral 2.5/5 (0.5) baseline so they 

        # aren't unfairly penalised as an actual zero-star product.

        components["rating"] = 0.5



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

    # 4. Final BuyWise Score - computed exactly once

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

