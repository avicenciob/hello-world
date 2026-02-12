"""
Substitution detector for critical raw materials.

Identifies patents that attempt to replace or substitute critical raw materials
with alternative materials, either partially or fully.

Detection strategies:
1. Explicit keyword matching (e.g., "cobalt-free", "replacing lithium")
2. Co-occurrence of CRM + alternative material in same patent
3. CPC code patterns associated with material substitution research
"""

import json
import logging
import re
from collections import defaultdict

from crm_patent_analyzer.data.critical_raw_materials import (
    CRM_BY_NAME,
    CriticalRawMaterial,
    detect_materials_in_text,
    get_all_materials,
)
from crm_patent_analyzer.data.database import get_db, upsert_substitution

logger = logging.getLogger(__name__)

# Patterns indicating substitution attempts
SUBSTITUTION_PATTERNS = [
    r"(?:replace|replacing|replacement)\s+(?:of\s+)?{material}",
    r"{material}[\s-]*free",
    r"without\s+{material}",
    r"(?:alternative|substitute|substitution)\s+(?:for|to|of)\s+{material}",
    r"(?:eliminating|reducing|minimizing)\s+{material}",
    r"{material}\s+(?:replaced|substituted)\s+(?:by|with)",
    r"(?:instead\s+of|in\s+place\s+of|in\s+lieu\s+of)\s+{material}",
    r"(?:reduced|lower|decreased|minimal)\s+{material}\s+(?:content|amount|concentration)",
    r"(?:non-|non\s+){material}",
]

# Known material substitution pairs (original -> common substitutes)
KNOWN_SUBSTITUTIONS = {
    "Cobalt": ["iron", "manganese", "nickel", "aluminium", "aluminum"],
    "Rare Earth Elements": [
        "ferrite", "iron nitride", "manganese bismuth",
        "iron-based", "cerium-free",
    ],
    "Lithium": ["sodium", "potassium", "zinc", "magnesium", "aluminium", "aluminum"],
    "Platinum Group Metals": [
        "non-precious metal", "iron", "cobalt", "nickel",
        "carbon-based", "metal-free",
    ],
    "Tungsten": ["molybdenum", "titanium", "ceramic", "cermet"],
    "Tantalum": ["niobium", "ceramic", "polymer", "aluminium", "aluminum"],
    "Gallium": ["silicon", "indium", "zinc oxide"],
    "Germanium": ["silicon", "tin"],
    "Natural graphite": ["synthetic graphite", "silicon", "hard carbon"],
    "Cobalt": ["iron phosphate", "manganese", "nickel-rich"],
    "Nickel": ["iron", "manganese", "zinc"],
    "Copper": ["aluminium", "aluminum", "carbon nanotube", "optical fiber"],
}


def detect_substitutions():
    """
    Scan all patents in the database for substitution attempts.

    Analyzes patent titles and abstracts for patterns indicating that
    a critical raw material is being replaced or substituted.
    """
    with get_db() as conn:
        patents = conn.execute("""
            SELECT p.patent_id, p.title, p.abstract, p.cpc_codes,
                   pm.material_name
            FROM patents p
            JOIN patent_materials pm ON p.patent_id = pm.patent_id
        """).fetchall()

        substitutions_found = 0
        for row in patents:
            patent_data = dict(row)
            material = CRM_BY_NAME.get(row["material_name"])
            if not material:
                continue

            subs = _detect_substitution_in_patent(patent_data, material)
            for sub in subs:
                upsert_substitution(
                    conn,
                    patent_data["patent_id"],
                    sub["original_material"],
                    sub["substitute_material"],
                    sub["description"],
                    sub["success_indicated"],
                )
                substitutions_found += 1

        logger.info("Found %d substitution attempts", substitutions_found)


def _detect_substitution_in_patent(
    patent: dict, material: CriticalRawMaterial
) -> list[dict]:
    """
    Detect substitution attempts for a specific material in a patent.

    Returns:
        List of substitution dicts with original_material, substitute_material,
        description, and success_indicated
    """
    title = patent.get("title", "")
    abstract = patent.get("abstract", "")
    text = f"{title} {abstract}"
    text_lower = text.lower()

    substitutions = []

    # Strategy 1: Pattern matching for explicit substitution language
    for term in material.search_terms():
        if len(term) < 3:
            continue
        term_lower = term.lower()
        if term_lower not in text_lower:
            continue

        for pattern_template in SUBSTITUTION_PATTERNS:
            pattern = pattern_template.format(material=re.escape(term_lower))
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                # Try to identify what the substitute is
                substitute = _extract_substitute_from_context(
                    text_lower, match.start(), match.end(), material
                )
                substitutions.append({
                    "original_material": material.name,
                    "substitute_material": substitute or "unspecified alternative",
                    "description": (
                        f"Patent '{title}' contains substitution language: "
                        f"'{match.group()}'"
                    ),
                    "success_indicated": _check_success_indicators(text_lower),
                })
                break  # One match per pattern is enough
            if substitutions:
                break

    # Strategy 2: Known substitution pairs
    known_subs = KNOWN_SUBSTITUTIONS.get(material.name, [])
    for sub in known_subs:
        if sub.lower() in text_lower and any(
            kw in text_lower for kw in [
                "substitute", "alternative", "replace", "instead",
                "free", "without", "reduced",
            ]
        ):
            substitutions.append({
                "original_material": material.name,
                "substitute_material": sub,
                "description": (
                    f"Patent '{title}' mentions known substitute "
                    f"'{sub}' for {material.name}"
                ),
                "success_indicated": _check_success_indicators(text_lower),
            })

    # Deduplicate
    seen = set()
    unique_subs = []
    for sub in substitutions:
        key = (sub["original_material"], sub["substitute_material"])
        if key not in seen:
            seen.add(key)
            unique_subs.append(sub)

    return unique_subs


def _extract_substitute_from_context(
    text: str, start: int, end: int, material: CriticalRawMaterial
) -> str | None:
    """Try to extract what material is being used as a substitute from surrounding text."""
    # Look at words after "with", "by", or near the match
    context_after = text[end:end + 100]
    context_before = text[max(0, start - 100):start]

    # Check for "replaced by/with X" pattern
    replaced_by = re.search(r"(?:by|with)\s+(\w[\w\s]{2,30}?)(?:\s+(?:in|for|as|to|,|\.))", context_after)
    if replaced_by:
        return replaced_by.group(1).strip()

    # Check known substitutes for this material
    known_subs = KNOWN_SUBSTITUTIONS.get(material.name, [])
    full_context = f"{context_before} {context_after}"
    for sub in known_subs:
        if sub.lower() in full_context:
            return sub

    return None


def _check_success_indicators(text: str) -> bool:
    """Check if the patent text indicates the substitution was successful."""
    success_phrases = [
        "successfully", "improved", "enhanced", "superior",
        "comparable performance", "equivalent", "effective replacement",
        "maintained", "without loss", "no degradation",
    ]
    return any(phrase in text for phrase in success_phrases)


def get_substitution_summary() -> dict:
    """
    Get a summary of all detected substitution attempts.

    Returns:
        dict mapping material_name -> list of substitution info dicts
    """
    with get_db() as conn:
        rows = conn.execute("""
            SELECT sa.*, p.title, p.url
            FROM substitution_attempts sa
            JOIN patents p ON sa.patent_id = p.patent_id
            ORDER BY sa.original_material, sa.substitute_material
        """).fetchall()

        summary = defaultdict(list)
        for row in rows:
            summary[row["original_material"]].append({
                "patent_id": row["patent_id"],
                "patent_title": row["title"],
                "patent_url": row["url"],
                "substitute": row["substitute_material"],
                "description": row["description"],
                "success_indicated": bool(row["success_indicated"]),
            })

        return dict(summary)
