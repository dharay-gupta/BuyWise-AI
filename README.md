# BuyWise AI — Smarter Purchase Decisions

> **SerpApi India Hackathon 2026 — Commerce & Market Intelligence Track**  

> *"From Search Results to Smarter Decisions."*

BuyWise AI is a Commerce & Market Intelligence platform that transforms live Google Shopping results from **SerpApi** into actionable, explainable purchase decisions. Rather than presenting raw, unranked product feeds with unverified promotional claims, BuyWise AI parses shopper intent, models observed market price distributions, evaluates deal authenticity against observed market medians, cross-references multi-merchant offers, and provides transparent recommendations tailored to user priorities.

---

## 1. Problem Statement & Overview

### The Problem

When shopping online, consumers face overwhelming product listings saturated with sponsored placements, fluctuating prices, and unverified discount claims ("50% off" from an inflated anchor price). Shoppers are forced to manually:

1. Search across multiple stores to check if an item is genuinely well-priced.

2. Determine whether a product fits their actual budget and intended use case.

3. Weigh trade-offs between price competitiveness, rating quality, and review volume.

4. Distinguish between merchant-advertised marketing claims and objective market reality.

### The BuyWise Solution

BuyWise AI acts as an objective decision co-pilot:

- **Evidence-Based Intelligence**: Computes transparent metrics strictly from live observed market data returned by SerpApi.

- **Explainable Scoring**: Uses deterministic multi-criteria scoring algorithms with four user-selectable decision modes—no LLM hallucinations or opaque black-box recommendations.

- **Deal & Cross-Merchant Analysis**: Checks advertised discounts against the observed market median and identifies price spreads when identical products are listed across multiple merchants.

---

## 2. Key Features

### 🧠 Search Intent & Budget Extraction

- Extracts clean product keywords and eliminates conversational search noise.

- Detects budget constraints from natural language queries (e.g., `"under ₹5000"`, `"between 10k and 25k"`, `"less than Rs. 3000"`).

- Identifies product categories (laptops, phones, headphones, monitors, etc.) and use-case signals (gaming, office, fitness, coding, travel).

- Surfaces all extracted parameters in the **BuyWise Understood** dashboard panel.

### ⚖️ Four Distinct Decision Modes

Scoring weights adapt dynamically to the user's shopping goals:

- **⚖️ Balanced** **(Default)**: Price 35% · Rating 30% · Review Confidence 15% · Market Position 20%

- **💰 Cheapest**: Price 60% · Market Position 25% · Rating 10% · Review Confidence 5%

- **🔥 Best Value**: Price 40% · Rating 30% · Review Confidence 15% · Market Position 15%

- **👑 Quality First**: Rating 45% · Review Confidence 30% · Market Position 15% · Price 10%

### 🏆 Explainable Top Picks & Analysis

- **Categorized Picks**: Best Overall, Best Value, Cheapest, Highest Rated, Premium Pick, and Hidden Gem.

- **Explainable Recommendation Factors**: Every top pick details **why** it was selected, citing exact price advantages, rating thresholds, budget fit, and review confidence.

- **Strengths & Weaknesses**: Auto-generated product trade-off breakdown highlighting advantages (e.g., **17% below market median**, **Strong review evidence**) and potential drawbacks (e.g., **Limited review volume**, **Exceeds stated budget**).

### 🏷️ Deal Quality & Budget Headroom

- Calculates advertised discount percentages only when positive current and old prices are available and comparable.

- Assigns a BuyWise Deal Assessment (`Strong Deal`, `Moderate Deal`, or `Minimal Discount`) based on the discount size relative to the observed market median.

- Calculates exact **Budget Headroom** (e.g., `₹500 under budget (25% remaining)` or `₹1,200 over budget`).

### 🏪 Cross-Merchant Price Intelligence

- Groups offers sharing the verified Google Shopping `product_id` across distinct merchants.

- Identifies the lowest observed merchant offer, total price spread across stores, and percentage savings versus the highest listing.

- Renders an interactive multi-merchant offer breakdown in the product detail modal.

### 📊 Market & Merchant Analytics

- **Visual Price Position Gauge**: Color-coded percentile gauge positioning every product as **Below Median**, **Near Median**, or **Above Median** across the observed results.

- **Interactive Visualizations (Chart.js)**: Observed price distribution histogram and price-versus-rating scatter plot.

- **Merchant Intelligence**: Summary of observed listings count, average observed price, and lowest observed price per marketplace.

### 🎯 Interactive Consumer Tools

- **Smart Filters**: Filter by maximum price, minimum star rating, merchant store, and recommendation tags; sort by score, price, rating, or reviews.

- **Side-by-Side Product Comparison**: Compare up to 3 selected products across attributes in a comparative matrix.

- **Product Detail Modal**: Deep-dive view consolidating specifications, SerpApi marketplace badges, delivery notes, deal ratings, score breakdowns, and merchant offers.

---

## 3. Architecture & Tech Stack

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend (Vanilla JS)                 │
│        Bootstrap 5 · Chart.js · Responsive Glassmorphism    │
└──────────────────────────────▲──────────────────────────────┘
                               │ HTTP / JSON (Port 5500 → 8000)
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend (Python)                 │
│   Routes (/api/search, /api/health) · Pydantic Schemas     │
└──────────────────────────────▲──────────────────────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
┌─────────────────────────────┐         ┌─────────────────────────────┐
│  SerpApi Integration Client │         │  BuyWise Intelligence Core  │
│  - Google Shopping Engine   │         │  - Intent Parser            │
│  - Normalization Layer      │         │  - Market & Merchant Stats  │
│  - Defensive Type Casting   │         │  - Deterministic Scorer     │
└─────────────────────────────┘         │  - Deal Quality Analyzer    │
                                        │  - Cross-Merchant Grouper   │
                                        │  - Recommendation Explainer │
                                        └─────────────────────────────┘
```

- **Backend**: Python 3.10+, FastAPI, Uvicorn, Pydantic v2, Pydantic-Settings, `serpapi` (official client), HTTPX.

- **Frontend**: Vanilla JavaScript (ES6+, strict mode, no heavy frameworks), HTML5, CSS3 with custom design tokens, Bootstrap 5.3, Chart.js.

- **Testing**: Pytest, Pytest-Asyncio.

---

## 4. Prerequisites

- **Operating System**: Windows 10/11, macOS, or Linux.

- **Python**: Version 3.10 or higher (tested and verified on Python 3.14).

- **SerpApi API Key**: An active API key from [SerpApi]\(https\://serpapi.com/) (free tier includes 100 searches/month).

- **Web Browser**: Modern Chromium, Firefox, or Safari browser.

---

## 5. Local Setup & Installation (Windows)

### Step 1: Clone or Open the Repository

```
powershell
cd C:\Users\hp\OneDrive\Desktop\BuyWise-AI
```

### Step 2: Create and Activate a Virtual Environment

```
powershell
\# Create virtual environment
python -m venv venv
\# Activate virtual environment in PowerShell
.\venv\Scripts\Activate.ps1
\# Or in Command Prompt:
\# venv\Scripts\activate.bat
```

### Step 3: Install Dependencies

```
powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Copy `.env.example` to `backend/.env`:

```
powershell
Copy-Item .env.example backend\.env
```

Open `backend/.env` in an editor and set your SerpApi API key:

```env
SERPAPI_API_KEY=your_serpapi_key_here
ENVIRONMENT=development
DATABASE_URL=sqlite:///../data/buywise.db
```

---

## 6. Running the Application

The frontend and backend run as decoupled services. Open **two separate terminal windows**.

### Terminal 1: Start the Backend API

```
powershell
cd C:\Users\hp\OneDrive\Desktop\BuyWise-AI\backend
..\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

- The backend API will be available at: **`http\://127.0.0.1:8000`**

- Interactive Swagger API docs: **`http\://127.0.0.1:8000/docs`**

### Terminal 2: Serve the Frontend

```
powershell
cd C:\Users\hp\OneDrive\Desktop\BuyWise-AI\frontend
python -m http.server 5500
```

- Open your browser and navigate to: **`http\://127.0.0.1:5500`**

**(Alternatively, you can open `frontend/index.html` using the VS Code Live Server extension on port 5500).**

---

## 7. API Endpoints & Usage

### 1. Health Check

- **Endpoint**: `GET /api/health`

- **Response**:

```
json
{
  "status": "healthy",
  "service": "BuyWise AI API"
}
```

### 2. Intelligent Commerce Search

- **Endpoint**: `GET /api/search`

- **Query Parameters**:

  - `q` **(required)**: Natural language product search query (e.g., `wireless headphones under 5000`).

  - `mode` **(optional, default: `balanced`)**: One of `balanced`, `cheapest`, `best_value`, `quality_first`.

#### Example Request:

```
http
GET http\://127.0.0.1:8000/api/search?q=wireless+headphones+under+5000&mode=balanced
```

#### Example Response Structure:

```
json
{
  "query": "wireless headphones under 5000",
  "count": 24,
  "decision_mode": "balanced",
  "intent": {
    "product_query": "wireless headphones",
    "category": "headphone",
    "use_case_signals": [],
    "budget_min": null,
    "budget_max": 5000.0,
    "priority": "balanced"
  },
  "market": {
    "products_analyzed": 24,
    "valid_prices_count": 24,
    "valid_ratings_count": 22,
    "lowest_price": 1499.0,
    "highest_price": 4999.0,
    "average_price": 2845.5,
    "median_price": 2499.0,
    "price_spread": 3500.0
  },
  "recommendations": {
    "best_overall": { "category": "Best Overall", "product_id": "...", "reason": "..." },
    "best_value": { "category": "Best Value", "product_id": "...", "reason": "..." },
    "cheapest": { "category": "Cheapest", "product_id": "...", "reason": "..." },
    "highest_rated": { "category": "Highest Rated", "product_id": "...", "reason": "..." },
    "premium_pick": { "category": "Premium Pick", "product_id": "...", "reason": "..." },
    "hidden_gem": { "category": "Hidden Gem", "product_id": "...", "reason": "..." }
  },
  "products": [
    {
      "title": "Sample Wireless Headphone",
      "product_id": "12345",
      "product_link": "https\://...",
      "source": "Amazon",
      "price": "₹1,999",
      "extracted_price": 1999.0,
      "old_price": "₹2,999",
      "extracted_old_price": 2999.0,
      "rating": 4.4,
      "reviews": 1820,
      "buywise_score": 84.6,
      "price_percentile": 14.3,
      "deal_info": {
        "discount_pct": 33.3,
        "deal_quality": "strong",
        "budget_headroom": "₹3,001 under budget (60% remaining)",
        "budget_utilisation_pct": 40.0
      },
      "cross_merchant": {
        "merchant_count": 2,
        "lowest_price": 1999.0,
        "highest_price": 2499.0,
        "best_merchant": "Amazon",
        "price_spread": 500.0,
        "savings_vs_highest": "₹500 price spread across 2 merchants (20%)",
        "merchants": [
          { "merchant": "Amazon", "price": 1999.0, "is_lowest": true },
          { "merchant": "Flipkart", "price": 2499.0, "is_lowest": false }
        ]
      }
    }
  ]
}
```

---

## 8. Test Suite & Verification

The test suite runs against mocked data structures to ensure zero quota consumption during automated testing.

### Running Tests

From the project root:

```
powershell
.\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

### Current Test Status

**Latest verified result: 186 passed, 0 failed, 1 warning in 1.57 seconds.**

The automated test suite uses mocked data structures to avoid consuming SerpApi quota during testing.

The warning is a Starlette deprecation notice related to the test client's `httpx` integration.

---

## 9. Project Structure

```
BuyWise-AI/
├── .env.example                       # Example environment variables template
├── .gitignore                         # Git ignore definitions (ignores .env, venv, caches)
├── README.md                          # Project documentation
├── requirements.txt                   # Production and testing Python dependencies
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                  # Pydantic Settings configuration loader
│   │   ├── main.py                    # FastAPI application, CORS middleware, route registration
│   │   ├── intelligence/              # BuyWise Intelligence Core
│   │   │   ├── cross_merchant.py      # Cross-merchant offer grouping and spread calculations
│   │   │   ├── deal_analysis.py       # Discount calculation and deal quality classification
│   │   │   ├── explainer.py           # Recommendation rationale factor generator
│   │   │   ├── intent_parser.py       # Natural language regex budget and intent extraction
│   │   │   ├── market_analysis.py     # Median, spread, and price distribution statistics
│   │   │   ├── market_insight.py      # Natural language market insights
│   │   │   ├── merchant_analysis.py   # Observed marketplace distribution aggregator
│   │   │   ├── normalization.py       # SerpApi raw shopping results normalizer
│   │   │   ├── recommendations.py     # Top picks selector across 6 categories
│   │   │   ├── scoring.py             # Deterministic BuyWise score calculation (4 modes)
│   │   │   ├── strengths_weaknesses.py# Product-level pros and cons analyzer
│   │   │   └── tradeoffs.py           # Market trade-off and savings text generator
│   │   ├── routes/
│   │   │   ├── health.py              # Health check endpoint
│   │   │   └── search.py              # Enriched search router
│   │   ├── schemas/
│   │   │   ├── intelligence.py        # Pydantic models for intelligence responses
│   │   │   └── product.py             # Normalized product and search schemas
│   │   └── services/
│   │       ├── intelligence_service.py# Master pipeline orchestrator
│   │       ├── search_service.py      # Search coordinator
│   │       └── serpapi_client.py      # Official SerpApi Google Shopping client
│   └── tests/                         # Automated test suite (186 tests in the latest verified run)
│
└── frontend/
    ├── index.html                     # Single-page application markup
    ├── css/
    │   └── style.css                  # Custom styling, dark glassmorphism, design tokens
    └── js/
        └── main.js                    # Vanilla JavaScript state management, API calls, DOM rendering
```

**Local configuration:** During setup, create `backend/.env` from `.env.example` and add your own SerpApi API key. This file is local-only, ignored by Git, and must never be committed to the public repository.

---

## 10. Security & API Key Precautions

- **Server-Side Key Isolation**: All calls to SerpApi originate exclusively from the backend Python service (`serpapi_client.py`). The frontend never receives, stores, or transmits the `SERPAPI_API_KEY`.

- **Git Protection**: `.env` and `backend/.env` are strictly included in `.gitignore`. Never commit or push `.env` files to public or shared version control.

- **Input Sanitization**: The frontend performs strict HTML and attribute escaping (`escHtml`, `escAttr`) across all dynamic strings returned by external APIs to prevent Cross-Site Scripting (XSS).

---

## 11. Data Integrity & Limitations

BuyWise AI strictly prioritizes **data honesty**:

- **Observed Market Data Only**: All statistical figures (lowest price, highest price, median, spreads, ratings) reflect only the products returned by SerpApi for the specific user query. BuyWise makes no claims of universal market completeness.

- **No Inferred Sales Volume or Demand**: BuyWise does not fabricate private sales volume, inventory stock status, consumer demand trends, or merchant profit margins.

- **Advertised Discounts vs. Deal Verification**: Discount percentages reflect merchant-advertised anchor prices (`extracted_old_price`). BuyWise explicitly notes that advertised discounts are seller-stated and not independently audited historical sales prices.

- **Merchant Delivery Estimates**: Shipping and delivery text is presented strictly as merchant-stated information and does not represent an independent fulfillment guarantee.

---

## 12. AI-Use Disclosure

**In compliance with SerpApi India Hackathon 2026 guidelines:**

- **Development Tooling**: AI coding assistants were utilized as interactive pair-programmers during development for iterative refactoring, documentation structuring, and generating test cases.

- **Production Architecture**: The core BuyWise recommendation engine, scoring algorithms, deal evaluation, and intent extraction run entirely on **deterministic Python code and mathematical algorithms**. No generative LLM is invoked during user search requests, ensuring zero hallucinations, instantaneous response times, and consistent results.

---

## License

This project was built for the **SerpApi India Hackathon 2026**. Distributed under the MIT License.
