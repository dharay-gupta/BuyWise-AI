import re
from app.schemas.intelligence import SearchIntent


def parse_intent(query: str) -> SearchIntent:
    """
    Parses a natural language search query to extract budget constraints,
    priority, and clean product query.

    Supports patterns like:
        "wireless headphones under 3000"
        "best headphones below ₹5000"
        "cheap gaming mouse"
        "premium laptop under 80000"
        "best value earbuds under 2000"
        "quality first headphones under 5000"
        "between 1000 and 5000"
        "Rs 5000", "Rs. 5000", "5k", "1 lakh"
    """
    budget_min = None
    budget_max = None
    priority = "balanced"
    keywords = []

    query_lower = query.lower()

    # -----------------------------------------------------------------------
    # 1. Budget number extraction helper
    # -----------------------------------------------------------------------
    def extract_number(val_str: str) -> float:
        val_str = (
            val_str.replace(",", "")
            .replace("₹", "")
            .replace("rs.", "")
            .replace("rs", "")
            .strip()
        )
        multiplier = 1.0
        if val_str.endswith("k"):
            val_str = val_str[:-1]
            multiplier = 1000.0
        elif "lakh" in val_str:
            val_str = val_str.replace("lakh", "").strip()
            multiplier = 100_000.0
        return float(val_str.strip()) * multiplier

    # Regex for currency/number formats (handles ₹, Rs, Rs., k, lakh)
    num_pattern = r"(?:₹|rs\.?\s*)?[\d]+(?:,\d+)*(?:\.\d+)?(?:\s*k|\s*lakh)?"

    # -----------------------------------------------------------------------
    # 2. Budget constraint parsing
    # -----------------------------------------------------------------------
    # Between X and Y
    between_match = re.search(
        fr"between\s+({num_pattern})\s+and\s+({num_pattern})", query_lower
    )
    if between_match:
        try:
            budget_min = extract_number(between_match.group(1))
            budget_max = extract_number(between_match.group(2))
        except ValueError:
            pass
    else:
        # Under / Below / Less than / Within
        under_match = re.search(
            fr"(?:under|below|less\s+than|within|upto|up\s+to)\s+({num_pattern})",
            query_lower,
        )
        if under_match:
            try:
                budget_max = extract_number(under_match.group(1))
            except ValueError:
                pass

        # "above X" or "more than X" → budget_min
        above_match = re.search(
            fr"(?:above|more\s+than|over|starting\s+from)\s+({num_pattern})",
            query_lower,
        )
        if above_match:
            try:
                budget_min = extract_number(above_match.group(1))
            except ValueError:
                pass

    # -----------------------------------------------------------------------
    # 3. Priority / Decision mode parsing
    # -----------------------------------------------------------------------
    # Order matters — more specific phrases first.
    # Use word-boundary regex for short words to avoid false matches
    # (e.g. 'top' inside 'laptop', 'laptop', 'best' inside 'best value').
    def _has_word(word: str) -> bool:
        return bool(re.search(fr"\b{re.escape(word)}\b", query_lower))

    if any(phrase in query_lower for phrase in ["quality first", "quality-first"]):
        priority = "quality_first"
    elif any(phrase in query_lower for phrase in ["best value", "value for money"]):
        priority = "best_value"
    elif any(_has_word(w) for w in ["cheap", "cheapest", "budget", "affordable"]):
        priority = "cheap"
    elif any(phrase in query_lower for phrase in ["lowest price"]):
        priority = "cheap"
    elif any(phrase in query_lower for phrase in ["premium", "luxury", "high-end", "top of the line"]):
        priority = "premium"
    elif any(phrase in query_lower for phrase in ["highest rated", "top rated", "best rated"]):
        priority = "highest_rated"
    elif any(_has_word(w) for w in ["best", "quality", "top"]):
        priority = "highest_rated"

    # -----------------------------------------------------------------------
    # 4. Clean product query (remove budget/priority phrases)
    # -----------------------------------------------------------------------
    clean_query = query_lower

    # Strip budget expressions
    clean_query = re.sub(
        r"(?:under|below|less\s+than|within|upto|up\s+to)\s+" + num_pattern,
        "",
        clean_query,
    )
    clean_query = re.sub(
        r"between\s+" + num_pattern + r"\s+and\s+" + num_pattern,
        "",
        clean_query,
    )
    clean_query = re.sub(
        r"(?:above|more\s+than|over|starting\s+from)\s+" + num_pattern,
        "",
        clean_query,
    )
    # Strip standalone ₹/Rs amounts
    clean_query = re.sub(r"₹\s*\d+(?:,\d+)*(?:\.\d+)?", "", clean_query)
    clean_query = re.sub(r"rs\.?\s*\d+(?:,\d+)*(?:\.\d+)?", "", clean_query)

    # Strip priority/qualifier words
    for phrase in [
        "quality first", "quality-first", "best value", "value for money",
        "highest rated", "top rated", "best rated",
    ]:
        clean_query = clean_query.replace(phrase, "")
    for word in ["cheap", "cheapest", "budget", "affordable", "premium", "luxury", "best", "quality", "top"]:
        clean_query = re.sub(fr"\b{word}\b", "", clean_query)

    clean_query = re.sub(r"\s+", " ", clean_query).strip()

    # -----------------------------------------------------------------------
    # 5. Keyword extraction (simple, no stop words)
    # -----------------------------------------------------------------------
    stop_words = {"the", "a", "an", "and", "or", "for", "with", "in", "on", "at", "of"}
    raw_words = [w for w in clean_query.split() if w not in stop_words and len(w) > 1]
    keywords = raw_words

    # -----------------------------------------------------------------------
    # 6. Category and Use Case Extraction
    # -----------------------------------------------------------------------
    category = None
    use_case_signals = []

    categories = {
        "laptop": ["laptop"],
        "phone": ["phone", "smartphone"],
        "headphone": ["headphone", "headphones"],
        "earbud": ["earbud", "earbuds", "earphones"],
        "camera": ["camera", "cameras"],
        "watch": ["watch", "watches", "smartwatch"],
        "monitor": ["monitor"],
        "mouse": ["mouse", "mice"],
        "keyboard": ["keyboard"],
        "tablet": ["tablet", "tablets"],
        "tv": ["tv", "television", "televisions"],
        "speaker": ["speaker", "speakers"]
    }

    for cat_name, syns in categories.items():
        if any(_has_word(phrase) for phrase in syns):
            category = cat_name
            break
            
    use_cases = {
        "gaming": ["gaming", "gamer"],
        "photography": ["photography", "camera", "photos", "vlogging"],
        "coding": ["coding", "programming", "developer"],
        "fitness": ["fitness", "gym", "running", "workout"],
        "office": ["office", "work", "business"],
        "travel": ["travel", "traveling", "commute", "noise cancelling"]
    }

    for uc, syns in use_cases.items():
        if any(phrase in query_lower for phrase in syns):
            use_case_signals.append(uc)

    return SearchIntent(
        product_query=clean_query if clean_query else query,
        category=category,
        use_case_signals=use_case_signals,
        budget_min=budget_min,
        budget_max=budget_max,
        priority=priority,
        keywords=keywords,
    )
