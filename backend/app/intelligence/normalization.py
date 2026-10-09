from app.schemas.product import NormalizedProduct
import re

# Phrases that indicate free shipping when present in the delivery/shipping
# text from SerpApi.  Only explicit mentions qualify.
_FREE_SHIPPING_PHRASES = (
    "free shipping",
    "free delivery",
    "free standard shipping",
    "ships free",
)


def _extract_free_shipping(shipping_text: str) -> bool | None:
    """
    Return True when the shipping text **explicitly** contains a recognised
    free-shipping phrase.  Return None (not False) for all other cases so
    callers can distinguish "explicitly absent" from "not present in data".

    Never infers free shipping from a missing fee.
    """
    if not shipping_text or not isinstance(shipping_text, str):
        return None
    low = shipping_text.strip().lower()
    if any(phrase in low for phrase in _FREE_SHIPPING_PHRASES):
        return True
    return None


def _sanitise_offer_text(raw: str | None) -> str | None:
    """
    Return a sanitised version of the raw special-offer text string, or None
    when the value is absent, empty, or contains only whitespace.

    No semantic inference is performed — the text is returned verbatim
    (stripped) so the frontend can display it as a neutral label.
    """
    if not raw or not isinstance(raw, str):
        return None
    stripped = raw.strip()
    return stripped if stripped else None


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

        # ----------------------------------------------------------------
        # Offer Intelligence (Phase 6.2)
        # ----------------------------------------------------------------
        # SerpApi may include a "delivery" field with shipping text.
        # We also check "shipping" as a direct alternate key used in some
        # response shapes.
        delivery_raw = item.get("delivery") or item.get("shipping")
        delivery_text = delivery_raw.strip() if isinstance(delivery_raw, str) else None

        # Determine free_shipping: explicit phrases only, never inferred.
        free_shipping = _extract_free_shipping(delivery_text)

        # shipping_info: store the delivery text verbatim (as shipping info);
        # separate from `delivery` to keep backward compatibility with the
        # existing `delivery` field which is also surfaced to the frontend.
        shipping_info = delivery_text if delivery_text else None

        # Special-offer text: SerpApi may provide an "extensions" list or
        # a direct "tag" / "badge" / "offer" field.  We check the most common
        # locations without inventing data.
        offer_text_raw = item.get("offer") or item.get("extensions")
        if isinstance(offer_text_raw, list):
            # Some SerpApi shapes use a list of extension strings
            offer_text_raw = " | ".join(str(x) for x in offer_text_raw if x)
        offer_text = _sanitise_offer_text(offer_text_raw)

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
            # delivery: only pass if it's a non-empty string (Pydantic requires str)
            delivery=item.get("delivery") if isinstance(item.get("delivery"), str) else None,
            availability=item.get("availability"),
            position=item.get("position"),
            snippet=item.get("snippet"),
            tag=item.get("tag"),
            badge=item.get("badge"),
            # Offer Intelligence fields
            shipping_info=shipping_info,
            free_shipping=free_shipping,
            offer_text=offer_text,
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
