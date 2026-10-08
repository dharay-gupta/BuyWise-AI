from fastapi import APIRouter, Query, HTTPException
from app.schemas.intelligence import IntelligenceResponse
from app.services.intelligence_service import process_intelligent_search
from app.intelligence.scoring import ALLOWED_MODES

router = APIRouter()

VALID_MODES = ALLOWED_MODES  # {"balanced", "cheapest", "best_value", "quality_first"}


@router.get("/search", response_model=IntelligenceResponse)
def search_products(
    q: str = Query(..., description="The product search query"),
    mode: str = Query(
        default="balanced",
        description=(
            "Decision mode influencing scoring weights. "
            "One of: balanced, cheapest, best_value, quality_first"
        ),
    ),
):
    """
    Searches for live products based on the query and returns an enriched
    intelligence response with market analytics, recommendations, and insights.

    The ?mode= parameter controls which scoring weights are applied:
      - balanced      Price 35%, Rating 30%, Review Confidence 15%, Market Position 20%
      - cheapest      Price 60%, Rating 10%, Review Confidence 5%, Market Position 25%
      - best_value    Price 40%, Rating 30%, Review Confidence 15%, Market Position 15%
      - quality_first Rating 45%, Review Confidence 30%, Price 10%, Market Position 15%

    Business logic lives entirely in services/intelligence modules, not here.
    """
    # Validate mode — do not allow arbitrary scoring parameters
    if mode not in VALID_MODES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid decision mode '{mode}'. "
                f"Allowed values: {', '.join(sorted(VALID_MODES))}"
            ),
        )

    try:
        response = process_intelligent_search(q, mode=mode)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger_err = str(e)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during search.",
        )
