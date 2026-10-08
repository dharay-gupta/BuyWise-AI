from app.intelligence.normalization import normalize_shopping_results, _safe_float, _safe_int

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
