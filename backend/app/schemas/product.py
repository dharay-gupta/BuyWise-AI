from pydantic import BaseModel, HttpUrl
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

class SearchResponse(BaseModel):
    query: str
    count: int
    products: List[NormalizedProduct]
