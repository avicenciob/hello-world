"""
Unified patent search orchestrator.

Coordinates searches across multiple patent data sources (SerpApi/Google Patents,
Lens.org) and stores results in the local database.
"""

import logging
from datetime import datetime, timedelta

from crm_patent_analyzer.config import LENS_API_KEY, SEARCH_LOOKBACK_DAYS, SERPAPI_KEY
from crm_patent_analyzer.data.critical_raw_materials import (
    CriticalRawMaterial,
    get_all_materials,
)
from crm_patent_analyzer.data.database import (
    complete_scan,
    get_db,
    start_scan,
    upsert_patent,
    upsert_patent_material,
)
from crm_patent_analyzer.search import google_patents, lens_api

logger = logging.getLogger(__name__)


def search_all_materials(
    after_date: str | None = None,
    materials: list[CriticalRawMaterial] | None = None,
    max_results_per_material: int = 100,
) -> dict[str, list[dict]]:
    """
    Search for patents across all (or specified) critical raw materials.

    Uses SerpApi as the primary source, falling back to Lens.org.

    Args:
        after_date: Only find patents published after this date (YYYYMMDD or YYYY-MM-DD)
        materials: Specific materials to search (default: all CRMs)
        max_results_per_material: Max patents per material

    Returns:
        Dict mapping material name -> list of patent dicts
    """
    if materials is None:
        materials = get_all_materials()

    results = {}
    search_fn = _get_search_function()

    with get_db() as conn:
        scan_id = start_scan(conn, "full_scan")

        total_found = 0
        for material in materials:
            logger.info("Searching patents for: %s", material.name)
            try:
                patents = search_fn(
                    material.name,
                    material.search_terms(),
                    after_date=after_date,
                    max_results=max_results_per_material,
                )
                results[material.name] = patents
                total_found += len(patents)

                # Store in database
                for patent in patents:
                    patent_id = upsert_patent(conn, patent)
                    # Record the material association
                    upsert_patent_material(
                        conn, patent_id, material.name,
                        matched_term=material.name,
                        usage_type="unknown",
                    )
            except Exception as e:
                logger.error("Error searching for %s: %s", material.name, e)
                results[material.name] = []

        complete_scan(conn, scan_id, total_found)

    logger.info("Search complete. Total patents found: %d", total_found)
    return results


def search_single_material(
    material: CriticalRawMaterial,
    after_date: str | None = None,
    max_results: int = 100,
) -> list[dict]:
    """Search patents for a single material and store results."""
    search_fn = _get_search_function()

    with get_db() as conn:
        scan_id = start_scan(conn, "single_material", material.name)

        patents = search_fn(
            material.name,
            material.search_terms(),
            after_date=after_date,
            max_results=max_results,
        )

        for patent in patents:
            patent_id = upsert_patent(conn, patent)
            upsert_patent_material(
                conn, patent_id, material.name,
                matched_term=material.name,
                usage_type="unknown",
            )

        complete_scan(conn, scan_id, len(patents))

    return patents


def incremental_scan(lookback_days: int | None = None) -> dict[str, list[dict]]:
    """
    Perform an incremental scan for new patents since last scan.

    Used by the scheduler for periodic updates.
    """
    days = lookback_days or SEARCH_LOOKBACK_DAYS
    after_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    logger.info("Running incremental scan for patents after %s", after_date)
    return search_all_materials(after_date=after_date)


def _get_search_function():
    """Return the best available search function based on configured API keys."""
    if SERPAPI_KEY:
        logger.info("Using SerpApi (Google Patents) for search")
        return google_patents.search_material_patents
    elif LENS_API_KEY:
        logger.info("Using Lens.org API for search")
        return lens_api.search_material_patents
    else:
        logger.warning(
            "No API keys configured. Set SERPAPI_KEY or LENS_API_KEY. "
            "Returning empty results."
        )
        return _empty_search


def _empty_search(material_name, search_terms, **kwargs):
    """Placeholder when no API key is available."""
    logger.warning("No search API configured. Skipping search for '%s'", material_name)
    return []
