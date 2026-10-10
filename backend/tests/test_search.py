from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

@patch("app.services.search_service.serpapi_client")
def test_search_endpoint_success(mock_serpapi_client):
    # Mock the return value of search_google_shopping
    mock_serpapi_client.search_google_shopping.return_value = {
        "shopping_results": [
            {
                "title": "Mock Headphones",
                "price": "₹1,000",
                "extracted_price": 1000.0,
                "rating": 4.0,
                "reviews": 10
            }
        ]
    }
    
    response = client.get("/api/search?q=headphones")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "headphones"
    assert data["count"] == 1
    assert data["products"][0]["title"] == "Mock Headphones"
    assert data["products"][0]["extracted_price"] == 1000.0
    
@patch("app.services.search_service.serpapi_client")
def test_search_endpoint_empty_results(mock_serpapi_client):
    mock_serpapi_client.search_google_shopping.return_value = {
        "shopping_results": []
    }
    
    response = client.get("/api/search?q=nothing")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["products"] == []

def test_search_endpoint_missing_query():
    # FastAPI automatically validates missing required query params
    response = client.get("/api/search")
    assert response.status_code == 422 # Unprocessable Entity


@patch("app.services.search_service.serpapi_client")
def test_search_endpoint_includes_market_confidence(mock_serpapi_client):
    mock_serpapi_client.search_google_shopping.return_value = {
        "shopping_results": [
            {
                "title": "Mock Product",
                "price": "₹2,000",
                "extracted_price": 2000.0,
                "rating": 4.5,
                "reviews": 120,
                "source": "Amazon",
            }
        ]
    }
    response = client.get("/api/search?q=phone")
    assert response.status_code == 200
    data = response.json()
    assert "confidence" in data
    assert data["confidence"] is not None
    assert "score" in data["confidence"]
    assert "level" in data["confidence"]
    assert data["confidence"]["level"] == "limited"  # 1 product < 5
    assert "confidence" in data["market"]
    assert data["market"]["confidence"] is not None

@patch("app.services.search_service.serpapi_client")
def test_search_endpoint_filters_accessories(mock_serpapi_client):
    mock_serpapi_client.search_google_shopping.return_value = {
        "shopping_results": [
            {
                "title": "Smartphone XYZ",
                "price": "₹50,000",
                "source": "Store A",
                "extracted_price": 50000.0,
                "rating": 4.5,
                "reviews": 100
            },
            {
                "title": "Smartphone XYZ Case Cover",
                "price": "₹500",
                "source": "Store B",
                "extracted_price": 500.0,
                "rating": 4.0,
                "reviews": 50
            }
        ]
    }
    response = client.get("/api/search?q=smartphone")
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) == 2
    assert data["market"]["median_price"] is None
    assert data["market"]["lowest_price"] == 50000.0
