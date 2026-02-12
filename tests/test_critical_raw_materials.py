"""Tests for the Critical Raw Materials data module."""

from crm_patent_analyzer.data.critical_raw_materials import (
    EU_CRITICAL_RAW_MATERIALS,
    detect_materials_in_text,
    find_material,
    get_all_materials,
)


def test_all_materials_count():
    """Verify we have all 31 EU CRMs defined."""
    materials = get_all_materials()
    assert len(materials) >= 30


def test_each_material_has_required_fields():
    for mat in EU_CRITICAL_RAW_MATERIALS:
        assert mat.name, "Material must have a name"
        assert mat.category, f"{mat.name} must have a category"
        assert len(mat.search_terms()) >= 1, f"{mat.name} must have at least 1 search term"


def test_find_material_by_name():
    mat = find_material("Cobalt")
    assert mat is not None
    assert mat.name == "Cobalt"
    assert mat.symbol == "Co"


def test_find_material_by_alias():
    mat = find_material("tungsten carbide")
    assert mat is not None
    assert mat.name == "Tungsten"


def test_find_material_case_insensitive():
    mat = find_material("LITHIUM")
    assert mat is not None
    assert mat.name == "Lithium"


def test_find_unknown_material():
    mat = find_material("unobtanium")
    assert mat is None


def test_detect_materials_in_text():
    text = "This patent describes a lithium cobalt oxide cathode for batteries"
    found = detect_materials_in_text(text)
    material_names = {m.name for m, _ in found}
    assert "Lithium" in material_names or "Cobalt" in material_names


def test_detect_materials_no_false_positives():
    text = "This is a simple text about everyday objects"
    found = detect_materials_in_text(text)
    assert len(found) == 0


def test_search_terms_include_name_and_aliases():
    mat = find_material("Tungsten")
    terms = mat.search_terms()
    assert "Tungsten" in terms
    assert "wolfram" in terms or "tungsten carbide" in terms
