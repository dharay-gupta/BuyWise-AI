from app.schemas.intelligence import EnhancedProduct, MarketStats, SearchIntent, ProductAnalysis

def analyze_strengths_weaknesses(product: EnhancedProduct, market: MarketStats, intent: SearchIntent) -> ProductAnalysis:
    strengths = []
    weaknesses = []
    neutral = []
    
    # Price
    if product.extracted_price is not None and market.median_price is not None:
        diff = market.median_price - product.extracted_price
        pct = (diff / market.median_price) * 100
        if pct > 10:
            strengths.append(f"Price is {pct:.0f}% below the observed market median.")
        elif pct < -10:
            weaknesses.append(f"Price is {-pct:.0f}% above the observed market median.")
        else:
            neutral.append("Priced near the observed market median.")

    # Rating
    if product.rating is not None:
        if product.rating >= 4.5:
            strengths.append(f"High observed rating of {product.rating}/5.")
        elif product.rating < 4.0:
            weaknesses.append(f"Lower observed rating of {product.rating}/5.")
            
    # Reviews
    if product.reviews is not None:
        if product.reviews > 500:
            strengths.append(f"Strong review evidence with {product.reviews} observed reviews.")
        elif product.reviews < 50:
            weaknesses.append(f"Limited review evidence with only {product.reviews} observed reviews.")

    # Score
    if product.buywise_score is not None:
        if product.buywise_score >= 80:
            strengths.append(f"Strong BuyWise Score of {product.buywise_score:.1f}.")
        elif product.buywise_score < 50:
            weaknesses.append(f"Low BuyWise Score of {product.buywise_score:.1f}.")

    # Budget
    if intent.budget_max is not None and product.extracted_price is not None:
        if product.extracted_price > intent.budget_max:
            weaknesses.append(f"Exceeds stated budget of ₹{intent.budget_max:,.0f}.")
        elif product.extracted_price <= intent.budget_max:
            strengths.append(f"Fits within the stated budget of ₹{intent.budget_max:,.0f}.")

    return ProductAnalysis(
        strengths=strengths,
        weaknesses=weaknesses,
        neutral=neutral
    )
