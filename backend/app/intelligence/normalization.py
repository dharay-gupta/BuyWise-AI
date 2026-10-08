from app.schemas.product import NormalizedProduct
import re

def normalize_shopping_results(raw_results: list) -> list[NormalizedProduct]:
    """
    Takes a list of raw shopping results from SerpApi and normalizes them
    into a list of NormalizedProduct objects.
    """
    normalized_list = []
    
    for item in raw_results:
        if not isinstance(item, dict):
            continue
            
        # Safely extract numerical values
        extracted_price = _safe_float(item.get("extracted_price"))
        extracted_old_price = _safe_float(item.get("extracted_old_price"))
        rating = _safe_float(item.get("rating"))
        reviews = _safe_int(item.get("reviews"))
        
        # Safely extract basic strings
        title = item.get("title", "").strip() if item.get("title") else None
        
        # In some SerpApi results, 'link' is provided instead of 'product_link'
        product_link = item.get("product_link") or item.get("link")
        
        product = NormalizedProduct(
            title=title,
            product_id=item.get("product_id"),
            product_link=product_link,
            source=item.get("source"),
            price=item.get("price"),
            extracted_price=extracted_price,
            old_price=item.get("old_price"),
            extracted_old_price=extracted_old_price,
            currency=item.get("currency"),
            rating=rating,
            reviews=reviews,
            thumbnail=item.get("thumbnail"),
            delivery=item.get("delivery"),
            availability=item.get("availability"),
            position=item.get("position"),
            snippet=item.get("snippet"),
            tag=item.get("tag"),
            badge=item.get("badge")
        )
        normalized_list.append(product)
        
    return normalized_list

def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        # Fallback to extract numbers using regex if standard casting fails
        if isinstance(val, str):
            match = re.search(r"(\d+(\.\d+)?)", val.replace(',', ''))
            if match:
                return float(match.group(1))
        return None

def _safe_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        if isinstance(val, str):
            match = re.search(r"(\d+)", val.replace(',', ''))
            if match:
                return int(match.group(1))
        return None
