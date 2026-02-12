"""Tests for the patent usage classifier."""

from crm_patent_analyzer.analysis.classifier import classify_patent
from crm_patent_analyzer.data.critical_raw_materials import find_material


def test_classify_good_patent():
    """Patent about a device should be classified as 'good'."""
    material = find_material("Cobalt")
    patent = {
        "patent_id": "US10000001",
        "title": "Lithium cobalt oxide battery cell for electric vehicles",
        "abstract": "A battery cell comprising a cathode containing lithium cobalt oxide",
        "cpc_codes": ["H01M4/525", "H01M10/052"],
    }
    result = classify_patent(patent, material)
    assert result["usage_type"] == "good"
    assert result["confidence"] > 0


def test_classify_manufacturing_patent():
    """Patent about a process should be classified as 'manufacturing'."""
    material = find_material("Tungsten")
    patent = {
        "patent_id": "US10000002",
        "title": "Method of producing tungsten carbide cutting tools by sintering",
        "abstract": "A method for manufacturing tungsten carbide tools by sintering powder",
        "cpc_codes": ["C22B34/36", "B22F3/10"],
    }
    result = classify_patent(patent, material)
    assert result["usage_type"] == "manufacturing"
    assert result["confidence"] > 0


def test_classify_unknown_patent():
    """Patent with no clear signals should be unknown."""
    material = find_material("Baryte")
    patent = {
        "patent_id": "US10000003",
        "title": "Baryte",
        "abstract": "",
        "cpc_codes": [],
    }
    result = classify_patent(patent, material)
    assert result["usage_type"] == "unknown"


def test_classify_returns_description():
    material = find_material("Gallium")
    patent = {
        "patent_id": "US10000004",
        "title": "Gallium nitride semiconductor device",
        "abstract": "A high-power device comprising a gallium nitride substrate layer",
        "cpc_codes": ["H01L29/20"],
    }
    result = classify_patent(patent, material)
    assert result["usage_description"]
    assert len(result["usage_description"]) > 0
