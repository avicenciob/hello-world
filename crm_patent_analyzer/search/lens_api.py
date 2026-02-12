"""
Patent search via Lens.org Scholarly & Patent API.

Lens.org provides free access to patent data with a generous API tier.
API documentation: https://docs.api.lens.org/

Requires a LENS_API_KEY environment variable.
Register at https://www.lens.org/lens/user/subscriptions
"""

import logging
import time

import requests

from crm_patent_analyzer.config import GOOGLE_PATENTS_BASE_URL, LENS_API_KEY

logger = logging.getLogger(__name__)

LENS_API_URL = "https://api.lens.org/patent/search"


def search_patents(
    query: str,
    after_date: str | None = None,
    before_date: str | None = None,
    offset: int = 0,
    size: int = 50,
) -> dict:
    """
    Search patents via Lens.org API.

    Args:
        query: Full-text search query
        after_date: Filter patents published after this date (YYYY-MM-DD)
        before_date: Filter patents published before this date (YYYY-MM-DD)
        offset: Pagination offset
        size: Number of results per page (max 50)

    Returns:
        dict with 'patents' list and 'total_results' count
    """
    if not LENS_API_KEY:
        logger.warning("LENS_API_KEY not set.")
        return {"patents": [], "total_results": 0, "source": "lens", "error": "no_api_key"}

    must_clauses = [{"query_string": {"query": query, "default_field": "full_text"}}]

    if after_date or before_date:
        date_range = {}
        if after_date:
            date_range["gte"] = after_date
        if before_date:
            date_range["lte"] = before_date
        must_clauses.append({"range": {"date_published": date_range}})

    body = {
        "query": {"bool": {"must": must_clauses}},
        "size": min(size, 50),
        "from": offset,
        "sort": [{"date_published": "desc"}],
        "include": [
            "lens_id", "title", "abstract", "biblio.parties",
            "biblio.classifications_cpc", "date_published",
            "biblio.publication_reference", "doc_number",
        ],
    }

    headers = {
        "Authorization": f"Bearer {LENS_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(LENS_API_URL, json=body, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.error("Lens.org API request failed: %s", e)
        return {"patents": [], "total_results": 0, "source": "lens", "error": str(e)}

    patents = []
    for result in data.get("data", []):
        patent = _parse_lens_result(result)
        if patent:
            patents.append(patent)

    total = data.get("total", len(patents))
    return {"patents": patents, "total_results": total, "source": "lens"}


def _parse_lens_result(result: dict) -> dict | None:
    """Parse a Lens.org patent result into our standard format."""
    lens_id = result.get("lens_id", "")
    doc_number = result.get("doc_number", "")

    pub_ref = result.get("biblio", {}).get("publication_reference", {})
    patent_id = doc_number or pub_ref.get("doc_number", "") or lens_id

    if not patent_id:
        return None

    # Extract title
    title_obj = result.get("title", "")
    if isinstance(title_obj, list):
        title = title_obj[0].get("text", "") if title_obj else ""
    elif isinstance(title_obj, dict):
        title = title_obj.get("text", "")
    else:
        title = str(title_obj)

    # Extract abstract
    abstract_obj = result.get("abstract", "")
    if isinstance(abstract_obj, list):
        abstract = abstract_obj[0].get("text", "") if abstract_obj else ""
    elif isinstance(abstract_obj, dict):
        abstract = abstract_obj.get("text", "")
    else:
        abstract = str(abstract_obj)

    # Extract parties
    parties = result.get("biblio", {}).get("parties", {})
    applicants = parties.get("applicants", [])
    inventors = parties.get("inventors", [])
    assignee = ", ".join(a.get("extracted_name", {}).get("value", "") for a in applicants[:3])
    inventor_str = ", ".join(i.get("extracted_name", {}).get("value", "") for i in inventors[:5])

    # CPC codes
    cpc_list = result.get("biblio", {}).get("classifications_cpc", {}).get("classifications", [])
    cpc_codes = [c.get("symbol", "") for c in cpc_list if c.get("symbol")]

    return {
        "patent_id": patent_id,
        "title": title,
        "abstract": abstract,
        "assignee": assignee,
        "inventors": inventor_str,
        "filing_date": None,
        "publication_date": result.get("date_published"),
        "grant_date": None,
        "cpc_codes": cpc_codes,
        "url": f"{GOOGLE_PATENTS_BASE_URL}{patent_id}",
        "source": "lens",
        "raw_data": result,
    }


def search_material_patents(
    material_name: str,
    search_terms: list[str],
    after_date: str | None = None,
    max_results: int = 100,
) -> list[dict]:
    """Search for patents mentioning a critical raw material via Lens.org."""
    all_patents = {}

    for term in search_terms[:5]:
        if len(all_patents) >= max_results:
            break

        # Broad search for the material
        query = f'"{term}"'
        result = search_patents(query, after_date=after_date, size=50)
        if not result.get("error"):
            for patent in result["patents"]:
                pid = patent["patent_id"]
                if pid not in all_patents:
                    all_patents[pid] = patent
        time.sleep(0.5)

    return list(all_patents.values())[:max_results]
