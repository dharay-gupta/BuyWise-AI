"""
Recommendation Engine — Phase 6.4 (Feature C + D)

Deterministically selects one product per recommendation card.

Selection order (deliberate):
  1. Cheapest       — only requires a valid price
  2. Best Overall   — highest BuyWise score with quality evidence (runs before
                      Highest Rated so the strongest product wins the top card)
  3. Highest Rated  — rating * review_confidence (evidence-weighted)
  4. Best Value     — best score below market median
  5. Premium Pick   — best score above median, rating >= 4.0
  6. Hidden Gem     — rated >= 4.0 with 1-49 reviews

Key principles in Phase 6.4:
- Duplicate-identity detection: the same listing is excluded from a second
  card when a meaningful alternative exists.
- A product may legitimately win multiple cards when there is no valid
  alternative (and the reason explains this).
- Highest Rated: rating weighted by review confidence (a 5.0/1 review does
  not beat 4.7/500 reviews).
- Hidden Gem: rated >= 4.0, low-but-positive review count (1-49),
  explicitly notes limited review evidence.
- All selection logic is deterministic and unit-testable.
"""
from typing import List, Optional, Set
from app.schemas.intelligence import (
    EnhancedProduct,
    Recommendations,
    Recommendation,
    MarketStats,
    SearchIntent,
)
from app.intelligence.tradeoffs import generate_tradeoff, generate_hidden_gem_tradeoff


def _product_key(product: EnhancedProduct) -> str:
    """
    Returns the canonical identity string for a product.
    Uses product_id when available; falls back to title so that different
    variants with different titles are not considered identical.
    """
    if product.product_id:
        return f"pid:{product.product_id}"
    if product.title:
        return f"title:{product.title}"
    return f"obj:{id(product)}"


def _best_candidate(
    candidates: List[EnhancedProduct],
    key_func,
    reverse: bool,
    used_keys: Set[str],
    margin: float = 0.0,
) -> Optional[EnhancedProduct]:
    """
    Returns the best candidate not already in used_keys, or None.
    Sorts by key_func. To avoid forcing diversity with a poor alternative,
    a fresh candidate is only chosen if its key_func value is within
    'margin' of the absolute best candidate's value.
    """
    if not candidates:
        return None
    ranked = sorted(candidates, key=key_func, reverse=reverse)
    best_val = key_func(ranked[0])

    # Prefer a fresh candidate if it's a meaningful alternative
    for candidate in ranked:
        if _product_key(candidate) not in used_keys:
            val = key_func(candidate)
            if reverse:
                is_meaningful = val >= best_val - margin
            else:
                is_meaningful = val <= best_val + margin

            if is_meaningful:
                return candidate

    # No meaningful fresh candidate: allow the best to repeat
    return ranked[0]


def generate_recommendations(
    products: List[EnhancedProduct],
    market: MarketStats,
    intent: Optional[SearchIntent] = None,
    detected_category: Optional[str] = None,
) -> Recommendations:
    """
    Deterministically selects one product per recommendation category.

    Categories:
        - Best Overall:    Highest BuyWise score with meaningful quality evidence.
        - Cheapest:        Lowest observed price.
        - Highest Rated:   Best rating * review_confidence (evidence-weighted).
        - Best Value:      Best BuyWise score among products below market median.
        - Premium Pick:    Best BuyWise score among above-median, high-rating products.
        - Hidden Gem:      High-rated (>=4.0) with very few reviews (1-49).

    Budget filtering (intent.budget_max) is applied when intent is provided.
    Missing price / rating / review data is handled safely throughout.
    Duplicate products are excluded from a second card when an alternative exists.
    """
    recs = Recommendations()

    # ------------------------------------------------------------------
    # 1. Budget Filtering
    # ------------------------------------------------------------------
    budget_max: Optional[float] = intent.budget_max if intent is not None else None

    if budget_max is not None:
        eligible_products = [
            p for p in products
            if p.extracted_price is not None and p.extracted_price <= budget_max
        ]
    else:
        eligible_products = [p for p in products if p.extracted_price is not None]

    if not eligible_products:
        return recs

    # ------------------------------------------------------------------
    # 2. Helper sub-lists
    # ------------------------------------------------------------------
    # Products that have a computed BuyWise score (None-safe)
    scored = [p for p in eligible_products if p.buywise_score is not None]

    # Products with a meaningful quality signal (score + rating + some review evidence).
    overall_candidates = [
        p for p in scored
        if p.rating is not None
        and (
            (p.review_confidence or 0.0) > 0.05
            or (p.reviews is not None and p.reviews > 0)
        )
    ]

    # Track assigned product keys to avoid the same listing filling multiple cards
    used_keys: Set[str] = set()

    # ------------------------------------------------------------------
    # 3. Cheapest — only requires a valid price
    # ------------------------------------------------------------------
    by_price = sorted(eligible_products, key=lambda x: x.extracted_price)  # type: ignore[arg-type]
    if by_price:
        cheapest = by_price[0]
        cheapest.recommendation_tags.append("💰 Cheapest")
        key = _product_key(cheapest)
        used_keys.add(key)
        recs.cheapest = Recommendation(
            category="Cheapest",
            product_id=cheapest.product_id or cheapest.title or "unknown",
            reason=(
                "Selected as the lowest-priced valid listing among "
                "the observed results."
            ),
        )

    # ------------------------------------------------------------------
    # 4. Best Overall — highest BuyWise score with meaningful quality evidence
    #    Runs BEFORE Highest Rated so the product with the highest composite
    #    score wins the most prominent recommendation card.
    # ------------------------------------------------------------------
    if overall_candidates:
        best_candidate = _best_candidate(
            overall_candidates,
            lambda x: x.buywise_score,  # type: ignore[arg-type]
            True,
            used_keys,
            margin=10.0,
        )
        if best_candidate is not None:
            best_candidate.recommendation_tags.append("🏆 Best Overall")
            bkey = _product_key(best_candidate)
            was_duplicate = bkey in used_keys
            used_keys.add(bkey)
            if was_duplicate:
                reason = (
                    "Strong overall balance of price competitiveness and quality "
                    "evidence. Also the lowest-priced listing — it genuinely "
                    "dominates across both dimensions in the observed results."
                )
            else:
                reason = (
                    "Strong overall balance of price competitiveness and quality "
                    "evidence among observed results."
                )
            recs.best_overall = Recommendation(
                category="Best Overall",
                product_id=best_candidate.product_id or best_candidate.title or "unknown",
                reason=reason,
            )

    # ------------------------------------------------------------------
    # 5. Highest Rated — rating weighted by review confidence
    #    A 5.0/1 review must not outrank a 4.7/500 review.
    #    Composite: rating * max(review_confidence, 0.01) — the floor of
    #    0.01 means a product with no reviews can score at most 0.05, well
    #    below any product with meaningful review evidence.
    # ------------------------------------------------------------------
    with_ratings = [p for p in scored if p.rating is not None and p.rating > 0]
    if with_ratings:
        def _rating_signal(p: EnhancedProduct) -> float:
            conf = p.review_confidence or 0.0
            # Give unreviewed products a minimal floor so they can appear
            # only when nothing else is available
            effective_conf = max(conf, 0.01)
            return (p.rating or 0.0) * effective_conf

        highest_candidate = _best_candidate(
            with_ratings, _rating_signal, True, used_keys, margin=0.5
        )
        if highest_candidate is not None:
            highest_candidate.recommendation_tags.append("⭐ Highest Rated")
            hkey = _product_key(highest_candidate)
            was_duplicate = hkey in used_keys
            used_keys.add(hkey)
            # Build reason reflecting actual evidence
            rev_count = highest_candidate.reviews or 0
            rating_val = highest_candidate.rating or 0.0
            if rev_count >= 100:
                reason = (
                    f"Ranks highly because of its {rating_val:.1f}\u2605 rating "
                    f"backed by {rev_count:,} observed reviews."
                )
            elif rev_count > 0:
                reason = (
                    f"Highest combined rating ({rating_val:.1f}\u2605) and review "
                    f"evidence signal, though review volume is limited "
                    f"({rev_count} reviews)."
                )
            else:
                reason = (
                    f"Highest observed rating ({rating_val:.1f}\u2605), but no "
                    "review count was observed — treat with caution."
                )
            if was_duplicate:
                reason += (
                    " Also selected for another category — no separate "
                    "higher-rated listing was available within budget."
                )
            recs.highest_rated = Recommendation(
                category="Highest Rated",
                product_id=highest_candidate.product_id or highest_candidate.title or "unknown",
                reason=reason,
            )

    # ------------------------------------------------------------------
    # 6. Best Value — best score among below-median products
    # ------------------------------------------------------------------
    if market.median_price and overall_candidates:
        value_candidates = [
            p for p in overall_candidates
            if p.extracted_price is not None and p.extracted_price < market.median_price
        ]
        if value_candidates:
            value_candidate = _best_candidate(
                value_candidates,
                lambda x: x.buywise_score,  # type: ignore[arg-type]
                True,
                used_keys,
                margin=10.0,
            )
            if value_candidate is not None:
                vkey = _product_key(value_candidate)
                was_duplicate = vkey in used_keys
                if not was_duplicate:
                    value_candidate.recommendation_tags.append("🔥 Best Value")
                used_keys.add(vkey)
                recs.best_value = Recommendation(
                    category="Best Value",
                    product_id=value_candidate.product_id or value_candidate.title or "unknown",
                    reason=(
                        "Offers a balance of price and available review evidence "
                        "while priced below the observed market median."
                    ),
                )

    # ------------------------------------------------------------------
    # 7. Premium Pick — above-median price, rating >= 4.0
    # ------------------------------------------------------------------
    if market.median_price and overall_candidates:
        premium_candidates = [
            p for p in overall_candidates
            if (
                p.extracted_price is not None
                and p.extracted_price > market.median_price
                and (p.rating or 0.0) >= 4.0
            )
        ]
        if premium_candidates:
            premium_candidate = _best_candidate(
                premium_candidates,
                lambda x: x.buywise_score,  # type: ignore[arg-type]
                True,
                used_keys,
                margin=10.0,
            )
            if premium_candidate is not None:
                pkey = _product_key(premium_candidate)
                was_duplicate = pkey in used_keys
                if not was_duplicate:
                    premium_candidate.recommendation_tags.append("👑 Premium Pick")
                used_keys.add(pkey)
                recs.premium_pick = Recommendation(
                    category="Premium Pick",
                    product_id=premium_candidate.product_id or premium_candidate.title or "unknown",
                    reason=(
                        "Costs more than the observed market median but provides "
                        "strong rating and review signals."
                    ),
                )

    # ------------------------------------------------------------------
    # 8. Hidden Gem — rated >= 4.0 but very few reviews (1-49)
    #    Explicitly notes limited review evidence in the reason.
    # ------------------------------------------------------------------
    hidden_candidates = [
        p for p in scored
        if (
            p.rating is not None
            and p.rating >= 4.0
            and 0 < (p.reviews or 0) < 50
        )
    ]
    if hidden_candidates:
        gem_candidate = _best_candidate(
            hidden_candidates,
            lambda x: x.buywise_score,  # type: ignore[arg-type]
            True,
            used_keys,
            margin=10.0,
        )
        if gem_candidate is not None:
            gkey = _product_key(gem_candidate)
            was_duplicate = gkey in used_keys
            if not was_duplicate:
                gem_candidate.recommendation_tags.append("💎 Hidden Gem")
            reviews_count = gem_candidate.reviews or 0
            rating_val = gem_candidate.rating or 0.0
            used_keys.add(gkey)
            recs.hidden_gem = Recommendation(
                category="Hidden Gem",
                product_id=gem_candidate.product_id or gem_candidate.title or "unknown",
                reason=(
                    "Selected as an alternative because it provides a "
                    "different price-quality trade-off: a {:.1f}\u2605 rating "
                    "with only {:d} observed reviews. "
                    "Review evidence is limited — the rating may not yet "
                    "reflect a large user base.".format(rating_val, reviews_count)
                ),
            )

    return recs
