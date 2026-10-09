from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.schemas.product import NormalizedProduct


class ExplanationFactor(BaseModel):
    name: str
    observation: str
    interpretation: str
    strength: str


class RecommendationExplanation(BaseModel):
    summary: str
    factors: List[ExplanationFactor] = []
    confidence_note: str = "Based on current observed market data."
    data_sources: List[str] = ["Google Shopping"]


class ProductAnalysis(BaseModel):
    strengths: List[str] = []
    weaknesses: List[str] = []
    neutral: List[str] = []


class SearchIntent(BaseModel):
    product_query: str
    category: Optional[str] = None
    use_case_signals: List[str] = []
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    priority: str = "balanced"  # balanced, cheapest, best_value, quality_first, cheap, premium, highest_rated
    keywords: List[str] = []


class MarketStats(BaseModel):
    products_analyzed: int
    valid_prices_count: int
    valid_ratings_count: int
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None
    average_price: Optional[float] = None
    median_price: Optional[float] = None
    price_spread: Optional[float] = None


class ScoreBreakdown(BaseModel):
    price: float = 0.0
    rating: float = 0.0
    review_confidence: float = 0.0
    market_position: float = 0.0
    # Maximum possible contributions (for display as X/max)
    price_max: float = 0.0
    rating_max: float = 0.0
    review_confidence_max: float = 0.0
    market_position_max: float = 0.0


class DealInfo(BaseModel):
    """Deal quality analysis based on observed merchant pricing."""
    discount_pct: Optional[float] = None
    deal_quality: Optional[str] = None  # "strong", "moderate", "minimal"
    budget_headroom: Optional[str] = None
    budget_utilisation_pct: Optional[float] = None


class MerchantOffer(BaseModel):
    """A single merchant's observed offer for a product."""
    merchant: str
    price: float
    is_lowest: bool = False


class CrossMerchantInfo(BaseModel):
    """Cross-merchant comparison for the same product_id."""
    merchant_count: int = 1
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None
    best_merchant: Optional[str] = None
    price_spread: Optional[float] = None
    savings_vs_highest: Optional[str] = None
    merchants: List[MerchantOffer] = []


class EnhancedProduct(NormalizedProduct):
    buywise_score: Optional[float] = None
    price_percentile: Optional[float] = None
    review_confidence: Optional[float] = None
    recommendation_tags: List[str] = []
    score_breakdown: Optional[ScoreBreakdown] = None
    insights: List[str] = []
    tradeoff_explanation: Optional[str] = None
    market_savings: Optional[str] = None
    recommendation_explanation: Optional[RecommendationExplanation] = None
    analysis: Optional[ProductAnalysis] = None
    deal_info: Optional[DealInfo] = None
    cross_merchant: Optional[CrossMerchantInfo] = None


class Recommendation(BaseModel):
    category: str
    product_id: str
    reason: str


class Recommendations(BaseModel):
    best_overall: Optional[Recommendation] = None
    best_value: Optional[Recommendation] = None
    cheapest: Optional[Recommendation] = None
    highest_rated: Optional[Recommendation] = None
    premium_pick: Optional[Recommendation] = None
    hidden_gem: Optional[Recommendation] = None


class MerchantInfo(BaseModel):
    name: str
    count: int
    avg_price: Optional[float] = None
    lowest_price: Optional[float] = None


class MerchantStats(BaseModel):
    merchants: List[MerchantInfo] = []
    note: str = "Based on current observed results only"


class IntelligenceResponse(BaseModel):
    query: str
    count: int
    decision_mode: str = "balanced"
    intent: Optional[SearchIntent] = None
    market: Optional[MarketStats] = None
    recommendations: Optional[Recommendations] = None
    products: List[EnhancedProduct] = []
    merchant_stats: Optional[MerchantStats] = None
    market_insights: List[str] = []
