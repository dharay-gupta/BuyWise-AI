"""
Category Detection — Phase 6.4 (Feature A)

Deterministically classifies a search into one of the supported broad categories.

Design rules:
- Uses the original query, parsed SearchIntent, and (optionally) product titles.
- Prefers strong, specific signals over weak keyword overlaps.
- Returns a clear fallback category when evidence is insufficient.
- Completely independent from BuyWise scoring.
- No SerpApi calls; no external I/O; pure deterministic logic.

Supported categories (broad taxonomy):
    electronics             — generic electronics that don't fit sub-categories
    computers_laptops       — laptops, desktops, PCs, notebooks
    mobile_phones           — smartphones, feature phones
    audio_accessories       — headphones, earphones, earbuds, speakers, microphones
    clothing                — shirts, t-shirts, jeans, dresses, tops, kurtas, etc.
    footwear                — shoes, boots, sandals, sneakers, slippers
    home_kitchen            — appliances, cookware, furniture, home decor
    beauty_personal_care    — skincare, haircare, makeup, grooming
    sports_fitness          — gym equipment, sportswear (not shoes specifically),
                              fitness accessories
    other                   — insufficient or ambiguous evidence
"""

import re
from typing import List, Optional, Sequence

from app.schemas.intelligence import SearchIntent


# ---------------------------------------------------------------------------
# Category label constants — single source of truth
# ---------------------------------------------------------------------------

CAT_ELECTRONICS = "electronics"
CAT_COMPUTERS = "computers_laptops"
CAT_MOBILE = "mobile_phones"
CAT_AUDIO = "audio_accessories"
CAT_CLOTHING = "clothing"
CAT_FOOTWEAR = "footwear"
CAT_HOME = "home_kitchen"
CAT_BEAUTY = "beauty_personal_care"
CAT_SPORTS = "sports_fitness"
CAT_OTHER = "other"

# Human-readable display labels
CATEGORY_LABELS = {
    CAT_ELECTRONICS: "Electronics",
    CAT_COMPUTERS: "Computers & Laptops",
    CAT_MOBILE: "Mobile Phones",
    CAT_AUDIO: "Audio & Accessories",
    CAT_CLOTHING: "Clothing",
    CAT_FOOTWEAR: "Footwear",
    CAT_HOME: "Home & Kitchen",
    CAT_BEAUTY: "Beauty & Personal Care",
    CAT_SPORTS: "Sports & Fitness",
    CAT_OTHER: "Other / Unknown",
}

# ---------------------------------------------------------------------------
# Keyword maps — ordered from most-specific to most-generic within each group.
# Each entry is (category_constant, set_of_trigger_words).
# A word must appear as a standalone word-boundary token to match.
# ---------------------------------------------------------------------------

# Ordered priority list: earlier entries win over later ones.
_ORDERED_RULES: List[tuple] = [
    # — Computers & Laptops —
    (CAT_COMPUTERS, {
        "laptop", "laptops", "notebook", "notebooks", "chromebook",
        "macbook", "ultrabook", "desktop", "pc", "computer",
        "gaming laptop", "gaming pc",
    }),

    # — Mobile Phones —
    (CAT_MOBILE, {
        "smartphone", "smartphones", "mobile phone", "mobile phones",
        "iphone", "android phone", "5g phone", "feature phone",
        # bare "phone" handled separately (lower weight) below
    }),

    # — Audio & Accessories —
    (CAT_AUDIO, {
        "headphone", "headphones", "earphone", "earphones",
        "earbud", "earbuds", "tws", "in-ear", "over-ear",
        "on-ear", "neckband", "speaker", "speakers",
        "bluetooth speaker", "soundbar", "microphone",
        "noise cancelling", "noise canceling",
    }),

    # — Clothing —
    (CAT_CLOTHING, {
        "shirt", "shirts", "t-shirt", "t-shirts", "tshirt", "tshirts",
        "jeans", "trousers", "pants", "dress", "dresses",
        "kurta", "kurtas", "saree", "sari", "top", "tops",
        "hoodie", "hoodies", "jacket", "jackets", "suit", "suits",
        "blazer", "blazers", "skirt", "skirts", "legging", "leggings",
        "shorts", "sweater", "sweaters", "sweatshirt",
        "polo", "polo shirt", "track pant", "track pants", "tracksuit",
    }),

    # — Footwear —
    (CAT_FOOTWEAR, {
        "shoe", "shoes", "boot", "boots", "sneaker", "sneakers",
        "sandal", "sandals", "slipper", "slippers", "loafer", "loafers",
        "heel", "heels", "pump", "pumps", "flip flop", "flip flops",
        "running shoe", "running shoes", "sports shoe", "sports shoes",
        "formal shoe", "formal shoes", "casual shoe", "casual shoes",
    }),

    # — Home & Kitchen —
    (CAT_HOME, {
        "refrigerator", "fridge", "washing machine", "air conditioner",
        "ac", "microwave", "oven", "mixer", "blender", "juicer",
        "pressure cooker", "cookware", "kitchen", "utensil", "utensils",
        "bed", "mattress", "sofa", "chair", "table", "furniture",
        "lamp", "fan", "air purifier", "vacuum cleaner", "iron",
        "water purifier", "ro", "geyser", "water heater",
        "curtain", "curtains", "pillow", "cushion",
    }),

    # — Beauty & Personal Care —
    (CAT_BEAUTY, {
        "face wash", "moisturiser", "moisturizer", "sunscreen",
        "foundation", "lipstick", "mascara", "eyeshadow",
        "perfume", "deodorant", "shampoo", "conditioner",
        "hair oil", "face mask", "serum", "toner",
        "trimmer", "razor", "shaving", "grooming",
        "makeup", "skincare", "haircare", "nail polish",
        "concealer", "blush", "highlighter",
    }),

    # — Sports & Fitness —
    (CAT_SPORTS, {
        "dumbbell", "dumbbells", "barbell", "kettlebell",
        "resistance band", "yoga mat", "treadmill", "cycle",
        "cycling", "gym", "protein powder", "whey protein",
        "fitness tracker", "sports bottle", "water bottle",
        "badminton", "cricket bat", "football", "basketball",
        "tennis racket", "skipping rope",
    }),

    # — Electronics (broad fallback) —
    (CAT_ELECTRONICS, {
        "monitor", "keyboard", "mouse", "webcam", "printer",
        "scanner", "projector", "tablet", "smartwatch", "watch",
        "camera", "lens", "tripod", "drone", "router", "modem",
        "hard drive", "ssd", "pendrive", "usb hub",
        "graphics card", "gpu", "cpu", "processor", "ram",
        "tv", "television", "led tv", "oled tv",
        "gaming chair", "gaming headset", "gamepad", "joystick",
        "power bank", "charger", "cable",
        "earphone",  # duplicated from audio, but electronics is lower priority
    }),
]

# Single-word signals that carry moderate evidence (word boundary match)
_SINGLE_WORD_SIGNALS = {
    "phone": CAT_MOBILE,       # "phone" alone has decent signal
    "mobile": CAT_MOBILE,
    "headset": CAT_AUDIO,
    "audio": CAT_AUDIO,
    "apparel": CAT_CLOTHING,
    "clothing": CAT_CLOTHING,
    "wear": CAT_CLOTHING,      # footwear / sportswear / menswear etc handled in multi-word
    "dress": CAT_CLOTHING,
    "fashion": CAT_CLOTHING,
    "footwear": CAT_FOOTWEAR,
    "appliance": CAT_HOME,
    "cosmetic": CAT_BEAUTY,
    "cosmetics": CAT_BEAUTY,
    "beauty": CAT_BEAUTY,
    "fitness": CAT_SPORTS,
    "sport": CAT_SPORTS,
    "electronic": CAT_ELECTRONICS,
    "electronics": CAT_ELECTRONICS,
    "gadget": CAT_ELECTRONICS,
}


def _words_in_text(text: str) -> set:
    """Return lowercase word-boundary tokens from text."""
    return set(re.findall(r"\b\w[\w\-]*\b", text.lower()))


def _phrase_in_text(phrase: str, text: str) -> bool:
    """Return True when `phrase` appears as a whole-word sequence in text."""
    # Escape phrase and anchor with word boundaries
    pattern = r"\b" + re.escape(phrase.lower()) + r"\b"
    return bool(re.search(pattern, text.lower()))


def detect_category(
    query: str,
    intent: Optional[SearchIntent] = None,
    product_titles: Optional[Sequence[str]] = None,
) -> str:
    """
    Deterministically returns one of the CATEGORY_* constants.

    Priority order:
    1. intent.category (from existing intent parser) — used as a strong signal
       but mapped to the broader Phase 6.4 taxonomy.
    2. Multi-word phrase matching against the query text.
    3. Single-word signal matching against the query text.
    4. Majority vote from product titles (top 10), if provided and unambiguous.
    5. Fallback: CAT_OTHER.

    Args:
        query:          Original user query (raw string).
        intent:         Optional parsed SearchIntent; provides category/keywords.
        product_titles: Optional sequence of product title strings from
                        normalized results. Used for secondary evidence only.

    Returns:
        One of the CAT_* string constants.
    """
    query_lower = query.lower().strip()

    # ------------------------------------------------------------------
    # 1. Map intent.category → broad category (strong signal)
    # ------------------------------------------------------------------
    if intent is not None and intent.category:
        mapped = _intent_category_to_broad(intent.category)
        if mapped != CAT_OTHER:
            return mapped

    # ------------------------------------------------------------------
    # 2. Multi-word phrase matching against the full query
    # ------------------------------------------------------------------
    for category, phrase_set in _ORDERED_RULES:
        for phrase in phrase_set:
            if " " in phrase:
                # Multi-word: use substring check with word boundaries
                if _phrase_in_text(phrase, query_lower):
                    return category
            else:
                # Single-word: use whole-word token match
                if _phrase_in_text(phrase, query_lower):
                    return category

    # ------------------------------------------------------------------
    # 3. Single-word weak signals against the full query
    # ------------------------------------------------------------------
    query_tokens = _words_in_text(query_lower)
    for signal_word, category in _SINGLE_WORD_SIGNALS.items():
        if signal_word in query_tokens:
            return category

    # ------------------------------------------------------------------
    # 4. Product-title majority vote (top 10 titles, optional)
    # ------------------------------------------------------------------
    if product_titles:
        votes: dict = {}
        for title in list(product_titles)[:10]:
            cat = _classify_title(title)
            if cat != CAT_OTHER:
                votes[cat] = votes.get(cat, 0) + 1

        if votes:
            # Only accept a clear majority (> 40% of sampled titles)
            sample_size = min(len(product_titles), 10)
            best_cat = max(votes, key=lambda k: votes[k])
            if votes[best_cat] / sample_size > 0.4:
                return best_cat

    return CAT_OTHER


def _classify_title(title: str) -> str:
    """
    Classify a single product title using the same ordered rules.
    Returns CAT_OTHER when no reliable match is found.
    Helper for the product-title majority-vote step.
    """
    if not title:
        return CAT_OTHER
    title_lower = title.lower()
    for category, phrase_set in _ORDERED_RULES:
        for phrase in phrase_set:
            if _phrase_in_text(phrase, title_lower):
                return category
    for signal_word, category in _SINGLE_WORD_SIGNALS.items():
        if _phrase_in_text(signal_word, title_lower):
            return category
    return CAT_OTHER


def _intent_category_to_broad(intent_cat: str) -> str:
    """
    Maps the fine-grained category strings from intent_parser.py to the
    broad Phase 6.4 taxonomy.

    intent_parser categories:
        laptop, phone, headphone, earbud, camera, watch,
        monitor, mouse, keyboard, tablet, tv, speaker
    """
    _MAP = {
        "laptop": CAT_COMPUTERS,
        "phone": CAT_MOBILE,
        "headphone": CAT_AUDIO,
        "earbud": CAT_AUDIO,
        "speaker": CAT_AUDIO,
        "camera": CAT_ELECTRONICS,
        "watch": CAT_ELECTRONICS,
        "monitor": CAT_ELECTRONICS,
        "mouse": CAT_ELECTRONICS,
        "keyboard": CAT_ELECTRONICS,
        "tablet": CAT_ELECTRONICS,
        "tv": CAT_ELECTRONICS,
    }
    return _MAP.get(intent_cat.lower(), CAT_OTHER)
