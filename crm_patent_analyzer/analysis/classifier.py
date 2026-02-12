"""
Patent usage classifier - determines if a critical raw material is used
as part of the good itself, or in a manufacturing process.

Classification approach:
1. Keyword-based heuristics analyzing title, abstract, and CPC codes
2. CPC code mapping (process-oriented vs product-oriented codes)
3. Confidence scoring based on signal strength
"""

import json
import logging
import re

from crm_patent_analyzer.data.critical_raw_materials import (
    CriticalRawMaterial,
    detect_materials_in_text,
)
from crm_patent_analyzer.data.database import get_db, upsert_patent_material

logger = logging.getLogger(__name__)

# Keywords strongly indicating the material is part of the GOOD itself
GOOD_KEYWORDS = [
    "comprising", "consisting of", "containing", "composed of",
    "device", "apparatus", "system", "component", "article",
    "electrode", "cathode", "anode", "membrane", "substrate",
    "alloy", "composite", "compound", "material", "composition",
    "battery", "cell", "sensor", "catalyst", "magnet",
    "layer", "coating", "film", "wire", "fiber",
    "implant", "prosthesis", "semiconductor", "wafer",
]

# Keywords strongly indicating the material is used in MANUFACTURING
MANUFACTURING_KEYWORDS = [
    "method of", "process for", "method for", "process of",
    "manufacturing", "fabricating", "producing", "preparing",
    "synthesizing", "forming", "depositing", "smelting",
    "refining", "extracting", "purifying", "separating",
    "etching", "doping", "annealing", "sintering",
    "electroplating", "electrodeposition", "chemical vapor deposition",
    "sputtering", "casting", "molding", "extrusion",
    "heat treatment", "calcination", "leaching", "flotation",
    "solvent extraction", "precipitation", "crystallization",
]

# CPC codes primarily associated with manufacturing processes
PROCESS_CPC_PREFIXES = [
    "C22B",  # Production or refining of metals
    "C22C",  # Alloys (can be both)
    "C23C",  # Coating metallic material
    "C25D",  # Electroplating
    "C25B",  # Electrolytic processes
    "B22D",  # Casting
    "B22F",  # Powder metallurgy
    "C01B",  # Non-metallic elements (processing)
    "C01G",  # Compounds containing metals (processing)
    "C04B",  # Ceramics manufacturing
    "C30B",  # Crystal growth
]

# CPC codes primarily associated with products/goods
PRODUCT_CPC_PREFIXES = [
    "H01M",  # Batteries/fuel cells (product)
    "H01L",  # Semiconductor devices (product)
    "H01F",  # Magnets (product)
    "H01G",  # Capacitors (product)
    "H02K",  # Electric machines (product)
    "B60L",  # Electric vehicles (product)
    "A61K",  # Pharmaceuticals (product)
    "A61L",  # Medical devices (product)
    "G02B",  # Optical elements (product)
    "F03D",  # Wind motors (product)
]


def classify_patent(patent: dict, material: CriticalRawMaterial) -> dict:
    """
    Classify how a critical raw material is used in a patent.

    Args:
        patent: Patent data dict
        material: The CRM being analyzed

    Returns:
        dict with keys: usage_type ('good'|'manufacturing'|'unknown'),
                       usage_description, confidence
    """
    title = patent.get("title", "").lower()
    abstract = patent.get("abstract", "").lower()
    text = f"{title} {abstract}"

    cpc_codes = patent.get("cpc_codes", [])
    if isinstance(cpc_codes, str):
        try:
            cpc_codes = json.loads(cpc_codes)
        except (json.JSONDecodeError, TypeError):
            cpc_codes = []

    good_score = 0.0
    manufacturing_score = 0.0
    signals = []

    # 1. Keyword analysis
    for kw in GOOD_KEYWORDS:
        if kw in text:
            good_score += 1.0
            signals.append(f"good_keyword:{kw}")

    for kw in MANUFACTURING_KEYWORDS:
        if kw in text:
            manufacturing_score += 1.0
            signals.append(f"mfg_keyword:{kw}")

    # 2. Title-based classification (titles are more definitive)
    if any(kw in title for kw in ["method", "process", "manufacturing", "producing", "preparation"]):
        manufacturing_score += 3.0
        signals.append("title_indicates_process")
    if any(kw in title for kw in ["device", "apparatus", "system", "composition", "battery", "cell"]):
        good_score += 3.0
        signals.append("title_indicates_good")

    # 3. CPC code analysis
    for cpc in cpc_codes:
        cpc_str = str(cpc)
        for prefix in PROCESS_CPC_PREFIXES:
            if cpc_str.startswith(prefix):
                manufacturing_score += 2.0
                signals.append(f"process_cpc:{cpc_str}")
                break
        for prefix in PRODUCT_CPC_PREFIXES:
            if cpc_str.startswith(prefix):
                good_score += 2.0
                signals.append(f"product_cpc:{cpc_str}")
                break

    # 4. Determine usage type
    total_score = good_score + manufacturing_score
    if total_score == 0:
        return {
            "usage_type": "unknown",
            "usage_description": "Insufficient signals to classify usage type",
            "confidence": 0.0,
            "signals": signals,
        }

    if good_score > manufacturing_score:
        usage_type = "good"
        confidence = good_score / total_score
        description = _generate_good_description(patent, material, signals)
    elif manufacturing_score > good_score:
        usage_type = "manufacturing"
        confidence = manufacturing_score / total_score
        description = _generate_manufacturing_description(patent, material, signals)
    else:
        usage_type = "unknown"
        confidence = 0.5
        description = "Patent shows equal signals for both good and manufacturing usage"

    # Cap confidence at 0.95
    confidence = min(confidence, 0.95)

    return {
        "usage_type": usage_type,
        "usage_description": description,
        "confidence": round(confidence, 3),
        "signals": signals,
    }


def _generate_good_description(patent: dict, material: CriticalRawMaterial,
                               signals: list[str]) -> str:
    """Generate a human-readable description of how the material is used in the good."""
    title = patent.get("title", "Unknown patent")
    material_terms = [s.split(":")[1] for s in signals if s.startswith("good_keyword:")]
    context = ", ".join(material_terms[:3]) if material_terms else "component"
    return (
        f"{material.name} is incorporated as a {context} "
        f"in the product described by: {title}"
    )


def _generate_manufacturing_description(patent: dict, material: CriticalRawMaterial,
                                        signals: list[str]) -> str:
    """Generate a human-readable description of how the material is used in manufacturing."""
    title = patent.get("title", "Unknown patent")
    process_terms = [s.split(":")[1] for s in signals if s.startswith("mfg_keyword:")]
    context = ", ".join(process_terms[:3]) if process_terms else "manufacturing step"
    return (
        f"{material.name} is used in a {context} "
        f"in the process described by: {title}"
    )


def classify_all_patents(material_name: str | None = None):
    """
    Classify all unclassified patents in the database.

    Args:
        material_name: If provided, only classify patents for this material
    """
    from crm_patent_analyzer.data.critical_raw_materials import CRM_BY_NAME

    with get_db() as conn:
        if material_name:
            rows = conn.execute("""
                SELECT p.*, pm.material_name, pm.matched_term
                FROM patents p
                JOIN patent_materials pm ON p.patent_id = pm.patent_id
                WHERE pm.material_name = ? AND pm.usage_type = 'unknown'
            """, (material_name,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT p.*, pm.material_name, pm.matched_term
                FROM patents p
                JOIN patent_materials pm ON p.patent_id = pm.patent_id
                WHERE pm.usage_type = 'unknown'
            """).fetchall()

        classified = 0
        for row in rows:
            mat_name = row["material_name"]
            material = CRM_BY_NAME.get(mat_name)
            if not material:
                continue

            patent_data = dict(row)
            result = classify_patent(patent_data, material)

            upsert_patent_material(
                conn,
                patent_data["patent_id"],
                mat_name,
                row["matched_term"] or mat_name,
                usage_type=result["usage_type"],
                usage_description=result["usage_description"],
                confidence=result["confidence"],
            )
            classified += 1

        logger.info("Classified %d patents", classified)
