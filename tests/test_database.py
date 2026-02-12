"""Tests for the database module."""

import tempfile
from pathlib import Path

from crm_patent_analyzer.data.database import (
    get_db,
    init_db,
    upsert_patent,
    upsert_patent_material,
    upsert_substitution,
    upsert_supply_chain_link,
)


def get_test_db():
    """Create a temporary database for testing."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = Path(tmp.name)
    tmp.close()
    init_db(db_path)
    return db_path


def test_init_db():
    db_path = get_test_db()
    with get_db(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in tables}
        assert "patents" in table_names
        assert "patent_materials" in table_names
        assert "supply_chain_links" in table_names
        assert "substitution_attempts" in table_names


def test_upsert_patent():
    db_path = get_test_db()
    with get_db(db_path) as conn:
        patent_data = {
            "patent_id": "US10000001",
            "title": "Test Patent",
            "abstract": "A test patent abstract",
            "assignee": "Test Corp",
            "inventors": "John Doe",
            "filing_date": "2023-01-01",
            "publication_date": "2023-06-01",
            "cpc_codes": ["H01M4/525"],
            "url": "https://patents.google.com/patent/US10000001",
        }
        pid = upsert_patent(conn, patent_data)
        assert pid == "US10000001"

        row = conn.execute(
            "SELECT * FROM patents WHERE patent_id = ?", (pid,)
        ).fetchone()
        assert row["title"] == "Test Patent"


def test_upsert_patent_material():
    db_path = get_test_db()
    with get_db(db_path) as conn:
        upsert_patent(conn, {
            "patent_id": "US10000001",
            "title": "Test",
        })
        upsert_patent_material(
            conn, "US10000001", "Cobalt", "cobalt",
            usage_type="good", usage_description="Used in cathode",
            confidence=0.85,
        )
        row = conn.execute(
            "SELECT * FROM patent_materials WHERE patent_id = ? AND material_name = ?",
            ("US10000001", "Cobalt"),
        ).fetchone()
        assert row["usage_type"] == "good"
        assert row["confidence"] == 0.85


def test_upsert_supply_chain_link():
    db_path = get_test_db()
    with get_db(db_path) as conn:
        for pid in ["US1", "US2"]:
            upsert_patent(conn, {"patent_id": pid, "title": f"Patent {pid}"})

        upsert_supply_chain_link(
            conn, "US1", "US2", "material_in_good",
            "Cobalt refined then used in battery", 0.8,
        )
        row = conn.execute(
            "SELECT * FROM supply_chain_links WHERE upstream_patent_id = 'US1'"
        ).fetchone()
        assert row["downstream_patent_id"] == "US2"
        assert row["link_type"] == "material_in_good"


def test_upsert_substitution():
    db_path = get_test_db()
    with get_db(db_path) as conn:
        upsert_patent(conn, {"patent_id": "US1", "title": "Test"})
        upsert_substitution(
            conn, "US1", "Cobalt", "Iron",
            "Replacing cobalt with iron in cathode", True,
        )
        row = conn.execute(
            "SELECT * FROM substitution_attempts WHERE patent_id = 'US1'"
        ).fetchone()
        assert row["original_material"] == "Cobalt"
        assert row["substitute_material"] == "Iron"
        assert row["success_indicated"] == 1
