from typing import List
from app.schemas.intelligence import MarketStats
from app.schemas.product import NormalizedProduct
import statistics

def analyze_market(products: List[NormalizedProduct]) -> MarketStats:
    """
    Calculates market statistics based ONLY on observed valid data.
    """
    valid_prices = [p.extracted_price for p in products if p.extracted_price is not None]
    valid_ratings = [p.rating for p in products if p.rating is not None]
    
    lowest = min(valid_prices) if valid_prices else None
    highest = max(valid_prices) if valid_prices else None
    avg = sum(valid_prices) / len(valid_prices) if valid_prices else None
    med = statistics.median(valid_prices) if valid_prices else None
    spread = (highest - lowest) if highest is not None and lowest is not None else None
    
    return MarketStats(
        products_analyzed=len(products),
        valid_prices_count=len(valid_prices),
        valid_ratings_count=len(valid_ratings),
        lowest_price=lowest,
        highest_price=highest,
        average_price=avg,
        median_price=med,
        price_spread=spread
    )
