# BuyWise AI

"From Search Results to Smarter Decisions."

BuyWise AI is a Commerce & Market Intelligence platform that uses SerpApi as a meaningful core data source. It goes beyond simple price comparison by extracting user intent, normalizing live market data, and providing explainable recommendations through deterministic scoring.

## Architecture

This project is built using:
- **Backend**: Python, FastAPI, Pydantic, SQLite
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5

### Current Architecture (Phase 3)
- `backend/app/services/serpapi_client.py`: Client for integrating live Google Shopping data using the official `serpapi` package.
- `backend/app/intelligence/`: A suite of deterministic modules extracting intent, market medians, trade-off explanations, and deriving a fair BuyWise Score without resorting to LLM fabrication.
- `backend/app/services/intelligence_service.py`: Orchestrates fetching search data and running the intelligence modules in one pass.
- `backend/app/routes/search.py`: Endpoint providing backwards compatible but enriched search capabilities.
- `frontend/`: Dashboard featuring Top Picks, dynamic intent parsing UI, score badges, and Chart.js market distribution graphs.

## Local Setup

1. **Clone/Navigate to the repository**
   Navigate to the `BuyWise-AI` folder.

2. **Set up Environment Variables**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Add your SerpApi key to the `.env` file (never commit this file!). 
   **Note on API Key:** To obtain a key, sign up at [SerpApi](https://serpapi.com/) and place it in the `SERPAPI_API_KEY` variable.

3. **Install Dependencies**
   It's recommended to use a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run the Backend**
   Navigate to the `backend` directory and run:
   ```bash
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://localhost:8000`. 
   - **Health Check**: `GET /api/health`
   - **Search API**: `GET /api/search?q=query`

5. **Run the Frontend**
   Simply open `frontend/index.html` in a web browser. Search queries entered on the interface will now use live commerce data.

## Testing

Tests use mocked SerpApi data to prevent quota usage.
To run the backend tests, navigate to the `backend` directory and use pytest:
```bash
pytest
```

## Data Integrity Notice
BuyWise uses observed **live search/commerce data** and does not claim unavailable metrics such as sales volume, inventory, or demand unless those values are strictly returned by SerpApi or inferred (clearly labelled). Historical prices are based on observed market data and snapshots.
