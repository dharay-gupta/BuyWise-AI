from app.schemas.intelligence import EnhancedProduct, MarketStats, SearchIntent, ExplanationFactor, RecommendationExplanation

def explain_recommendation(product: EnhancedProduct, market: MarketStats, intent: SearchIntent, recommendation_category: str) -> RecommendationExplanation:
    factors = []
    
    # Price
    if product.extracted_price is not None and market.median_price is not None:
        if product.extracted_price < market.median_price:
            factors.append(ExplanationFactor(
                name="Price Advantage",
                observation=f"₹{product.extracted_price:,.0f} is below the observed market median of ₹{market.median_price:,.0f}.",
                interpretation="Offers savings compared to typical prices in the observed results.",
                strength="strong" if product.extracted_price < market.median_price * 0.8 else "moderate"
            ))
        elif product.extracted_price > market.median_price:
            factors.append(ExplanationFactor(
                name="Premium Pricing",
                observation=f"₹{product.extracted_price:,.0f} is above the observed market median of ₹{market.median_price:,.0f}.",
                interpretation="Priced higher than typical results, possibly indicating premium features or brand.",
                strength="moderate"
            ))

    # Rating
    if product.rating is not None:
        if product.rating >= 4.5:
            factors.append(ExplanationFactor(
                name="Rating Strength",
                observation=f"Observed rating: {product.rating}/5.",
                interpretation="High average rating based on observed reviews.",
                strength="strong"
            ))
        elif product.rating >= 4.0:
            factors.append(ExplanationFactor(
                name="Solid Rating",
                observation=f"Observed rating: {product.rating}/5.",
                interpretation="Good average rating based on observed reviews.",
                strength="moderate"
            ))

    # Budget Fit
    if intent.budget_max is not None and product.extracted_price is not None:
        if product.extracted_price <= intent.budget_max:
            factors.append(ExplanationFactor(
                name="Budget Fit",
                observation=f"Priced at ₹{product.extracted_price:,.0f}.",
                interpretation=f"Fits well within your stated ₹{intent.budget_max:,.0f} budget.",
                strength="strong"
            ))

    # Review Evidence
    if product.reviews is not None:
        if product.reviews > 1000:
            factors.append(ExplanationFactor(
                name="Strong Review Evidence",
                observation=f"Based on {product.reviews} observed reviews.",
                interpretation="High confidence in the rating due to a large number of reviews.",
                strength="strong"
            ))
        elif product.reviews < 50:
            factors.append(ExplanationFactor(
                name="Limited Review Evidence",
                observation=f"The product has relatively few observed reviews ({product.reviews}).",
                interpretation="Confidence in the rating is lower due to limited data.",
                strength="weak"
            ))

    # BuyWise Score
    if product.buywise_score is not None:
        if product.buywise_score >= 80:
            factors.append(ExplanationFactor(
                name="Strong BuyWise Score",
                observation=f"BuyWise Score: {product.buywise_score:.1f}/100.",
                interpretation="Demonstrates a strong balance of price, rating, and market position.",
                strength="strong"
            ))

    category_summaries = {
        "best_overall": "BuyWise recommends this as Best Overall because it offers the strongest balance of price, rating, and review confidence among observed results.",
        "best_value": "BuyWise recommends this as Best Value because its observed price is below the market median while maintaining a solid rating and review evidence.",
        "cheapest": "BuyWise recommends this as the Cheapest option because it has the lowest valid price among observed results.",
        "highest_rated": "BuyWise recommends this as Highest Rated because it has the best combination of rating and review count among observed results.",
        "premium_pick": "BuyWise recommends this as a Premium Pick because it offers high ratings despite being priced above the market median.",
        "hidden_gem": "BuyWise recommends this as a Hidden Gem because it maintains a high rating despite having fewer observed reviews."
    }
    
    summary = category_summaries.get(recommendation_category, "BuyWise recommends this product based on observed market data.")
    
    return RecommendationExplanation(
        summary=summary,
        factors=factors,
        confidence_note="Based on current observed market data.",
        data_sources=["Google Shopping"]
    )
