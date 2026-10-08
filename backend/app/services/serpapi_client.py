import serpapi
from app.config import settings
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class SerpApiClient:
    def __init__(self):
        if not settings.serpapi_api_key:
            logger.error("SerpApi API key is missing from configuration.")
        self.api_key = settings.serpapi_api_key

    def search_google_shopping(self, query: str) -> dict:
        if not self.api_key:
            raise HTTPException(status_code=500, detail="Search service is currently unavailable due to missing configuration.")
            
        params = {
            "engine": "google_shopping",
            "q": query,
            "gl": "in",
            "hl": "en",
            "api_key": self.api_key
        }

        try:
            # We initialize a localized client per request so it remains thread-safe
            # and uses the official library
            client = serpapi.Client(api_key=self.api_key)
            # The library has search methods, e.g., client.search(params)
            results = client.search(params)
            # We return it as a dict which is what `.as_dict()` gives us from the object
            return results.as_dict()
        except Exception as e:
            # Depending on exactly how serpapi package raises errors, we catch all
            # application level failures here.
            logger.error(f"Error fetching from SerpApi: {str(e)}")
            raise HTTPException(status_code=502, detail="Error retrieving data from search provider.")

serpapi_client = SerpApiClient()
