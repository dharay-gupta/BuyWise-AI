from app.services.search_service import perform_commerce_search
from app.schemas.intelligence import IntelligenceResponse, EnhancedProduct
from app.intelligence.intent_parser import parse_intent
from app.intelligence.market_analysis import analyze_market
from app.intelligence.scoring import score_product, DECISION_MODE_LABELS
from app.intelligence.recommendations import generate_recommendations
from app.intelligence.tradeoffs import generate_tradeoff, generate_savings_text
from app.intelligence.merchant_analysis import analyze_merchants
from app.intelligence.market_insight import generate_market_insights
import logging

logger = logging.getLogger(__name__)


def process_intelligent_search(query: str, mode: str = "balanced") -> IntelligenceResponse:
    """
    Orchestrates the entire BuyWise intelligence pipeline.

    Pipeline:
        search_service → intent_parser → market_analysis → scoring →
        recommendations → tradeoffs → merchant_analysis → market_insights

    Args:
        query: User search query (natural language)
        mode:  Decision mode (balanced | cheapest | best_value | quality_first)
               Controls scoring weights. Validated at the route layer.
    """
    # 1. Basic search (Phase 2)
    search_response = perform_commerce_search(query)
    products = search_response.products

    if not products:
        return IntelligenceResponse(
            query=query,
            count=0,
            decision_mode=mode,
            products=[],
        )

    # Convert NormalizedProduct → EnhancedProduct
    enhanced_products = [EnhancedProduct(**p.model_dump()) for p in products]

    # 2. Intent Parsing
    intent = parse_intent(query)

    # Override intent.priority with the explicit mode when provided so that
    # the user-selected decision mode always takes precedence over what the
    # natural-language parser infers.
    intent.priority = mode

    # 3. Market Analysis (only on valid observed data)
    market = analyze_market(enhanced_products)

    # 4. Scoring — uses intent.priority (= mode)
    for product in enhanced_products:
        score_product(product, market, intent)

    # 5. Per-product insights, tradeoffs, and savings text
    for product in enhanced_products:
        # Price position insight
        if product.extracted_price is not None and market.median_price is not None:
            if product.extracted_price < market.median_price:
                product.insights.append("Below observed market median")
            elif product.extracted_price > market.median_price:
                product.insights.append("Above observed market median")
            else:
                product.insights.append("At observed market median")

        # Review confidence insight
        if product.review_confidence is not None:
            if product.review_confidence > 0.7:
                product.insights.append("Strong rating evidence")
            elif product.review_confidence > 0.3:
                product.insights.append("Moderate rating evidence")
            elif product.review_confidence > 0:
                product.insights.append("Limited review evidence")

        # Tradeoff explanation
        product.tradeoff_explanation = generate_tradeoff(product, market)

        # Market savings text
        product.market_savings = generate_savings_text(product, market)

    # 6. Recommendations — pass intent so budget filtering applies
    recommendations = generate_recommendations(enhanced_products, market, intent)

    # 7. Merchant Intelligence
    merchant_stats = analyze_merchants(enhanced_products)

    # 8. Market Insights
    market_insights = generate_market_insights(enhanced_products, market)

    # Sort products: best BuyWise scores first
    enhanced_products.sort(key=lambda x: x.buywise_score or 0, reverse=True)

    return IntelligenceResponse(
        query=query,
        count=len(enhanced_products),
        decision_mode=mode,
        intent=intent,
        market=market,
        recommendations=recommendations,
        products=enhanced_products,
        merchant_stats=merchant_stats,
        market_insights=market_insights,
    )
