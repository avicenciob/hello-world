"""SQLite database for storing patent data, analysis results, and supply chain mappings."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from crm_patent_analyzer.config import DATABASE_PATH


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = str(db_path or DATABASE_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db(db_path: Path | None = None):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | None = None):
    """Initialize the database schema."""
    with get_db(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS patents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patent_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                abstract TEXT,
                assignee TEXT,
                inventors TEXT,
                filing_date TEXT,
                publication_date TEXT,
                grant_date TEXT,
                cpc_codes TEXT,
                url TEXT,
                source TEXT DEFAULT 'google_patents',
                raw_data TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS patent_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patent_id TEXT NOT NULL,
                material_name TEXT NOT NULL,
                matched_term TEXT,
                usage_type TEXT CHECK(usage_type IN ('good', 'manufacturing', 'unknown')),
                usage_description TEXT,
                confidence REAL DEFAULT 0.0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (patent_id) REFERENCES patents(patent_id),
                UNIQUE(patent_id, material_name)
            );

            CREATE TABLE IF NOT EXISTS supply_chain_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upstream_patent_id TEXT NOT NULL,
                downstream_patent_id TEXT NOT NULL,
                link_type TEXT CHECK(link_type IN ('material_in_good', 'material_in_process', 'good_in_good', 'process_in_process')),
                link_description TEXT,
                confidence REAL DEFAULT 0.0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (upstream_patent_id) REFERENCES patents(patent_id),
                FOREIGN KEY (downstream_patent_id) REFERENCES patents(patent_id),
                UNIQUE(upstream_patent_id, downstream_patent_id)
            );

            CREATE TABLE IF NOT EXISTS substitution_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patent_id TEXT NOT NULL,
                original_material TEXT NOT NULL,
                substitute_material TEXT NOT NULL,
                description TEXT,
                success_indicated INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (patent_id) REFERENCES patents(patent_id),
                UNIQUE(patent_id, original_material, substitute_material)
            );

            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_type TEXT NOT NULL,
                material_name TEXT,
                started_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT,
                patents_found INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running'
            );

            CREATE INDEX IF NOT EXISTS idx_patents_patent_id ON patents(patent_id);
            CREATE INDEX IF NOT EXISTS idx_patents_publication_date ON patents(publication_date);
            CREATE INDEX IF NOT EXISTS idx_patent_materials_patent_id ON patent_materials(patent_id);
            CREATE INDEX IF NOT EXISTS idx_patent_materials_material ON patent_materials(material_name);
            CREATE INDEX IF NOT EXISTS idx_supply_chain_upstream ON supply_chain_links(upstream_patent_id);
            CREATE INDEX IF NOT EXISTS idx_supply_chain_downstream ON supply_chain_links(downstream_patent_id);
            CREATE INDEX IF NOT EXISTS idx_substitution_patent ON substitution_attempts(patent_id);
            CREATE INDEX IF NOT EXISTS idx_substitution_original ON substitution_attempts(original_material);
        """)


def upsert_patent(conn: sqlite3.Connection, patent_data: dict) -> str:
    """Insert or update a patent record. Returns the patent_id."""
    patent_id = patent_data["patent_id"]
    conn.execute("""
        INSERT INTO patents (patent_id, title, abstract, assignee, inventors,
                            filing_date, publication_date, grant_date, cpc_codes,
                            url, source, raw_data, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(patent_id) DO UPDATE SET
            title=excluded.title, abstract=excluded.abstract,
            assignee=excluded.assignee, inventors=excluded.inventors,
            filing_date=excluded.filing_date, publication_date=excluded.publication_date,
            grant_date=excluded.grant_date, cpc_codes=excluded.cpc_codes,
            url=excluded.url, raw_data=excluded.raw_data,
            updated_at=datetime('now')
    """, (
        patent_id, patent_data.get("title", ""), patent_data.get("abstract", ""),
        patent_data.get("assignee", ""), patent_data.get("inventors", ""),
        patent_data.get("filing_date"), patent_data.get("publication_date"),
        patent_data.get("grant_date"),
        json.dumps(patent_data.get("cpc_codes", [])),
        patent_data.get("url", ""),
        patent_data.get("source", "google_patents"),
        json.dumps(patent_data.get("raw_data", {})),
    ))
    return patent_id


def upsert_patent_material(conn: sqlite3.Connection, patent_id: str,
                           material_name: str, matched_term: str,
                           usage_type: str = "unknown",
                           usage_description: str = "",
                           confidence: float = 0.0):
    conn.execute("""
        INSERT INTO patent_materials (patent_id, material_name, matched_term,
                                     usage_type, usage_description, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(patent_id, material_name) DO UPDATE SET
            usage_type=excluded.usage_type,
            usage_description=excluded.usage_description,
            confidence=excluded.confidence
    """, (patent_id, material_name, matched_term, usage_type, usage_description, confidence))


def upsert_supply_chain_link(conn: sqlite3.Connection, upstream_id: str,
                             downstream_id: str, link_type: str,
                             link_description: str = "", confidence: float = 0.0):
    conn.execute("""
        INSERT INTO supply_chain_links (upstream_patent_id, downstream_patent_id,
                                       link_type, link_description, confidence)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(upstream_patent_id, downstream_patent_id) DO UPDATE SET
            link_type=excluded.link_type,
            link_description=excluded.link_description,
            confidence=excluded.confidence
    """, (upstream_id, downstream_id, link_type, link_description, confidence))


def upsert_substitution(conn: sqlite3.Connection, patent_id: str,
                        original_material: str, substitute_material: str,
                        description: str = "", success_indicated: bool = False):
    conn.execute("""
        INSERT INTO substitution_attempts (patent_id, original_material,
                                          substitute_material, description, success_indicated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(patent_id, original_material, substitute_material) DO UPDATE SET
            description=excluded.description,
            success_indicated=excluded.success_indicated
    """, (patent_id, original_material, substitute_material, description,
          int(success_indicated)))


def start_scan(conn: sqlite3.Connection, scan_type: str,
               material_name: str | None = None) -> int:
    cursor = conn.execute("""
        INSERT INTO scan_history (scan_type, material_name) VALUES (?, ?)
    """, (scan_type, material_name))
    return cursor.lastrowid


def complete_scan(conn: sqlite3.Connection, scan_id: int, patents_found: int,
                  status: str = "completed"):
    conn.execute("""
        UPDATE scan_history SET completed_at=datetime('now'),
               patents_found=?, status=? WHERE id=?
    """, (patents_found, status, scan_id))
