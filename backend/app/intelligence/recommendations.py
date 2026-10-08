from typing import List, Optional
from app.schemas.intelligence import (
    EnhancedProduct,
    Recommendations,
    Recommendation,
    MarketStats,
    SearchIntent,
)
from app.intelligence.tradeoffs import generate_tradeoff, generate_hidden_gem_tradeoff


def generate_recommendations(
    products: List[EnhancedProduct],
    market: MarketStats,
    intent: Optional[SearchIntent] = None,
) -> Recommendations:
    """
    Deterministically selects one product per recommendation category.

    Categories:
        - Best Overall: Highest BuyWise score with meaningful quality evidence.
        - Cheapest:     Lowest observed price.
        - Highest Rated: Highest rating signal weighted by review confidence.
        - Best Value:   Best BuyWise score among products below the market median.
        - Premium Pick: Best BuyWise score among above-median, high-rating products.
        - Hidden Gem:   Highly-rated product with a very low review count.

    Budget filtering (intent.budget_max) is applied when intent is provided.
    Missing price / rating / review data is handled safely throughout.
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
    # Accept review_confidence > 0.05 (set by score_product pipeline) OR reviews > 0
    # (present on manually-constructed products that bypass score_product in tests).
    overall_candidates = [
        p for p in scored
        if p.rating is not None
        and (
            (p.review_confidence or 0.0) > 0.05
            or (p.reviews is not None and p.reviews > 0)
        )
    ]

    # ------------------------------------------------------------------
    # 3. Cheapest — only requires a valid price
    # ------------------------------------------------------------------
    by_price = sorted(eligible_products, key=lambda x: x.extracted_price)  # type: ignore[arg-type]
    if by_price:
        cheapest = by_price[0]
        cheapest.recommendation_tags.append("💰 Cheapest")
        recs.cheapest = Recommendation(
            category="Cheapest",
            product_id=cheapest.product_id or cheapest.title or "unknown",
            reason="Lowest observed price among products with valid price data.",
        )

    # ------------------------------------------------------------------
    # 4. Highest Rated — rating weighted by review confidence
    # ------------------------------------------------------------------
    with_ratings = [p for p in scored if p.rating is not None and p.rating > 0]
    if with_ratings:
        highest = sorted(
            with_ratings,
            key=lambda x: (x.rating or 0.0) * (x.review_confidence or 0.1),
            reverse=True,
        )[0]
        highest.recommendation_tags.append("⭐ Highest Rated")
        recs.highest_rated = Recommendation(
            category="Highest Rated",
            product_id=highest.product_id or highest.title or "unknown",
            reason="Highest-quality rating signal among products with sufficient review evidence.",
        )

    # ------------------------------------------------------------------
    # 5. Best Overall — highest BuyWise score with meaningful quality evidence
    # ------------------------------------------------------------------
    if overall_candidates:
        best = sorted(overall_candidates, key=lambda x: x.buywise_score, reverse=True)[0]  # type: ignore[arg-type]
        best.recommendation_tags.append("🏆 Best Overall")
        recs.best_overall = Recommendation(
            category="Best Overall",
            product_id=best.product_id or best.title or "unknown",
            reason="Strong overall balance of price competitiveness and quality evidence.",
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
            value = sorted(value_candidates, key=lambda x: x.buywise_score, reverse=True)[0]  # type: ignore[arg-type]
            if (
                "🏆 Best Overall" not in value.recommendation_tags
                and "💰 Cheapest" not in value.recommendation_tags
            ):
                value.recommendation_tags.append("🔥 Best Value")
                recs.best_value = Recommendation(
                    category="Best Value",
                    product_id=value.product_id or value.title or "unknown",
                    reason=(
                        "Strong balance of price, rating, and review evidence "
                        "relative to the observed market."
                    ),
                )

    # ------------------------------------------------------------------
    # 7. Premium Pick — above-median price, rating ≥ 4.0
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
            premium = sorted(premium_candidates, key=lambda x: x.buywise_score, reverse=True)[0]  # type: ignore[arg-type]
            if (
                "🏆 Best Overall" not in premium.recommendation_tags
                and "⭐ Highest Rated" not in premium.recommendation_tags
            ):
                premium.recommendation_tags.append("👑 Premium Pick")
                recs.premium_pick = Recommendation(
                    category="Premium Pick",
                    product_id=premium.product_id or premium.title or "unknown",
                    reason=(
                        "Costs more than the market median but provides "
                        "strong rating and review signals."
                    ),
                )

    # ------------------------------------------------------------------
    # 8. Hidden Gem — rated ≥ 4.0 but very few reviews (1–49)
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
        gem = sorted(hidden_candidates, key=lambda x: x.buywise_score, reverse=True)[0]  # type: ignore[arg-type]
        if (
            "🏆 Best Overall" not in gem.recommendation_tags
            and "💰 Cheapest" not in gem.recommendation_tags
        ):
            gem.recommendation_tags.append("💎 Hidden Gem")
            recs.hidden_gem = Recommendation(
                category="Hidden Gem",
                product_id=gem.product_id or gem.title or "unknown",
                reason="Strong value and quality signals despite limited review volume.",
            )

    return recs
