from typing import List, Dict
from app.schemas.intelligence import (
    EnhancedProduct,
    CrossMerchantInfo,
    MerchantOffer,
)


def build_cross_merchant_map(
    products: List[EnhancedProduct],
) -> Dict[str, CrossMerchantInfo]:
    """
    Groups products by ``product_id`` and builds cross-merchant comparison
    data for products that appear from **multiple distinct merchants** with
    valid pricing.

    Identity matching uses ``product_id`` (assigned by Google Shopping via
    SerpApi).  Products whose ``product_id`` is ``None`` or empty are
    excluded because there is no reliable way to assert identity.

    Only merchants with a valid, positive ``extracted_price`` and a non-empty
    ``source`` are included so the comparison is meaningful.

    Returns a dict keyed by ``product_id``.  Products that appear from only
    one merchant will **not** have an entry — the absence of a key means
    "single merchant observed".
    """
    # Step 1: group by product_id
    groups: Dict[str, List[EnhancedProduct]] = {}
    for p in products:
        pid = p.product_id
        if not pid:
            continue
        groups.setdefault(pid, []).append(p)

    result: Dict[str, CrossMerchantInfo] = {}

    for pid, group in groups.items():
        # Keep only products with a valid price and a known merchant
        valid = [
            p
            for p in group
            if p.extracted_price is not None
            and p.extracted_price > 0
            and p.source
        ]
        # Require at least two *distinct* merchants
        unique_merchants = {p.source for p in valid}
        if len(unique_merchants) < 2:
            continue

        prices = [p.extracted_price for p in valid]
        lowest = min(prices)
        highest = max(prices)

        offers: List[MerchantOffer] = []
        for p in valid:
            offers.append(
                MerchantOffer(
                    merchant=p.source,
                    price=p.extracted_price,
                    is_lowest=(p.extracted_price == lowest),
                )
            )
        offers.sort(key=lambda o: o.price)

        best_merchant = next(
            (o.merchant for o in offers if o.is_lowest), None
        )
        spread = highest - lowest

        savings_text = None
        if spread > 0:
            savings_pct = round((spread / highest) * 100)
            savings_text = (
                f"₹{int(spread):,} price spread across "
                f"{len(unique_merchants)} merchants ({savings_pct}%)"
            )

        result[pid] = CrossMerchantInfo(
            merchant_count=len(unique_merchants),
            lowest_price=lowest,
            highest_price=highest,
            best_merchant=best_merchant,
            price_spread=spread,
            savings_vs_highest=savings_text,
            merchants=offers,
        )

    return result
