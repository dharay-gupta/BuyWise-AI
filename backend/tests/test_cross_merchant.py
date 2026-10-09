import pytest
from app.schemas.intelligence import EnhancedProduct
from app.intelligence.cross_merchant import build_cross_merchant_map


def test_two_distinct_merchants_produce_comparison():
    products = [
        EnhancedProduct(product_id="prod-100", source="Amazon", extracted_price=999.0),
        EnhancedProduct(product_id="prod-100", source="Flipkart", extracted_price=1199.0),
    ]

    result = build_cross_merchant_map(products)
    assert "prod-100" in result
    info = result["prod-100"]
    assert info.merchant_count == 2
    assert info.lowest_price == 999.0
    assert info.highest_price == 1199.0
    assert len(info.merchants) == 2


def test_lowest_priced_merchant_identified_correctly():
    products = [
        EnhancedProduct(product_id="prod-200", source="Croma", extracted_price=24999.0),
        EnhancedProduct(product_id="prod-200", source="Reliance Digital", extracted_price=22999.0),
        EnhancedProduct(product_id="prod-200", source="Tata CLiQ", extracted_price=23499.0),
    ]

    result = build_cross_merchant_map(products)
    info = result["prod-200"]
    assert info.best_merchant == "Reliance Digital"
    assert info.lowest_price == 22999.0

    # Verify is_lowest flags on individual offers
    for offer in info.merchants:
        if offer.merchant == "Reliance Digital":
            assert offer.is_lowest is True
        else:
            assert offer.is_lowest is False


def test_price_spread_and_savings_text():
    products = [
        EnhancedProduct(product_id="prod-300", source="Store A", extracted_price=800.0),
        EnhancedProduct(product_id="prod-300", source="Store B", extracted_price=1000.0),
    ]

    result = build_cross_merchant_map(products)
    info = result["prod-300"]
    assert info.price_spread == 200.0
    # spread = 200, highest = 1000 -> 20%
    assert "₹200 price spread across 2 merchants (20%)" in info.savings_vs_highest


def test_single_merchant_does_not_produce_comparison():
    products = [
        EnhancedProduct(product_id="prod-400", source="SingleStore", extracted_price=500.0),
    ]

    result = build_cross_merchant_map(products)
    assert "prod-400" not in result
    assert len(result) == 0


def test_missing_or_empty_product_id_excluded():
    products = [
        EnhancedProduct(product_id=None, source="Store A", extracted_price=500.0),
        EnhancedProduct(product_id=None, source="Store B", extracted_price=600.0),
        EnhancedProduct(product_id="", source="Store A", extracted_price=500.0),
        EnhancedProduct(product_id="", source="Store B", extracted_price=600.0),
    ]

    result = build_cross_merchant_map(products)
    assert len(result) == 0


def test_invalid_prices_excluded():
    products = [
        # Missing price
        EnhancedProduct(product_id="prod-500", source="Store A", extracted_price=None),
        # Zero price
        EnhancedProduct(product_id="prod-500", source="Store B", extracted_price=0.0),
        # Negative price
        EnhancedProduct(product_id="prod-500", source="Store C", extracted_price=-50.0),
        # Only one valid price
        EnhancedProduct(product_id="prod-500", source="Store D", extracted_price=1000.0),
    ]

    result = build_cross_merchant_map(products)
    # Since only 1 merchant has a valid price, distinct merchant count < 2
    assert "prod-500" not in result


def test_missing_merchant_name_excluded():
    products = [
        EnhancedProduct(product_id="prod-600", source=None, extracted_price=500.0),
        EnhancedProduct(product_id="prod-600", source="", extracted_price=600.0),
        EnhancedProduct(product_id="prod-600", source="ValidStore", extracted_price=550.0),
    ]

    result = build_cross_merchant_map(products)
    # Only 1 valid merchant name -> no comparison
    assert "prod-600" not in result


def test_duplicate_offers_same_merchant_not_inflated():
    products = [
        EnhancedProduct(product_id="prod-700", source="SameStore", extracted_price=500.0),
        EnhancedProduct(product_id="prod-700", source="SameStore", extracted_price=520.0),
        EnhancedProduct(product_id="prod-700", source="SameStore", extracted_price=490.0),
    ]

    result = build_cross_merchant_map(products)
    # All from 'SameStore', so only 1 distinct merchant
    assert "prod-700" not in result


def test_unrelated_product_ids_never_grouped():
    products = [
        EnhancedProduct(product_id="phone-alpha", source="Amazon", extracted_price=15000.0),
        EnhancedProduct(product_id="phone-beta", source="Flipkart", extracted_price=16000.0),
        EnhancedProduct(product_id="laptop-gamma", source="Croma", extracted_price=55000.0),
    ]

    result = build_cross_merchant_map(products)
    # Each product_id has only 1 merchant
    assert len(result) == 0


def test_empty_input_returns_empty_mapping():
    assert build_cross_merchant_map([]) == {}
