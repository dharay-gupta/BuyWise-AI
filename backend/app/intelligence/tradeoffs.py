from app.schemas.intelligence import EnhancedProduct, MarketStats
from typing import Optional


def generate_tradeoff(product: EnhancedProduct, market: MarketStats) -> str:
    """
    Generates a deterministic tradeoff explanation based on the product's
    position compared to the observed market data.
    All statements are based on observed SerpApi data only.
    """
    if product.extracted_price is None:
        return "Insufficient price data to generate a reliable market comparison."

    parts = []

    # Compare to median
    if market.median_price:
        diff = market.median_price - product.extracted_price
        if diff > 0:
            pct = round((diff / market.median_price) * 100)
            parts.append(
                f"₹{int(diff)} ({pct}%) below the observed market median"
            )
        elif diff < 0:
            pct = round((abs(diff) / market.median_price) * 100)
            parts.append(
                f"₹{int(abs(diff))} ({pct}%) above the observed market median"
            )
        else:
            parts.append("Priced exactly at the observed market median")

    # Add rating context
    if product.rating:
        if product.reviews and product.reviews > 100:
            parts.append(
                f"with strong rating evidence ({product.rating}⭐, {product.reviews:,} reviews)"
            )
        elif product.reviews and product.reviews > 0:
            parts.append(
                f"with a {product.rating}⭐ rating (limited review volume — {product.reviews} reviews)"
            )
        else:
            parts.append(f"with a {product.rating}⭐ rating (no review count observed)")
    else:
        parts.append("but lacks rating evidence in observed data")

    explanation = ". ".join(parts).strip()
    if explanation:
        explanation = explanation[0].upper() + explanation[1:]
    if explanation and not explanation.endswith("."):
        explanation += "."

    return explanation


def generate_hidden_gem_tradeoff(product: EnhancedProduct) -> str:
    """
    Specific trade-off text for a Hidden Gem.
    """
    return (
        "Strong observed value at a competitive price, but review evidence is "
        "limited compared to top picks — worth considering if budget is a priority."
    )


def generate_savings_text(
    product: EnhancedProduct, market: MarketStats
) -> Optional[str]:
    """
    Returns a short market savings insight string based solely on observed data.
    Returns None when there is insufficient data to make a meaningful statement.
    All output is labelled as based on observed data.
    """
    if product.extracted_price is None or market.median_price is None:
        return None

    diff = market.median_price - product.extracted_price

    if diff > 0:
        pct = round((diff / market.median_price) * 100)
        return f"₹{int(diff)} below observed market median ({pct}% savings vs. median)"
    elif diff < 0:
        pct = round((abs(diff) / market.median_price) * 100)
        return f"₹{int(abs(diff))} above observed market median ({pct}% above median)"
    else:
        return "Priced at the observed market median"
