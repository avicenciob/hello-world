"""
Supply chain mapper for critical raw material patents.

Maps upstream-downstream relationships between patents to trace how critical
raw materials flow through supply chains:

1. Raw material extraction/processing patents (upstream)
2. Component/intermediate good patents (midstream)
3. Final product patents (downstream)

Links are established by:
- CPC code proximity (patents in related technology areas)
- Citation analysis (patents citing each other)
- Semantic similarity (patents describing related technologies)
- Material flow inference (output of one patent = input of another)
"""

import json
import logging
from collections import defaultdict

from crm_patent_analyzer.data.database import (
    get_db,
    upsert_supply_chain_link,
)

logger = logging.getLogger(__name__)

# Technology domain groupings for supply chain inference
# Maps CPC prefixes to supply chain stages
SUPPLY_CHAIN_STAGES = {
    # Stage 1: Extraction & Processing
    "extraction": ["C22B", "C01B", "C01G", "C01F", "B03", "B07"],
    # Stage 2: Material Refinement & Synthesis
    "refinement": ["C22C", "C23C", "C25D", "C30B", "C04B", "C01D"],
    # Stage 3: Component Manufacturing
    "component": ["H01M", "H01L", "H01F", "H01G", "H01B", "C08", "C09"],
    # Stage 4: System Integration
    "system": ["H02K", "H02J", "F03D", "B60L", "H05K", "G01", "G02"],
    # Stage 5: End Products
    "product": ["A61K", "A61L", "B60", "F24", "H04", "G06"],
}

# Known supply chain connections (CPC prefix pairs)
# (upstream_prefix, downstream_prefix) -> link description
KNOWN_SUPPLY_CHAINS = {
    ("C22B", "H01M"): "Refined metal used in battery electrodes",
    ("C22B", "H01L"): "Refined material used in semiconductor fabrication",
    ("C22B", "H01F"): "Refined metal used in magnet production",
    ("C22B", "C22C"): "Refined metal used in alloy production",
    ("C22C", "H02K"): "Alloy used in electric motor manufacturing",
    ("C22C", "B60L"): "Alloy used in electric vehicle components",
    ("C01B", "H01M"): "Synthesized material used in battery production",
    ("C01B", "H01L"): "Synthesized material used in semiconductors",
    ("C01G", "H01M"): "Metal compound used in battery cathode",
    ("C30B", "H01L"): "Crystal used in semiconductor wafer production",
    ("H01M", "B60L"): "Battery used in electric vehicle",
    ("H01L", "H05K"): "Semiconductor integrated into circuit board",
    ("H01F", "H02K"): "Magnet used in electric motor",
    ("H02K", "F03D"): "Electric motor used in wind turbine",
    ("H02K", "B60L"): "Electric motor used in electric vehicle",
    ("C04B", "A61L"): "Ceramic used in medical implant",
    ("C23C", "H01L"): "Coating process applied to semiconductor",
}


def build_supply_chain_map():
    """
    Analyze all patents in the database and build supply chain linkages.

    This function:
    1. Groups patents by CPC codes and materials
    2. Identifies upstream/downstream relationships
    3. Stores links in the supply_chain_links table
    """
    with get_db() as conn:
        # Fetch all patents with their materials and classifications
        patents = conn.execute("""
            SELECT p.patent_id, p.title, p.abstract, p.cpc_codes,
                   pm.material_name, pm.usage_type
            FROM patents p
            JOIN patent_materials pm ON p.patent_id = pm.patent_id
            ORDER BY p.patent_id
        """).fetchall()

        if not patents:
            logger.warning("No patents in database to map supply chains")
            return

        # Group patents by material
        material_patents = defaultdict(list)
        for row in patents:
            material_patents[row["material_name"]].append(dict(row))

        links_created = 0

        # For each material, find upstream-downstream relationships
        for material_name, mat_patents in material_patents.items():
            for i, upstream in enumerate(mat_patents):
                upstream_stage = _get_supply_chain_stage(upstream)
                upstream_cpcs = _get_cpc_prefixes(upstream)

                for downstream in mat_patents[i + 1:]:
                    if upstream["patent_id"] == downstream["patent_id"]:
                        continue

                    downstream_stage = _get_supply_chain_stage(downstream)
                    downstream_cpcs = _get_cpc_prefixes(downstream)

                    # Check if there's a known supply chain connection
                    link = _find_supply_chain_link(
                        upstream, downstream,
                        upstream_stage, downstream_stage,
                        upstream_cpcs, downstream_cpcs,
                    )

                    if link:
                        upsert_supply_chain_link(
                            conn,
                            upstream["patent_id"],
                            downstream["patent_id"],
                            link["link_type"],
                            link["description"],
                            link["confidence"],
                        )
                        links_created += 1

        logger.info("Created %d supply chain links", links_created)


def _get_supply_chain_stage(patent: dict) -> str:
    """Determine which supply chain stage a patent belongs to."""
    cpcs = _get_cpc_prefixes(patent)
    usage_type = patent.get("usage_type", "unknown")

    # Check CPC-based stage
    for stage, prefixes in SUPPLY_CHAIN_STAGES.items():
        for prefix in prefixes:
            if prefix in cpcs:
                return stage

    # Fall back to usage type
    if usage_type == "manufacturing":
        return "refinement"
    elif usage_type == "good":
        return "component"

    return "unknown"


def _get_cpc_prefixes(patent: dict) -> set[str]:
    """Extract CPC code prefixes (first 4 chars) from a patent."""
    cpc_codes = patent.get("cpc_codes", "[]")
    if isinstance(cpc_codes, str):
        try:
            cpc_codes = json.loads(cpc_codes)
        except (json.JSONDecodeError, TypeError):
            cpc_codes = []
    return {str(c)[:4] for c in cpc_codes if c}


def _find_supply_chain_link(
    upstream: dict, downstream: dict,
    upstream_stage: str, downstream_stage: str,
    upstream_cpcs: set[str], downstream_cpcs: set[str],
) -> dict | None:
    """
    Determine if there's a supply chain link between two patents.

    Returns link info dict or None.
    """
    # Check known CPC-based supply chains
    for up_cpc in upstream_cpcs:
        for down_cpc in downstream_cpcs:
            key = (up_cpc, down_cpc)
            if key in KNOWN_SUPPLY_CHAINS:
                link_type = _determine_link_type(upstream, downstream)
                return {
                    "link_type": link_type,
                    "description": KNOWN_SUPPLY_CHAINS[key],
                    "confidence": 0.8,
                }

    # Check stage-based relationships
    stage_order = ["extraction", "refinement", "component", "system", "product"]
    if upstream_stage in stage_order and downstream_stage in stage_order:
        up_idx = stage_order.index(upstream_stage)
        down_idx = stage_order.index(downstream_stage)

        if 0 < down_idx - up_idx <= 2:
            link_type = _determine_link_type(upstream, downstream)
            confidence = 0.5 if (down_idx - up_idx) == 1 else 0.3
            return {
                "link_type": link_type,
                "description": (
                    f"Supply chain stage progression: "
                    f"{upstream_stage} -> {downstream_stage}"
                ),
                "confidence": confidence,
            }

    # Check for title/abstract semantic overlap
    overlap_score = _text_overlap_score(upstream, downstream)
    if overlap_score > 0.3:
        link_type = _determine_link_type(upstream, downstream)
        return {
            "link_type": link_type,
            "description": "Linked by technology keyword overlap",
            "confidence": min(overlap_score, 0.6),
        }

    return None


def _determine_link_type(upstream: dict, downstream: dict) -> str:
    """Determine the type of supply chain link."""
    up_type = upstream.get("usage_type", "unknown")
    down_type = downstream.get("usage_type", "unknown")

    if up_type == "manufacturing" and down_type == "good":
        return "material_in_good"
    elif up_type == "manufacturing" and down_type == "manufacturing":
        return "process_in_process"
    elif up_type == "good" and down_type == "good":
        return "good_in_good"
    else:
        return "material_in_process"


def _text_overlap_score(patent_a: dict, patent_b: dict) -> float:
    """Calculate keyword overlap between two patents (simple Jaccard similarity)."""
    text_a = f"{patent_a.get('title', '')} {patent_a.get('abstract', '')}".lower()
    text_b = f"{patent_b.get('title', '')} {patent_b.get('abstract', '')}".lower()

    # Extract significant words (length >= 4, not common stop words)
    stop_words = {
        "this", "that", "with", "from", "have", "been", "were", "will",
        "which", "their", "about", "would", "there", "could", "other",
        "into", "more", "also", "than", "each", "said", "when", "them",
        "some", "such", "only", "first", "second", "third",
        "method", "process", "comprising", "present", "invention",
    }

    words_a = {w for w in text_a.split() if len(w) >= 4 and w not in stop_words}
    words_b = {w for w in text_b.split() if len(w) >= 4 and w not in stop_words}

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def get_supply_chain_graph() -> dict:
    """
    Retrieve the full supply chain graph from the database.

    Returns:
        dict with 'nodes' (patents) and 'edges' (supply chain links)
        formatted for visualization.
    """
    with get_db() as conn:
        # Get all patents that have supply chain links
        nodes_data = conn.execute("""
            SELECT DISTINCT p.patent_id, p.title, p.url, p.assignee,
                   p.publication_date, pm.material_name, pm.usage_type,
                   pm.usage_description, pm.confidence
            FROM patents p
            JOIN patent_materials pm ON p.patent_id = pm.patent_id
            WHERE p.patent_id IN (
                SELECT upstream_patent_id FROM supply_chain_links
                UNION
                SELECT downstream_patent_id FROM supply_chain_links
            )
        """).fetchall()

        edges_data = conn.execute("""
            SELECT upstream_patent_id, downstream_patent_id,
                   link_type, link_description, confidence
            FROM supply_chain_links
            ORDER BY confidence DESC
        """).fetchall()

        nodes = []
        for row in nodes_data:
            nodes.append({
                "id": row["patent_id"],
                "title": row["title"],
                "url": row["url"],
                "assignee": row["assignee"],
                "publication_date": row["publication_date"],
                "material": row["material_name"],
                "usage_type": row["usage_type"],
                "usage_description": row["usage_description"],
                "confidence": row["confidence"],
            })

        edges = []
        for row in edges_data:
            edges.append({
                "source": row["upstream_patent_id"],
                "target": row["downstream_patent_id"],
                "link_type": row["link_type"],
                "description": row["link_description"],
                "confidence": row["confidence"],
            })

        return {"nodes": nodes, "edges": edges}
