from typing import List, Dict, Optional
from app.schemas.intelligence import MerchantInfo, MerchantStats, EnhancedProduct


def analyze_merchants(products: List[EnhancedProduct]) -> MerchantStats:
    """
    Aggregates merchant information from observed SerpApi results.

    Only uses data actually returned by SerpApi.
    Does NOT claim that any merchant is universally cheaper.
    All output is labeled as based on current observed results.
    """
    merchant_prices: Dict[str, List[float]] = {}
    merchant_counts: Dict[str, int] = {}

    for product in products:
        source = product.source
        if not source:
            source = "Unknown"

        merchant_counts[source] = merchant_counts.get(source, 0) + 1

        if product.extracted_price is not None:
            if source not in merchant_prices:
                merchant_prices[source] = []
            merchant_prices[source].append(product.extracted_price)

    # Build MerchantInfo list, sorted by count descending
    merchant_list: List[MerchantInfo] = []
    for name, count in sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True):
        prices = merchant_prices.get(name, [])
        avg_price = round(sum(prices) / len(prices), 2) if prices else None
        lowest_price = min(prices) if prices else None

        merchant_list.append(
            MerchantInfo(
                name=name,
                count=count,
                avg_price=avg_price,
                lowest_price=lowest_price,
            )
        )

    return MerchantStats(
        merchants=merchant_list,
        note="Based on current observed results only",
    )
