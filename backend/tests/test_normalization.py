from app.intelligence.normalization import normalize_shopping_results, _safe_float, _safe_int, _resolve_product_link

def test_normalize_basic_fields():
    raw = [{
        "title": "Headphones",
        "product_id": "123",
        "product_link": "http://example.com",
        "source": "Amazon",
        "price": "₹1,999",
        "extracted_price": 1999.0,
        "rating": 4.5,
        "reviews": 120,
        "thumbnail": "http://image.com"
    }]
    normalized = normalize_shopping_results(raw)
    assert len(normalized) == 1
    p = normalized[0]
    assert p.title == "Headphones"
    assert p.price == "₹1,999"
    assert p.extracted_price == 1999.0
    assert p.rating == 4.5
    assert p.reviews == 120

def test_safe_float():
    assert _safe_float(12.5) == 12.5
    assert _safe_float("12.5") == 12.5
    assert _safe_float("₹1,234.50") == 1234.5
    assert _safe_float(None) is None
    assert _safe_float("invalid") is None

def test_safe_int():
    assert _safe_int(12) == 12
    assert _safe_int("12") == 12
    assert _safe_int("1,234") == 1234
    assert _safe_int("1,234 reviews") == 1234
    assert _safe_int(None) is None
    assert _safe_int("invalid") is None

def test_normalize_missing_fields():
    raw = [{"title": "Only Title"}]
    normalized = normalize_shopping_results(raw)
    assert len(normalized) == 1
    p = normalized[0]
    assert p.title == "Only Title"
    assert p.price is None
    assert p.extracted_price is None

def test_normalize_empty_list():
    assert normalize_shopping_results([]) == []

def test_normalize_malformed_type():
    assert normalize_shopping_results([None, "string", {"title": "Valid"}])
    assert len(normalize_shopping_results([None, "string", {"title": "Valid"}])) == 1


# ---------------------------------------------------------------------------
# Tests for _resolve_product_link and Shape-B (multiple_sources) behaviour
# ---------------------------------------------------------------------------

def test_resolve_product_link_standard_result():
    """Shape-A: product_link is present and returned as-is."""
    item = {"product_link": "https://www.google.com/search?q=phone", "link": "https://other.com"}
    assert _resolve_product_link(item) == "https://www.google.com/search?q=phone"


def test_resolve_product_link_falls_back_to_link_key():
    """product_link is an empty string — should fall back to the link key."""
    item = {"product_link": "", "link": "https://fallback.example.com/product"}
    assert _resolve_product_link(item) == "https://fallback.example.com/product"


def test_resolve_product_link_both_absent():
    """Neither key present — returns None (Shape-B with no URL data)."""
    item = {"title": "Some Product", "product_id": "abc123"}
    assert _resolve_product_link(item) is None


def test_resolve_product_link_whitespace_only():
    """Whitespace-only string is treated as absent; falls back to link if available."""
    item = {"product_link": "   ", "link": "https://real.example.com"}
    assert _resolve_product_link(item) == "https://real.example.com"


def test_normalize_shape_b_aggregated_result():
    """Shape-B items (multiple_sources=True, no price/link/source in raw data)
    must be included in the output but with None for the missing fields.
    The normalizer must not invent data or raise an exception."""
    raw = [{
        "title": "Samsung Galaxy S24 - Marblegray - 256 GB 8GB",
        "product_id": "deadbeef1234",
        "multiple_sources": True,
        "position": 11,
        "rating": 4.2,
        "reviews": 530,
        "thumbnail": "https://example.com/thumb.jpg",
    }]
    normalized = normalize_shopping_results(raw)
    assert len(normalized) == 1
    p = normalized[0]
    assert p.title == "Samsung Galaxy S24 - Marblegray - 256 GB 8GB"
    assert p.product_id == "deadbeef1234"
    assert p.product_link is None   # no URL recoverable without extra API call
    assert p.price is None
    assert p.extracted_price is None
    assert p.source is None
    assert p.rating == 4.2
    assert p.reviews == 530


def test_normalize_shape_b_empty_multiple_sources_flag():
    """multiple_sources=False (or absent) with no link data still yields None link."""
    raw = [{
        "title": "Budget Phone",
        "product_id": "xyz999",
        "multiple_sources": False,
        # no product_link, no link, no price
    }]
    normalized = normalize_shopping_results(raw)
    assert len(normalized) == 1
    p = normalized[0]
    assert p.product_link is None
    assert p.price is None
    assert p.source is None


def test_normalize_shape_a_with_multiple_sources_true_preserves_data():
    """Some Shape-A items set multiple_sources=True but still have a top-level
    product_link, price, and source.  These must be preserved exactly."""
    raw = [{
        "title": "Samsung Galaxy S24+ 5G",
        "product_id": "aaa111",
        "multiple_sources": True,
        "product_link": "https://www.google.com/search?tbs=stt:1",
        "price": "₹89,999",
        "extracted_price": 89999.0,
        "source": "Flipkart",
        "rating": 4.5,
        "reviews": 200,
    }]
    normalized = normalize_shopping_results(raw)
    assert len(normalized) == 1
    p = normalized[0]
    assert p.product_link == "https://www.google.com/search?tbs=stt:1"
    assert p.price == "₹89,999"
    assert p.extracted_price == 89999.0
    assert p.source == "Flipkart"


def test_normalize_extracted_price_zero_not_discarded():
    """extracted_price of 0.0 is a valid value and must not be treated as missing."""
    raw = [{
        "title": "Free Sample",
        "extracted_price": 0.0,
        "price": "₹0",
        "product_link": "https://example.com",
        "source": "Seller",
    }]
    normalized = normalize_shopping_results(raw)
    assert len(normalized) == 1
    p = normalized[0]
    assert p.extracted_price == 0.0
    assert p.price == "₹0"
