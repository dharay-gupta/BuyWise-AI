from pydantic import BaseModel
from typing import Optional, List


class NormalizedProduct(BaseModel):
    title: Optional[str] = None
    product_id: Optional[str] = None
    product_link: Optional[str] = None
    source: Optional[str] = None
    price: Optional[str] = None
    extracted_price: Optional[float] = None
    old_price: Optional[str] = None
    extracted_old_price: Optional[float] = None
    currency: Optional[str] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    thumbnail: Optional[str] = None
    delivery: Optional[str] = None
    availability: Optional[str] = None
    position: Optional[int] = None
    snippet: Optional[str] = None
    tag: Optional[str] = None
    badge: Optional[str] = None

    # --- Offer Intelligence fields (Phase 6.2) ---
    # Shipping text verbatim from the SerpApi result (e.g. "Free shipping",
    # "Delivery by Thu", "+₹49 shipping").  None when absent from source data.
    shipping_info: Optional[str] = None
    # True ONLY when the source data explicitly states free shipping.
    # Never inferred from a missing shipping fee.
    free_shipping: Optional[bool] = None
    # Special-offer text verbatim from the SerpApi result (e.g. "10% off with
    # HDFC card").  None when absent from source data.
    offer_text: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    count: int
    products: List[NormalizedProduct]
