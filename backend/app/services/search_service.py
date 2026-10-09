from app.services.serpapi_client import serpapi_client
from app.intelligence.normalization import normalize_shopping_results
from app.schemas.product import SearchResponse
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# Minimum usable product count before a fallback search is considered.
FALLBACK_THRESHOLD = 5


def perform_commerce_search(query: str) -> SearchResponse:
    """
    Coordinates searching live commerce data through SerpApi and normalizing it.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    # Optional check: excessively long query
    if len(query) > 200:
        raise HTTPException(status_code=400, detail="Search query is too long.")

    # 1. Fetch raw data from SerpApi
    raw_data = serpapi_client.search_google_shopping(query)

    # Extract shopping results list from response
    shopping_results = raw_data.get("shopping_results", [])

    if not shopping_results:
        logger.info(f"No shopping results found for query: '{query}'")
        # Do not throw an error; return an empty list gracefully
        return SearchResponse(query=query, count=0, products=[])

    # 2. Normalize data
    normalized_products = normalize_shopping_results(shopping_results)

    # 3. Construct response
    return SearchResponse(
        query=query,
        count=len(normalized_products),
        products=normalized_products
    )


def perform_commerce_search_with_fallback(
    original_query: str,
    fallback_query: str,
) -> tuple[SearchResponse, bool]:
    """
    Performs an initial search for ``original_query``.  If the result contains
    fewer than FALLBACK_THRESHOLD usable (normalized) products AND
    ``fallback_query`` is non-empty and distinct from ``original_query``, a
    single fallback search is attempted using ``fallback_query``.

    Returns
    -------
    (response, fallback_used)
        response       – A SearchResponse (always for ``original_query`` label).
        fallback_used  – True when the fallback request was actually sent.

    Contract
    --------
    * At most **one** extra SerpApi request per call.
    * If the initial search raises an HTTPException it is re-raised immediately
      (existing error-handling behaviour preserved).
    * If the fallback itself fails, the original (sparse) results are returned
      and the exception is logged rather than propagated.
    * The returned SearchResponse always carries ``original_query`` as the
      query label so that the caller's intent/budget context is preserved.
    """
    if not original_query or not original_query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    if len(original_query) > 200:
        raise HTTPException(status_code=400, detail="Search query is too long.")

    # -- Initial search (may raise HTTPException; we let it propagate) --------
    initial_response = perform_commerce_search(original_query)

    usable_count = len(initial_response.products)
    fallback_used = False

    # -- Decide whether a fallback is warranted --------------------------------
    if usable_count >= FALLBACK_THRESHOLD:
        # Already enough products — return immediately, no extra request.
        return initial_response, fallback_used

    # Normalise both queries for comparison (strip, lower-case, collapse spaces)
    def _normalise(q: str) -> str:
        return " ".join(q.strip().lower().split())

    norm_original = _normalise(original_query)
    norm_fallback = _normalise(fallback_query) if fallback_query else ""

    if not norm_fallback or norm_fallback == norm_original:
        # Fallback query is empty or identical — skip to avoid duplicate request.
        logger.info(
            f"Skipping fallback: fallback_query is empty or identical to original "
            f"(original='{original_query}', fallback='{fallback_query}')"
        )
        return initial_response, fallback_used

    # -- Single fallback request ----------------------------------------------
    logger.info(
        f"Initial search returned {usable_count} products (< {FALLBACK_THRESHOLD}). "
        f"Attempting fallback query: '{fallback_query}'"
    )
    fallback_used = True
    try:
        fallback_raw = serpapi_client.search_google_shopping(fallback_query)
        fallback_results = fallback_raw.get("shopping_results", [])
        if fallback_results:
            fallback_products = normalize_shopping_results(fallback_results)
            if fallback_products:
                logger.info(
                    f"Fallback returned {len(fallback_products)} products. "
                    f"Using fallback results."
                )
                # Return results under the ORIGINAL query label so that the
                # caller's budget / intent context is not lost.
                return SearchResponse(
                    query=original_query,
                    count=len(fallback_products),
                    products=fallback_products,
                ), fallback_used
            else:
                logger.info("Fallback products normalized to empty list; retaining original.")
        else:
            logger.info("Fallback returned no shopping_results; retaining original.")

    except HTTPException as exc:
        # Fallback failed — log and retain original sparse results
        logger.warning(
            f"Fallback search failed (HTTP {exc.status_code}): {exc.detail}. "
            f"Retaining original {usable_count} results."
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            f"Fallback search raised unexpected error: {exc}. "
            f"Retaining original {usable_count} results."
        )

    # Fallback was attempted but produced no improvement — return original data.
    return initial_response, fallback_used
