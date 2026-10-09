from app.services.search_service import perform_commerce_search_with_fallback
from app.schemas.intelligence import IntelligenceResponse, EnhancedProduct
from app.intelligence.intent_parser import parse_intent
from app.intelligence.market_analysis import analyze_market
from app.intelligence.scoring import score_product, DECISION_MODE_LABELS
from app.intelligence.recommendations import generate_recommendations
from app.intelligence.tradeoffs import generate_tradeoff, generate_savings_text
from app.intelligence.merchant_analysis import analyze_merchants
from app.intelligence.market_insight import generate_market_insights
from app.intelligence.explainer import explain_recommendation
from app.intelligence.strengths_weaknesses import analyze_strengths_weaknesses
from app.intelligence.deal_analysis import analyze_deal
from app.intelligence.cross_merchant import build_cross_merchant_map
from app.intelligence.market_confidence import calculate_market_confidence
from app.intelligence.category_detector import detect_category  # Phase 6.4
import logging

logger = logging.getLogger(__name__)


def process_intelligent_search(query: str, mode: str = "balanced") -> IntelligenceResponse:
    """
    Orchestrates the entire BuyWise intelligence pipeline.

    Pipeline:
        search_service -> intent_parser -> category_detector -> market_analysis
        -> scoring -> recommendations -> tradeoffs -> merchant_analysis
        -> market_insights

    Args:
        query: User search query (natural language)
        mode:  Decision mode (balanced | cheapest | best_value | quality_first)
               Controls scoring weights. Validated at the route layer.
    """
    # 1. Parse intent FIRST so we have a clean product query for the
    #    potential fallback search.  Budget / currency / location from the
    #    original query are preserved in `intent` throughout.
    intent = parse_intent(query)

    # Override intent.priority with the explicit mode when provided so that
    # the user-selected decision mode always takes precedence over what the
    # natural-language parser infers.
    intent.priority = mode

    # Build the fallback query from the parsed intent's clean product query.
    # The intent parser already strips budget phrases (e.g. "under 5000") and
    # priority qualifiers, leaving just the core product terms.
    fallback_query = intent.product_query.strip() if intent.product_query else ""

    # 2. Search - with a single fallback if the initial result is sparse.
    search_response, fallback_used = perform_commerce_search_with_fallback(
        original_query=query,
        fallback_query=fallback_query,
    )
    products = search_response.products

    if not products:
        empty_conf = calculate_market_confidence([])
        return IntelligenceResponse(
            query=query,
            count=0,
            decision_mode=mode,
            intent=intent,
            products=[],
            confidence=empty_conf,
            search_used_fallback=fallback_used if fallback_used else None,
        )

    # Convert NormalizedProduct -> EnhancedProduct
    enhanced_products = [EnhancedProduct(**p.model_dump()) for p in products]

    # 3. Category Detection (Phase 6.4)
    #    Use product titles as secondary evidence to help classify generic queries.
    product_titles = [p.title for p in enhanced_products if p.title]
    detected_category = detect_category(query, intent, product_titles)
    logger.debug("Category detected: %s for query: %r", detected_category, query)

    # 3.5 Market Analysis (only on valid observed data)
    market = analyze_market(enhanced_products)

    # 3.6 Market Evidence Confidence (Phase 6.1)
    confidence = calculate_market_confidence(enhanced_products, market)
    market.confidence = confidence

    # 4. Scoring - uses intent.priority (= mode) + detected_category (Phase 6.4)
    for product in enhanced_products:
        score_product(product, market, intent, detected_category)

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

        # Deal analysis (Phase 5.3)
        product.deal_info = analyze_deal(product, market, intent)

    # 5.5 Cross-merchant intelligence (Phase 5.3)
    cross_merchant_map = build_cross_merchant_map(enhanced_products)
    for product in enhanced_products:
        pid = product.product_id
        if pid and pid in cross_merchant_map:
            product.cross_merchant = cross_merchant_map[pid]

    # 6. Recommendations - pass intent so budget filtering applies
    #    Also pass detected_category for category context (Phase 6.4)
    recommendations = generate_recommendations(
        enhanced_products, market, intent, detected_category
    )

    # 6.5 Add explanations and strengths/weaknesses
    recommended_ids = {}
    if recommendations.best_overall:
        recommended_ids[recommendations.best_overall.product_id] = "best_overall"
    if recommendations.best_value:
        recommended_ids[recommendations.best_value.product_id] = "best_value"
    if recommendations.cheapest:
        recommended_ids[recommendations.cheapest.product_id] = "cheapest"
    if recommendations.highest_rated:
        recommended_ids[recommendations.highest_rated.product_id] = "highest_rated"
    if recommendations.premium_pick:
        recommended_ids[recommendations.premium_pick.product_id] = "premium_pick"
    if recommendations.hidden_gem:
        recommended_ids[recommendations.hidden_gem.product_id] = "hidden_gem"

    for product in enhanced_products:
        product.analysis = analyze_strengths_weaknesses(product, market, intent)
        if product.product_id in recommended_ids:
            product.recommendation_explanation = explain_recommendation(
                product, market, intent, recommended_ids[product.product_id]
            )

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
        confidence=confidence,
        search_used_fallback=fallback_used if fallback_used else None,
    )
