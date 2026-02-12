"""
Patent search via SerpApi's Google Patents endpoint.

SerpApi provides structured access to Google Patents search results.
API documentation: https://serpapi.com/google-patents-api

Requires a SERPAPI_KEY environment variable (free tier: 100 searches/month).
"""

import logging
import time
from datetime import datetime, timedelta

import requests

from crm_patent_analyzer.config import (
    GOOGLE_PATENTS_BASE_URL,
    MAX_RESULTS_PER_MATERIAL,
    SERPAPI_KEY,
)

logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


def search_patents(
    query: str,
    after_date: str | None = None,
    before_date: str | None = None,
    page: int = 0,
    num_results: int = 10,
) -> dict:
    """
    Search Google Patents via SerpApi.

    Args:
        query: Search query string (e.g., material name + application)
        after_date: Filter patents published after this date (YYYYMMDD)
        before_date: Filter patents published before this date (YYYYMMDD)
        page: Page number (0-indexed, each page has `num_results` results)
        num_results: Number of results per page (max 10 for SerpApi)

    Returns:
        dict with 'patents' (list of patent dicts) and 'total_results' count
    """
    if not SERPAPI_KEY:
        logger.warning("SERPAPI_KEY not set. Using Lens.org fallback or returning empty results.")
        return {"patents": [], "total_results": 0, "source": "serpapi", "error": "no_api_key"}

    params = {
        "engine": "google_patents",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": min(num_results, 10),
    }

    if after_date:
        params["after"] = f"publication:{after_date}"
    if before_date:
        params["before"] = f"publication:{before_date}"
    if page > 0:
        params["page"] = page

    try:
        response = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.error("SerpApi request failed: %s", e)
        return {"patents": [], "total_results": 0, "source": "serpapi", "error": str(e)}

    patents = []
    for result in data.get("organic_results", []):
        patent = _parse_serpapi_result(result)
        if patent:
            patents.append(patent)

    total = data.get("search_information", {}).get("total_results", len(patents))

    return {"patents": patents, "total_results": total, "source": "serpapi"}


def _parse_serpapi_result(result: dict) -> dict | None:
    """Parse a single SerpApi Google Patents result into our standard format."""
    patent_id = result.get("patent_id", "")
    if not patent_id:
        snippet = result.get("snippet", "")
        link = result.get("link", "")
        # Try to extract patent ID from the link
        if "/patent/" in link:
            patent_id = link.split("/patent/")[-1].split("/")[0]

    if not patent_id:
        return None

    return {
        "patent_id": patent_id,
        "title": result.get("title", ""),
        "abstract": result.get("snippet", ""),
        "assignee": result.get("assignee", ""),
        "inventors": result.get("inventor", ""),
        "filing_date": result.get("filing_date"),
        "publication_date": result.get("publication_date") or result.get("date"),
        "grant_date": result.get("grant_date"),
        "cpc_codes": result.get("cpc_codes", []),
        "url": result.get("link", f"{GOOGLE_PATENTS_BASE_URL}{patent_id}"),
        "source": "google_patents",
        "raw_data": result,
    }


def search_material_patents(
    material_name: str,
    search_terms: list[str],
    after_date: str | None = None,
    max_results: int | None = None,
) -> list[dict]:
    """
    Search for patents related to a specific critical raw material.

    Constructs multiple targeted queries using the material's search terms
    combined with usage-context keywords.

    Args:
        material_name: The CRM name
        search_terms: List of names/aliases to search
        after_date: Only find patents after this date
        max_results: Maximum total results to return

    Returns:
        List of patent dicts
    """
    max_results = max_results or MAX_RESULTS_PER_MATERIAL
    all_patents = {}  # Deduplicate by patent_id

    # Build targeted queries
    queries = []
    for term in search_terms[:5]:  # Limit to top 5 terms to conserve API calls
        # General material patent query
        queries.append(f'"{term}"')
        # Material in manufacturing
        queries.append(f'"{term}" AND (manufacturing OR process OR method OR production)')
        # Material in product/good
        queries.append(f'"{term}" AND (device OR apparatus OR composition OR product)')

    for query in queries:
        if len(all_patents) >= max_results:
            break

        result = search_patents(query, after_date=after_date)

        if result.get("error"):
            logger.warning("Search failed for query '%s': %s", query, result["error"])
            continue

        for patent in result["patents"]:
            pid = patent["patent_id"]
            if pid not in all_patents:
                all_patents[pid] = patent

        # Rate limiting - be respectful to the API
        time.sleep(1)

    patents_list = list(all_patents.values())[:max_results]
    logger.info("Found %d patents for material '%s'", len(patents_list), material_name)
    return patents_list


def search_downstream_patents(
    patent_title: str,
    patent_id: str,
    cpc_codes: list[str] | None = None,
) -> list[dict]:
    """
    Search for downstream patents that might use the good/process
    described in the given patent.

    Args:
        patent_title: Title of the upstream patent
        patent_id: ID of the upstream patent
        cpc_codes: CPC codes from the upstream patent

    Returns:
        List of patent dicts that may be downstream consumers
    """
    all_patents = {}

    # Search by citing the upstream patent
    queries = [f'"{patent_id}"']

    # Extract key noun phrases from the title for semantic search
    title_words = patent_title.split()
    if len(title_words) >= 3:
        # Use the most descriptive portion of the title
        key_phrase = " ".join(title_words[:6])
        queries.append(f'"{key_phrase}" AND (using OR comprising OR incorporating)')

    for query in queries:
        result = search_patents(query, num_results=10)
        if not result.get("error"):
            for patent in result["patents"]:
                pid = patent["patent_id"]
                if pid != patent_id and pid not in all_patents:
                    all_patents[pid] = patent
        time.sleep(1)

    return list(all_patents.values())


def search_substitution_patents(
    material_name: str,
    search_terms: list[str],
) -> list[dict]:
    """
    Search for patents that explicitly attempt to substitute a critical raw material.

    Args:
        material_name: The CRM being substituted
        search_terms: Search terms for the material

    Returns:
        List of patent dicts describing substitution attempts
    """
    all_patents = {}
    substitution_keywords = [
        "substitute", "replacement", "alternative", "replacing",
        "free", "without", "reduced", "eliminating",
    ]

    for term in search_terms[:3]:
        for kw in substitution_keywords[:4]:
            query = f'"{term}" AND ({kw})'
            result = search_patents(query, num_results=10)
            if not result.get("error"):
                for patent in result["patents"]:
                    pid = patent["patent_id"]
                    if pid not in all_patents:
                        all_patents[pid] = patent
            time.sleep(1)

            if len(all_patents) >= 50:
                break
        if len(all_patents) >= 50:
            break

    return list(all_patents.values())
