from typing import Optional
from app.schemas.intelligence import EnhancedProduct, MarketStats, SearchIntent, DealInfo


def analyze_deal(
    product: EnhancedProduct,
    market: MarketStats,
    intent: SearchIntent,
) -> DealInfo:
    """
    Analyses deal quality using observed merchant pricing data.

    Discount percentage is calculated only when both current and old prices
    are valid, positive, and the old price exceeds the current price.

    Budget utilisation is calculated only when the user's intent includes
    a budget and the product has a valid price.

    Deal quality is a BuyWise-derived assessment that combines the
    merchant-advertised discount with the product's position relative to
    the observed market median.  It is NOT a guarantee that the discount
    is genuine — it reflects what was observed in the current search.
    """
    deal = DealInfo()

    # ------------------------------------------------------------------
    # 1. Discount calculation
    # ------------------------------------------------------------------
    if (
        product.extracted_price is not None
        and product.extracted_old_price is not None
        and product.extracted_price > 0
        and product.extracted_old_price > 0
        and product.extracted_old_price > product.extracted_price
    ):
        discount = (
            (product.extracted_old_price - product.extracted_price)
            / product.extracted_old_price
        ) * 100
        deal.discount_pct = round(discount, 1)

        # Deal quality — combines discount with market-median position
        below_median = (
            market.median_price is not None
            and product.extracted_price < market.median_price
        )

        if discount >= 20 and below_median:
            deal.deal_quality = "strong"
        elif discount >= 10 or (discount > 0 and below_median):
            deal.deal_quality = "moderate"
        else:
            deal.deal_quality = "minimal"

    # ------------------------------------------------------------------
    # 2. Budget utilisation
    # ------------------------------------------------------------------
    if (
        intent.budget_max is not None
        and product.extracted_price is not None
        and intent.budget_max > 0
        and product.extracted_price > 0
    ):
        utilisation = (product.extracted_price / intent.budget_max) * 100
        deal.budget_utilisation_pct = round(min(utilisation, 999.0), 1)

        headroom = intent.budget_max - product.extracted_price
        if headroom > 0:
            remaining_pct = round(100 - utilisation)
            deal.budget_headroom = (
                f"₹{int(headroom):,} under budget ({remaining_pct}% remaining)"
            )
        elif headroom == 0:
            deal.budget_headroom = "Exactly at budget"
        else:
            deal.budget_headroom = f"₹{int(abs(headroom)):,} over budget"

    return deal
