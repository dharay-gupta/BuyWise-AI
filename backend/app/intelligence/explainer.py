"""
Recommendation Explainer — Phase 6.4 (Feature D)

Generates structured explanations for recommended products.

Rules:
- Only state conditions that are actually true for this product.
- When data is limited, explicitly mention the limitation.
- No generic text claiming superior specifications if none were observed.
- Concise and readable for display on recommendation cards and product modals.
"""
from app.schemas.intelligence import (
    EnhancedProduct,
    MarketStats,
    SearchIntent,
    ExplanationFactor,
    RecommendationExplanation,
)


def explain_recommendation(
    product: EnhancedProduct,
    market: MarketStats,
    intent: SearchIntent,
    recommendation_category: str,
) -> RecommendationExplanation:
    """
    Build a RecommendationExplanation for the given product and category.

    Only adds factors when the underlying condition is genuinely true.
    Data limitations are surfaced explicitly rather than omitted silently.
    """
    factors = []

    # ------------------------------------------------------------------
    # Price position
    # ------------------------------------------------------------------
    if product.extracted_price is not None and market.median_price is not None:
        if product.extracted_price < market.median_price:
            pct_below = round(
                (market.median_price - product.extracted_price) / market.median_price * 100
            )
            factors.append(ExplanationFactor(
                name="Price Advantage",
                observation=(
                    f"\u20b9{product.extracted_price:,.0f} is below the observed "
                    f"market median of \u20b9{market.median_price:,.0f}."
                ),
                interpretation=(
                    f"Offers savings ({pct_below}%) compared to typical prices "
                    "in the observed results."
                ),
                strength="strong" if pct_below >= 20 else "moderate",
            ))
        elif product.extracted_price > market.median_price:
            factors.append(ExplanationFactor(
                name="Premium Pricing",
                observation=(
                    f"\u20b9{product.extracted_price:,.0f} is above the observed "
                    f"market median of \u20b9{market.median_price:,.0f}."
                ),
                interpretation=(
                    "Priced higher than the typical observed result — "
                    "may reflect premium brand or features."
                ),
                strength="moderate",
            ))

    # ------------------------------------------------------------------
    # Rating signal
    # ------------------------------------------------------------------
    if product.rating is not None:
        if product.rating >= 4.5:
            factors.append(ExplanationFactor(
                name="Rating Strength",
                observation=f"Observed rating: {product.rating}/5.",
                interpretation="High average rating based on observed reviews.",
                strength="strong",
            ))
        elif product.rating >= 4.0:
            factors.append(ExplanationFactor(
                name="Solid Rating",
                observation=f"Observed rating: {product.rating}/5.",
                interpretation="Good average rating based on observed reviews.",
                strength="moderate",
            ))

    # ------------------------------------------------------------------
    # Budget fit
    # ------------------------------------------------------------------
    if intent.budget_max is not None and product.extracted_price is not None:
        if product.extracted_price <= intent.budget_max:
            utilisation_pct = round(
                (product.extracted_price / intent.budget_max) * 100
            )
            factors.append(ExplanationFactor(
                name="Budget Fit",
                observation=f"Priced at \u20b9{product.extracted_price:,.0f}.",
                interpretation=(
                    f"Fits within your stated \u20b9{intent.budget_max:,.0f} budget "
                    f"({utilisation_pct}% utilisation)."
                ),
                strength="strong",
            ))

    # ------------------------------------------------------------------
    # Review evidence (quality and limitations)
    # ------------------------------------------------------------------
    if product.reviews is not None:
        if product.reviews >= 1000:
            factors.append(ExplanationFactor(
                name="Strong Review Evidence",
                observation=f"Based on {product.reviews:,} observed reviews.",
                interpretation=(
                    "High confidence in the rating due to a large number "
                    "of observed reviews."
                ),
                strength="strong",
            ))
        elif product.reviews >= 50:
            factors.append(ExplanationFactor(
                name="Moderate Review Evidence",
                observation=f"Based on {product.reviews} observed reviews.",
                interpretation="Moderate review volume; confidence in rating is reasonable.",
                strength="moderate",
            ))
        elif product.reviews > 0:
            factors.append(ExplanationFactor(
                name="Limited Review Evidence",
                observation=(
                    f"The product has only {product.reviews} observed review(s)."
                ),
                interpretation=(
                    "Confidence in the rating is lower due to limited data. "
                    "The rating may change significantly as more users review it."
                ),
                strength="weak",
            ))
        else:
            factors.append(ExplanationFactor(
                name="No Review Count Observed",
                observation="No review count was available in the observed data.",
                interpretation=(
                    "Cannot assess rating reliability without review volume data."
                ),
                strength="weak",
            ))
    elif product.rating is not None:
        # Rating present but reviews field is absent from source data
        factors.append(ExplanationFactor(
            name="Review Count Not Available",
            observation="Review count was not included in the observed data.",
            interpretation=(
                "Cannot confirm the reliability of the rating without review "
                "volume information."
            ),
            strength="weak",
        ))

    # ------------------------------------------------------------------
    # BuyWise Score context
    # ------------------------------------------------------------------
    if product.buywise_score is not None:
        if product.buywise_score >= 80:
            factors.append(ExplanationFactor(
                name="Strong BuyWise Score",
                observation=f"BuyWise Score: {product.buywise_score:.1f}/100.",
                interpretation=(
                    "Demonstrates a strong balance of price, rating, and "
                    "market position based on observed data."
                ),
                strength="strong",
            ))
        elif product.buywise_score >= 60:
            factors.append(ExplanationFactor(
                name="Reasonable BuyWise Score",
                observation=f"BuyWise Score: {product.buywise_score:.1f}/100.",
                interpretation=(
                    "Moderate overall balance of the observed scoring signals."
                ),
                strength="moderate",
            ))

    # ------------------------------------------------------------------
    # Summary — per recommendation category
    # ------------------------------------------------------------------
    category_summaries = {
        "best_overall": (
            "BuyWise recommends this as Best Overall because it offers the "
            "strongest balance of price, rating, and review confidence among "
            "observed results."
        ),
        "best_value": (
            "BuyWise recommends this as Best Value because its observed price "
            "is below the market median while maintaining a solid rating and "
            "review evidence."
        ),
        "cheapest": (
            "BuyWise recommends this as the Cheapest option because it has "
            "the lowest valid price among observed results."
        ),
        "highest_rated": (
            "BuyWise recommends this as Highest Rated because it has the best "
            "combination of rating and review count among observed results."
        ),
        "premium_pick": (
            "BuyWise recommends this as a Premium Pick because it offers high "
            "ratings despite being priced above the market median."
        ),
        "hidden_gem": (
            "BuyWise recommends this as a Hidden Gem because it maintains a "
            "high rating despite having fewer observed reviews. "
            "Review evidence is limited — treat this recommendation with caution."
        ),
    }

    summary = category_summaries.get(
        recommendation_category,
        "BuyWise recommends this product based on observed market data.",
    )

    return RecommendationExplanation(
        summary=summary,
        factors=factors,
        confidence_note="Based on current observed market data.",
        data_sources=["Google Shopping"],
    )
