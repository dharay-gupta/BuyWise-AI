from typing import List
from app.schemas.intelligence import EnhancedProduct, MarketStats


def generate_market_insights(
    products: List[EnhancedProduct], market: MarketStats
) -> List[str]:
    """
    Generates a list of honest market insight statements based solely on
    observed SerpApi data and deterministic calculations from those observations.

    All statements are explicitly labeled as observations, not universal claims.
    Never fabricates demand, sales, inventory, or historical data.
    """
    insights: List[str] = []

    if not products or market.products_analyzed == 0:
        return insights

    # -----------------------------------------------------------------------
    # Price concentration insight
    # -----------------------------------------------------------------------
    if (
        market.lowest_price is not None
        and market.highest_price is not None
        and market.median_price is not None
        and market.valid_prices_count >= 3
    ):
        low = market.lowest_price
        high = market.highest_price
        spread = high - low

        if spread > 0:
            # Check if most products cluster in the lower half
            lower_half_count = sum(
                1
                for p in products
                if p.extracted_price is not None
                and p.extracted_price <= (low + spread * 0.5)
            )
            lower_pct = round(lower_half_count / market.valid_prices_count * 100)

            insights.append(
                f"Observed prices range from ₹{int(low):,} to ₹{int(high):,}. "
                f"{lower_pct}% of observed products fall in the lower half of this range."
            )

    # -----------------------------------------------------------------------
    # High-rated products with strong evidence
    # -----------------------------------------------------------------------
    if market.valid_ratings_count >= 3:
        strong_evidence = [
            p
            for p in products
            if p.rating is not None
            and p.rating >= 4.5
            and p.reviews is not None
            and p.reviews >= 100
        ]
        count = len(strong_evidence)
        if count > 0:
            insights.append(
                f"Only {count} of {market.products_analyzed} observed products "
                f"have a rating of 4.5⭐ or above with at least 100 reviews."
            )

    # -----------------------------------------------------------------------
    # Below-median share
    # -----------------------------------------------------------------------
    if market.median_price is not None and market.valid_prices_count >= 3:
        below_median = [
            p
            for p in products
            if p.extracted_price is not None
            and p.extracted_price < market.median_price
        ]
        pct = round(len(below_median) / market.valid_prices_count * 100)
        insights.append(
            f"{pct}% of observed products are priced below the observed market median "
            f"of ₹{int(market.median_price):,}."
        )

    # -----------------------------------------------------------------------
    # Average price vs. median comparison
    # -----------------------------------------------------------------------
    if (
        market.average_price is not None
        and market.median_price is not None
        and market.valid_prices_count >= 5
    ):
        avg = market.average_price
        med = market.median_price
        if avg > med * 1.15:
            insights.append(
                f"The observed average price (₹{int(avg):,}) is notably higher than "
                f"the median (₹{int(med):,}), suggesting some higher-priced products "
                f"are pulling the average up."
            )
        elif avg < med * 0.85:
            insights.append(
                f"The observed average price (₹{int(avg):,}) is notably lower than "
                f"the median (₹{int(med):,}), suggesting some very low-priced products "
                f"in this observed set."
            )

    # -----------------------------------------------------------------------
    # Missing data note
    # -----------------------------------------------------------------------
    products_without_price = market.products_analyzed - market.valid_prices_count
    if products_without_price > 0:
        insights.append(
            f"{products_without_price} of {market.products_analyzed} observed products "
            f"did not include price data and were excluded from price analysis."
        )

    # -----------------------------------------------------------------------
    # Cross-merchant deals observation
    # -----------------------------------------------------------------------
    cross_merchant_products = [
        p for p in products
        if p.cross_merchant and p.cross_merchant.merchant_count > 1
    ]
    if cross_merchant_products:
        count = len(cross_merchant_products)
        insights.append(
            f"We found {count} product{'s' if count > 1 else ''} offered by multiple "
            f"observed merchants, allowing for direct price comparison."
        )

    return insights
