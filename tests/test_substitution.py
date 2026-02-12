"""Tests for the substitution detection module."""

from crm_patent_analyzer.analysis.substitution import _detect_substitution_in_patent
from crm_patent_analyzer.data.critical_raw_materials import find_material


def test_detect_explicit_replacement():
    material = find_material("Cobalt")
    patent = {
        "patent_id": "US1",
        "title": "Cobalt-free cathode material for lithium batteries",
        "abstract": "A cathode material replacing cobalt with iron phosphate",
    }
    subs = _detect_substitution_in_patent(patent, material)
    assert len(subs) > 0
    assert subs[0]["original_material"] == "Cobalt"


def test_detect_known_substitute_pair():
    material = find_material("Lithium")
    patent = {
        "patent_id": "US2",
        "title": "Sodium-ion battery as alternative to lithium-ion",
        "abstract": "Using sodium as a substitute for lithium in rechargeable batteries",
    }
    subs = _detect_substitution_in_patent(patent, material)
    assert len(subs) > 0
    assert any(s["substitute_material"] == "sodium" for s in subs)


def test_no_false_substitution():
    material = find_material("Cobalt")
    patent = {
        "patent_id": "US3",
        "title": "Improved cobalt oxide cathode performance",
        "abstract": "Enhanced cobalt oxide cathode with improved cycling stability",
    }
    subs = _detect_substitution_in_patent(patent, material)
    assert len(subs) == 0


def test_detect_material_free_pattern():
    material = find_material("Rare Earth Elements")
    patent = {
        "patent_id": "US4",
        "title": "Rare earth free permanent magnet design",
        "abstract": "A permanent magnet without rare earth elements using ferrite",
    }
    subs = _detect_substitution_in_patent(patent, material)
    assert len(subs) > 0
