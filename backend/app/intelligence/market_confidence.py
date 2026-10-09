from typing import List, Optional
from app.schemas.intelligence import MarketConfidence, MarketStats
from app.schemas.product import NormalizedProduct


def calculate_market_confidence(
    products: List[NormalizedProduct],
    market: Optional[MarketStats] = None,
) -> MarketConfidence:
    """
    Calculates a deterministic BuyWise evidence-quality indicator (0–100)
    reflecting the completeness, breadth, and statistical density of observed
    search results from Google Shopping.

    This is an empirical heuristic of data completeness within the current
    result set — NOT a calibrated probability or guarantee of whole-market
    representativeness.

    Scoring Components (Total: 100 points):
      1. Sample Size Adequacy (Max 35 points):
         - n == 0: 0 points
         - n < 5:  scaled linearly up to ~9.6 points (strictly marked 'limited')
         - 5 <= n <= 20: 15.0 to 35.0 points
         - n > 20: 35.0 points
      2. Price Coverage (Max 25 points):
         - Percentage of products with valid positive extracted prices
      3. Rating & Review Evidence Breadth (Max 25 points):
         - 60% weight on rating presence + 40% weight on review count presence
      4. Merchant Diversity (Max 15 points):
         - Breadth of distinct observed merchant sources (0: 0, 1: 5, 2: 8, 3: 11, 4+: 15)

    Confidence Levels:
      - 'limited':  sample_size < 5 OR score < 45.0
      - 'moderate': sample_size >= 5 AND 45.0 <= score < 75.0
      - 'high':     sample_size >= 5 AND score >= 75.0 AND price_coverage >= 70% AND merchants >= 2
    """
    total = len(products)
    if total == 0:
        return MarketConfidence(
            score=0.0,
            level="limited",
            sample_size=0,
            price_coverage_pct=0.0,
            rating_coverage_pct=0.0,
            merchant_diversity_count=0,
            reasons=["No observed products returned for this query."],
        )

    # 1. Sample Size Adequacy (Max 35)
    if total < 5:
        sample_score = round((total / 5.0) * 12.0, 1)
    elif total <= 20:
        sample_score = round(15.0 + ((total - 5) / 15.0) * 20.0, 1)
    else:
        sample_score = 35.0

    # 2. Price Coverage (Max 25)
    valid_prices = [
        p for p in products
        if p.extracted_price is not None and p.extracted_price > 0
    ]
    price_coverage = len(valid_prices) / total
    price_score = round(price_coverage * 25.0, 1)

    # 3. Rating & Review Coverage (Max 25)
    rated = [p for p in products if p.rating is not None and p.rating > 0]
    reviewed = [p for p in products if p.reviews is not None and p.reviews > 0]
    rating_cov = len(rated) / total
    review_cov = len(reviewed) / total
    rating_score = round((0.6 * rating_cov + 0.4 * review_cov) * 25.0, 1)

    # 4. Merchant Diversity (Max 15)
    unique_merchants = {
        p.source.strip() for p in products
        if p.source and p.source.strip()
    }
    merchant_count = len(unique_merchants)
    if merchant_count == 0:
        merchant_score = 0.0
    elif merchant_count == 1:
        merchant_score = 5.0
    elif merchant_count == 2:
        merchant_score = 8.0
    elif merchant_count == 3:
        merchant_score = 11.0
    else:
        merchant_score = 15.0

    # Total Score
    total_score = min(
        100.0,
        max(0.0, sample_score + price_score + rating_score + merchant_score)
    )
    total_score = round(total_score, 1)

    # Level Determination
    if total < 5 or total_score < 45.0:
        level = "limited"
    elif total_score >= 75.0 and price_coverage >= 0.7 and merchant_count >= 2:
        level = "high"
    else:
        level = "moderate"

    # Evidence Reasons
    reasons: List[str] = []

    # Sample reason
    if total < 5:
        reasons.append(
            f"Small observed sample size ({total} product{'s' if total != 1 else ''}) "
            f"provides limited market visibility."
        )
    elif total < 15:
        reasons.append(f"Moderate observed sample size of {total} products.")
    else:
        reasons.append(f"Substantial observed sample of {total} products.")

    # Price reason
    price_pct = round(price_coverage * 100, 1)
    if price_coverage == 1.0:
        reasons.append("100% of observed listings include valid price data.")
    elif price_coverage >= 0.8:
        reasons.append(f"{price_pct:.0f}% of observed listings have verified price points.")
    else:
        missing_count = total - len(valid_prices)
        reasons.append(
            f"Only {price_pct:.0f}% of listings have prices ({missing_count} missing)."
        )

    # Rating reason
    rating_pct = round(rating_cov * 100, 1)
    if rating_cov >= 0.8:
        reasons.append(f"Broad rating coverage ({rating_pct:.0f}% of listings rated).")
    elif rating_cov >= 0.4:
        reasons.append(f"Partial rating coverage ({rating_pct:.0f}% of listings rated).")
    else:
        reasons.append("Sparse customer rating data in observed results.")

    # Merchant reason
    if merchant_count >= 3:
        reasons.append(
            f"Multi-store representation across {merchant_count} distinct merchants."
        )
    elif merchant_count == 2:
        reasons.append("Listings span 2 distinct merchant sources.")
    elif merchant_count == 1:
        reasons.append("All observed listings originate from a single merchant.")
    else:
        reasons.append("No merchant source attribution available.")

    return MarketConfidence(
        score=total_score,
        level=level,
        sample_size=total,
        price_coverage_pct=round(price_coverage * 100, 1),
        rating_coverage_pct=round(rating_cov * 100, 1),
        merchant_diversity_count=merchant_count,
        reasons=reasons,
    )
