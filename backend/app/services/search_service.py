from app.services.serpapi_client import serpapi_client
from app.intelligence.normalization import normalize_shopping_results
from app.schemas.product import SearchResponse
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def perform_commerce_search(query: str) -> SearchResponse:
    """
    Coordinates searching live commerce data through SerpApi and normalizing it.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    
    # Optional check: excessively long query
    if len(query) > 200:
        raise HTTPException(status_code=400, detail="Search query is too long.")
    
    # 1. Fetch raw data from SerpApi
    raw_data = serpapi_client.search_google_shopping(query)
    
    # Extract shopping results list from response
    shopping_results = raw_data.get("shopping_results", [])
    
    if not shopping_results:
        logger.info(f"No shopping results found for query: '{query}'")
        # Do not throw an error; return an empty list gracefully
        return SearchResponse(query=query, count=0, products=[])
    
    # 2. Normalize data
    normalized_products = normalize_shopping_results(shopping_results)
    
    # 3. Construct response
    return SearchResponse(
        query=query,
        count=len(normalized_products),
        products=normalized_products
    )
