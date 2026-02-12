"""
=============================================================================
CRM PATENT SUPPLY CHAIN MAPPER - Single-File Version
=============================================================================
EU Critical Raw Materials Patent Intelligence Tool

HOW TO RUN:
    1. Install Python 3.11+ from https://www.python.org/downloads/
       (check "Add python.exe to PATH" during install)
    2. Open this file in Spyder, VS Code, or any Python IDE
    3. Set your SERPAPI_KEY below (line ~30)
    4. Run this file (F5 in Spyder, or: python crm_all_in_one.py)
    5. Open http://localhost:8050 in your browser

PREREQUISITES (run once in PowerShell / terminal):
    pip install requests flask

=============================================================================
"""

# ===================== CONFIGURATION - EDIT THIS =====================
SERPAPI_KEY = "1accd4c96bf783ae8b0bfd3adba7a698e1e1d1dddca917f15922c7d980c01838"
WEB_PORT = 8050
# =====================================================================

import json
import logging
import os
import re
import sqlite3
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent

os.environ["SERPAPI_KEY"] = SERPAPI_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("crm_patent_analyzer")

# Try importing required packages
try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

try:
    from flask import Flask, jsonify, render_template_string, request
except ImportError:
    print("ERROR: 'flask' not installed. Run: pip install flask")
    sys.exit(1)

# ===========================================================================
# SECTION 1: EU CRITICAL RAW MATERIALS (2023)
# ===========================================================================

@dataclass
class CriticalRawMaterial:
    name: str
    symbol: str
    aliases: list = field(default_factory=list)
    cpc_codes: list = field(default_factory=list)
    applications: list = field(default_factory=list)
    category: str = ""

    def search_terms(self):
        terms = [self.name]
        if self.symbol:
            terms.append(self.symbol)
        terms.extend(self.aliases)
        return list(set(terms))


EU_CRITICAL_RAW_MATERIALS = [
    CriticalRawMaterial("Antimony", "Sb",
        ["stibium","antimony trioxide","Sb2O3"],
        ["C22B30/02"], ["flame retardants","batteries","semiconductors"], "metal"),
    CriticalRawMaterial("Arsenic", "As",
        ["gallium arsenide","GaAs"],
        ["C22B30/04"], ["semiconductors","alloys"], "metalloid"),
    CriticalRawMaterial("Baryte", "BaSO4",
        ["barite","barium sulfate","heavy spar"],
        ["C01F11/46"], ["drilling fluids","radiation shielding"], "mineral"),
    CriticalRawMaterial("Bauxite", "",
        ["aluminium ore","aluminum ore","gibbsite"],
        ["C22B21/00"], ["aluminium production","refractories"], "mineral"),
    CriticalRawMaterial("Beryllium", "Be",
        ["beryllium copper","BeCu","beryllium oxide"],
        ["C22B59/00"], ["aerospace","electronics","nuclear"], "metal"),
    CriticalRawMaterial("Bismuth", "Bi",
        ["bismuth oxide","bismuth telluride"],
        ["C22B30/06"], ["pharmaceuticals","thermoelectrics"], "metal"),
    CriticalRawMaterial("Boron", "B",
        ["borate","boron carbide","B4C","boron nitride","borax"],
        ["C01B35/00"], ["glass","ceramics","detergents"], "metalloid"),
    CriticalRawMaterial("Cobalt", "Co",
        ["cobalt oxide","CoO","lithium cobalt oxide","LiCoO2"],
        ["C22B23/00","H01M4/525"], ["batteries","superalloys","catalysts","magnets"], "metal"),
    CriticalRawMaterial("Coking coal", "",
        ["metallurgical coal","met coal"],
        ["C10B57/00"], ["steelmaking","coke production"], "mineral"),
    CriticalRawMaterial("Copper", "Cu",
        ["cuprum","copper oxide","CuO","copper sulfate"],
        ["C22B15/00"], ["electrical wiring","electronics","renewable energy"], "metal"),
    CriticalRawMaterial("Feldspar", "",
        ["orthoclase","plagioclase","microcline"],
        ["C04B33/00"], ["ceramics","glassmaking"], "mineral"),
    CriticalRawMaterial("Fluorspar", "CaF2",
        ["fluorite","calcium fluoride"],
        ["C01F11/22"], ["steelmaking flux","hydrofluoric acid"], "mineral"),
    CriticalRawMaterial("Gallium", "Ga",
        ["gallium arsenide","GaAs","gallium nitride","GaN"],
        ["C22B58/00","H01L29/20"], ["semiconductors","LEDs","solar cells","5G"], "metal"),
    CriticalRawMaterial("Germanium", "Ge",
        ["germanium dioxide","GeO2"],
        ["C22B41/00"], ["fiber optics","infrared optics","semiconductors"], "metalloid"),
    CriticalRawMaterial("Hafnium", "Hf",
        ["hafnium oxide","HfO2"],
        ["C22B34/14"], ["nuclear reactors","superalloys"], "metal"),
    CriticalRawMaterial("Helium", "He",
        ["liquid helium","helium-3"],
        ["C01B23/00"], ["cryogenics","MRI","welding"], "element"),
    CriticalRawMaterial("Lithium", "Li",
        ["lithium carbonate","Li2CO3","lithium hydroxide","LiOH","spodumene","LiFePO4"],
        ["C22B26/12","H01M10/052"], ["batteries","ceramics","glass","pharmaceuticals"], "metal"),
    CriticalRawMaterial("Magnesium", "Mg",
        ["magnesium alloy","magnesium oxide","MgO","magnesia"],
        ["C22B26/20"], ["lightweight alloys","refractories"], "metal"),
    CriticalRawMaterial("Manganese", "Mn",
        ["manganese dioxide","MnO2","ferromanganese"],
        ["C22B47/00","H01M4/50"], ["steelmaking","batteries"], "metal"),
    CriticalRawMaterial("Natural graphite", "C",
        ["graphite","flake graphite","crystalline graphite"],
        ["C01B32/20","H01M4/587"], ["batteries","refractories","lubricants"], "mineral"),
    CriticalRawMaterial("Nickel", "Ni",
        ["nickel sulfate","NiSO4","nickel oxide"],
        ["C22B23/00","H01M4/525"], ["stainless steel","batteries","superalloys"], "metal"),
    CriticalRawMaterial("Niobium", "Nb",
        ["columbium","ferroniobium","niobium oxide"],
        ["C22B34/24"], ["steel alloys","superconductors","capacitors"], "metal"),
    CriticalRawMaterial("Phosphate rock", "",
        ["phosphorite","apatite","rock phosphate"],
        ["C05B1/00"], ["fertilizers","phosphoric acid"], "mineral"),
    CriticalRawMaterial("Platinum Group Metals", "PGM",
        ["platinum","Pt","palladium","Pd","rhodium","Rh","ruthenium","Ru","iridium","Ir"],
        ["C22B11/00","B01J23/40"], ["catalytic converters","fuel cells","electronics"], "metal"),
    CriticalRawMaterial("Rare Earth Elements", "REE",
        ["rare earth","lanthanum","cerium","neodymium","Nd","dysprosium","NdFeB","neodymium magnet",
         "yttrium","scandium","praseodymium","samarium","europium","gadolinium","terbium"],
        ["C22B59/00","H01F1/057"], ["magnets","catalysts","wind turbines","phosphors"], "metal"),
    CriticalRawMaterial("Silicon metal", "Si",
        ["polysilicon","silicon wafer","ferrosilicon","silicon carbide","SiC"],
        ["C01B33/00"], ["semiconductors","solar cells","silicones"], "metalloid"),
    CriticalRawMaterial("Strontium", "Sr",
        ["strontium carbonate","celestite"],
        ["C01F11/00"], ["pyrotechnics","ferrite magnets"], "metal"),
    CriticalRawMaterial("Tantalum", "Ta",
        ["tantalum pentoxide","Ta2O5","coltan","tantalite"],
        ["C22B34/24","H01G9/042"], ["capacitors","surgical instruments","jet engines"], "metal"),
    CriticalRawMaterial("Titanium", "Ti",
        ["titanium dioxide","TiO2","Ti-6Al-4V","rutile","ilmenite"],
        ["C22B34/12"], ["aerospace","pigments","medical implants","3D printing"], "metal"),
    CriticalRawMaterial("Tungsten", "W",
        ["wolfram","tungsten carbide","WC","scheelite","wolframite"],
        ["C22B34/36","B23B27/14"], ["cutting tools","mining","lighting"], "metal"),
    CriticalRawMaterial("Vanadium", "V",
        ["vanadium pentoxide","V2O5","ferrovanadium","vanadium redox battery"],
        ["C22B34/22","H01M8/18"], ["steel alloys","flow batteries","catalysts"], "metal"),
]

CRM_BY_NAME = {m.name: m for m in EU_CRITICAL_RAW_MATERIALS}
ALL_CRM_SEARCH_TERMS = {}
for _mat in EU_CRITICAL_RAW_MATERIALS:
    for _term in _mat.search_terms():
        ALL_CRM_SEARCH_TERMS[_term.lower()] = _mat.name


def detect_materials_in_text(text):
    text_lower = text.lower()
    found = []
    seen = set()
    for term in sorted(ALL_CRM_SEARCH_TERMS.keys(), key=len, reverse=True):
        mat_name = ALL_CRM_SEARCH_TERMS[term]
        if mat_name not in seen and len(term) >= 3 and term in text_lower:
            found.append((CRM_BY_NAME[mat_name], term))
            seen.add(mat_name)
    return found


# ===========================================================================
# SECTION 2: DATABASE
# ===========================================================================

DB_PATH = Path(__file__).parent / "crm_patents.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
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
                usage_type TEXT CHECK(usage_type IN ('good','manufacturing','unknown')),
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
                link_type TEXT,
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
        """)


def upsert_patent(conn, data):
    pid = data["patent_id"]
    conn.execute("""
        INSERT INTO patents (patent_id,title,abstract,assignee,inventors,
            filing_date,publication_date,grant_date,cpc_codes,url,source,raw_data,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
        ON CONFLICT(patent_id) DO UPDATE SET
            title=excluded.title, abstract=excluded.abstract,
            assignee=excluded.assignee, updated_at=datetime('now')
    """, (pid, data.get("title",""), data.get("abstract",""),
          data.get("assignee",""), data.get("inventors",""),
          data.get("filing_date"), data.get("publication_date"),
          data.get("grant_date"), json.dumps(data.get("cpc_codes",[])),
          data.get("url",""), data.get("source","google_patents"),
          json.dumps(data.get("raw_data",{}))))
    return pid


def upsert_patent_material(conn, patent_id, material_name, matched_term,
                           usage_type="unknown", usage_description="", confidence=0.0):
    conn.execute("""
        INSERT INTO patent_materials (patent_id,material_name,matched_term,
            usage_type,usage_description,confidence)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(patent_id,material_name) DO UPDATE SET
            usage_type=excluded.usage_type, usage_description=excluded.usage_description,
            confidence=excluded.confidence
    """, (patent_id, material_name, matched_term, usage_type, usage_description, confidence))


def upsert_supply_chain_link(conn, up_id, down_id, link_type, desc="", confidence=0.0):
    conn.execute("""
        INSERT INTO supply_chain_links (upstream_patent_id,downstream_patent_id,
            link_type,link_description,confidence)
        VALUES (?,?,?,?,?)
        ON CONFLICT(upstream_patent_id,downstream_patent_id) DO UPDATE SET
            link_type=excluded.link_type, confidence=excluded.confidence
    """, (up_id, down_id, link_type, desc, confidence))


def upsert_substitution(conn, patent_id, original, substitute, desc="", success=False):
    conn.execute("""
        INSERT INTO substitution_attempts (patent_id,original_material,
            substitute_material,description,success_indicated)
        VALUES (?,?,?,?,?)
        ON CONFLICT(patent_id,original_material,substitute_material) DO UPDATE SET
            description=excluded.description, success_indicated=excluded.success_indicated
    """, (patent_id, original, substitute, desc, int(success)))


# ===========================================================================
# SECTION 3: PATENT SEARCH (SerpApi / Google Patents)
# ===========================================================================

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
GOOGLE_PATENTS_BASE = "https://patents.google.com/patent/"


def search_patents_api(query, after_date=None, num_results=10):
    key = os.environ.get("SERPAPI_KEY", "")
    if not key:
        logger.warning("No SERPAPI_KEY set. Skipping search.")
        return {"patents": [], "total_results": 0}

    params = {"engine": "google_patents", "q": query, "api_key": key, "num": min(num_results, 10)}
    if after_date:
        params["after"] = f"publication:{after_date}"

    try:
        resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error("Search failed: %s", e)
        return {"patents": [], "total_results": 0}

    patents = []
    for r in data.get("organic_results", []):
        pid = r.get("patent_id", "")
        if not pid:
            link = r.get("link", "")
            if "/patent/" in link:
                pid = link.split("/patent/")[-1].split("/")[0]
        if pid:
            patents.append({
                "patent_id": pid,
                "title": r.get("title", ""),
                "abstract": r.get("snippet", ""),
                "assignee": r.get("assignee", ""),
                "inventors": r.get("inventor", ""),
                "filing_date": r.get("filing_date"),
                "publication_date": r.get("publication_date") or r.get("date"),
                "grant_date": r.get("grant_date"),
                "cpc_codes": r.get("cpc_codes", []),
                "url": r.get("link", f"{GOOGLE_PATENTS_BASE}{pid}"),
                "source": "google_patents",
                "raw_data": r,
            })

    return {"patents": patents, "total_results": data.get("search_information", {}).get("total_results", len(patents))}


def search_material_patents(material, after_date=None, max_results=50):
    all_patents = {}
    terms = material.search_terms()[:5]
    for term in terms:
        if len(all_patents) >= max_results:
            break
        for query in [f'"{term}"',
                      f'"{term}" AND (manufacturing OR process OR production)',
                      f'"{term}" AND (device OR apparatus OR composition)']:
            if len(all_patents) >= max_results:
                break
            result = search_patents_api(query, after_date=after_date)
            for p in result["patents"]:
                all_patents.setdefault(p["patent_id"], p)
            time.sleep(1)
    return list(all_patents.values())[:max_results]


# ===========================================================================
# SECTION 4: CLASSIFIER (Good vs Manufacturing)
# ===========================================================================

GOOD_KW = ["comprising","consisting of","containing","device","apparatus","system",
    "component","electrode","cathode","anode","battery","cell","sensor","catalyst",
    "magnet","layer","coating","alloy","composite","semiconductor","wafer"]

MFG_KW = ["method of","process for","method for","manufacturing","fabricating",
    "producing","preparing","synthesizing","smelting","refining","extracting",
    "etching","doping","annealing","sintering","electroplating","sputtering",
    "casting","molding","heat treatment","leaching"]

PROCESS_CPC = ["C22B","C22C","C23C","C25D","C25B","B22D","B22F","C01B","C01G","C04B","C30B"]
PRODUCT_CPC = ["H01M","H01L","H01F","H01G","H02K","B60L","A61K","A61L","G02B","F03D"]


def classify_patent(patent, material):
    title = patent.get("title", "").lower()
    abstract = patent.get("abstract", "").lower()
    text = f"{title} {abstract}"
    cpc_codes = patent.get("cpc_codes", [])
    if isinstance(cpc_codes, str):
        try: cpc_codes = json.loads(cpc_codes)
        except: cpc_codes = []

    g_score = sum(1.0 for kw in GOOD_KW if kw in text)
    m_score = sum(1.0 for kw in MFG_KW if kw in text)

    if any(kw in title for kw in ["method","process","manufacturing","producing"]):
        m_score += 3.0
    if any(kw in title for kw in ["device","apparatus","system","battery","cell","composition"]):
        g_score += 3.0

    for cpc in cpc_codes:
        c = str(cpc)
        if any(c.startswith(p) for p in PROCESS_CPC): m_score += 2.0
        if any(c.startswith(p) for p in PRODUCT_CPC): g_score += 2.0

    total = g_score + m_score
    if total == 0:
        return {"usage_type": "unknown", "usage_description": "Insufficient signals", "confidence": 0.0}

    if g_score > m_score:
        return {"usage_type": "good",
                "usage_description": f"{material.name} is part of the product in: {patent.get('title','')}",
                "confidence": min(g_score / total, 0.95)}
    elif m_score > g_score:
        return {"usage_type": "manufacturing",
                "usage_description": f"{material.name} is used in manufacturing process: {patent.get('title','')}",
                "confidence": min(m_score / total, 0.95)}
    else:
        return {"usage_type": "unknown", "usage_description": "Equal signals", "confidence": 0.5}


# ===========================================================================
# SECTION 5: SUPPLY CHAIN MAPPER
# ===========================================================================

KNOWN_CHAINS = {
    ("C22B","H01M"): "Refined metal used in battery",
    ("C22B","H01L"): "Refined material in semiconductor",
    ("C22B","H01F"): "Refined metal in magnet",
    ("C22B","C22C"): "Refined metal in alloy",
    ("C01B","H01M"): "Synthesized material in battery",
    ("C01G","H01M"): "Metal compound in battery cathode",
    ("H01M","B60L"): "Battery in electric vehicle",
    ("H01F","H02K"): "Magnet in electric motor",
    ("H02K","F03D"): "Motor in wind turbine",
    ("H02K","B60L"): "Motor in electric vehicle",
}

STAGE_ORDER = {"extraction": 0, "refinement": 1, "component": 2, "system": 3, "product": 4}
STAGE_CPC = {
    "extraction": ["C22B","C01B","C01G"],
    "refinement": ["C22C","C23C","C25D","C30B"],
    "component": ["H01M","H01L","H01F","H01G"],
    "system": ["H02K","H02J","F03D","B60L"],
    "product": ["A61K","A61L","B60","H04"],
}


def get_stage(patent):
    cpcs = set()
    cpc_raw = patent.get("cpc_codes", "[]")
    if isinstance(cpc_raw, str):
        try: cpc_raw = json.loads(cpc_raw)
        except: cpc_raw = []
    cpcs = {str(c)[:4] for c in cpc_raw if c}
    for stage, prefixes in STAGE_CPC.items():
        if any(p in cpcs for p in prefixes):
            return stage
    ut = patent.get("usage_type", "unknown")
    return "refinement" if ut == "manufacturing" else "component" if ut == "good" else "unknown"


def build_supply_chain():
    with get_db() as conn:
        patents = conn.execute("""
            SELECT p.patent_id, p.title, p.abstract, p.cpc_codes,
                   pm.material_name, pm.usage_type
            FROM patents p JOIN patent_materials pm ON p.patent_id = pm.patent_id
        """).fetchall()

        by_material = defaultdict(list)
        for r in patents:
            by_material[r["material_name"]].append(dict(r))

        links = 0
        for mat_name, pats in by_material.items():
            for i, up in enumerate(pats):
                up_cpcs = set()
                try: up_cpcs = {str(c)[:4] for c in json.loads(up.get("cpc_codes","[]")) if c}
                except: pass
                up_stage = get_stage(up)

                for down in pats[i+1:]:
                    if up["patent_id"] == down["patent_id"]:
                        continue
                    down_cpcs = set()
                    try: down_cpcs = {str(c)[:4] for c in json.loads(down.get("cpc_codes","[]")) if c}
                    except: pass
                    down_stage = get_stage(down)

                    link_desc = None
                    conf = 0.0
                    for uc in up_cpcs:
                        for dc in down_cpcs:
                            if (uc, dc) in KNOWN_CHAINS:
                                link_desc = KNOWN_CHAINS[(uc, dc)]
                                conf = 0.8
                                break
                        if link_desc: break

                    if not link_desc and up_stage in STAGE_ORDER and down_stage in STAGE_ORDER:
                        diff = STAGE_ORDER.get(down_stage, 0) - STAGE_ORDER.get(up_stage, 0)
                        if 0 < diff <= 2:
                            link_desc = f"{up_stage} -> {down_stage}"
                            conf = 0.5 if diff == 1 else 0.3

                    if link_desc:
                        lt = "material_in_good" if up.get("usage_type") == "manufacturing" else "good_in_good"
                        upsert_supply_chain_link(conn, up["patent_id"], down["patent_id"], lt, link_desc, conf)
                        links += 1

        logger.info("Created %d supply chain links", links)


# ===========================================================================
# SECTION 6: SUBSTITUTION DETECTOR
# ===========================================================================

SUBSTITUTION_PATTERNS = [
    r"(?:replace|replacing|replacement)\s+(?:of\s+)?{material}",
    r"{material}[\s-]*free",
    r"without\s+{material}",
    r"(?:alternative|substitute)\s+(?:for|to|of)\s+{material}",
    r"(?:eliminating|reducing)\s+{material}",
    r"{material}\s+(?:replaced|substituted)\s+(?:by|with)",
]

KNOWN_SUBS = {
    "Cobalt": ["iron","manganese","nickel","aluminium"],
    "Lithium": ["sodium","potassium","zinc","magnesium"],
    "Rare Earth Elements": ["ferrite","iron nitride"],
    "Platinum Group Metals": ["iron","cobalt","nickel","carbon-based"],
    "Tungsten": ["molybdenum","titanium","ceramic"],
    "Nickel": ["iron","manganese","zinc"],
    "Copper": ["aluminium","aluminum","carbon nanotube"],
}


def detect_substitutions():
    with get_db() as conn:
        patents = conn.execute("""
            SELECT p.patent_id, p.title, p.abstract, pm.material_name
            FROM patents p JOIN patent_materials pm ON p.patent_id = pm.patent_id
        """).fetchall()

        count = 0
        for row in patents:
            material = CRM_BY_NAME.get(row["material_name"])
            if not material:
                continue
            text = f"{row['title'] or ''} {row['abstract'] or ''}".lower()

            for term in material.search_terms():
                if len(term) < 3 or term.lower() not in text:
                    continue
                for pat in SUBSTITUTION_PATTERNS:
                    pattern = pat.format(material=re.escape(term.lower()))
                    if re.search(pattern, text):
                        upsert_substitution(conn, row["patent_id"], material.name,
                            "unspecified alternative",
                            f"Substitution language found in: {row['title']}", False)
                        count += 1
                        break

            for sub in KNOWN_SUBS.get(material.name, []):
                if sub.lower() in text and any(kw in text for kw in
                    ["substitute","alternative","replace","free","without"]):
                    success = any(w in text for w in ["successfully","improved","enhanced","comparable"])
                    upsert_substitution(conn, row["patent_id"], material.name, sub,
                        f"Known substitute '{sub}' found in: {row['title']}", success)
                    count += 1

        logger.info("Found %d substitution entries", count)


# ===========================================================================
# SECTION 7: FULL PIPELINE
# ===========================================================================

def run_full_pipeline(incremental=True, lookback_days=30, material_name=None):
    logger.info("=" * 60)
    logger.info("CRM Patent Analysis Pipeline - %s", datetime.now().isoformat())
    logger.info("=" * 60)

    init_db()

    after_date = None
    if incremental:
        after_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y%m%d")

    materials = EU_CRITICAL_RAW_MATERIALS
    if material_name:
        mat = CRM_BY_NAME.get(material_name)
        if not mat:
            logger.error("Unknown material: %s", material_name)
            return
        materials = [mat]

    logger.info("[1/4] Searching patents...")
    with get_db() as conn:
        for mat in materials:
            logger.info("  Searching: %s", mat.name)
            patents = search_material_patents(mat, after_date=after_date, max_results=50)
            for p in patents:
                upsert_patent(conn, p)
                upsert_patent_material(conn, p["patent_id"], mat.name, mat.name)
            logger.info("    Found %d patents", len(patents))

    logger.info("[2/4] Classifying patents...")
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.*, pm.material_name, pm.matched_term
            FROM patents p JOIN patent_materials pm ON p.patent_id = pm.patent_id
            WHERE pm.usage_type = 'unknown'
        """).fetchall()
        for row in rows:
            mat = CRM_BY_NAME.get(row["material_name"])
            if not mat: continue
            result = classify_patent(dict(row), mat)
            upsert_patent_material(conn, row["patent_id"], mat.name,
                row["matched_term"] or mat.name,
                result["usage_type"], result["usage_description"], result["confidence"])

    logger.info("[3/4] Building supply chain map...")
    build_supply_chain()

    logger.info("[4/4] Detecting substitutions...")
    detect_substitutions()

    logger.info("Pipeline complete!")


# ===========================================================================
# SECTION 8: WEB DASHBOARD
# ===========================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>CRM Patent Supply Chain Mapper</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
:root{--bg1:#0f172a;--bg2:#1e293b;--bg3:#334155;--t1:#f1f5f9;--t2:#94a3b8;
--blue:#3b82f6;--green:#10b981;--amber:#f59e0b;--rose:#f43f5e;--purple:#8b5cf6;--border:#475569}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg1);color:var(--t1);overflow:hidden;height:100vh}
.layout{display:grid;grid-template-columns:280px 1fr 340px;grid-template-rows:60px 1fr;height:100vh}
.header{grid-column:1/-1;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 20px}
.header h1{font-size:16px;background:linear-gradient(135deg,var(--blue),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stats{display:flex;gap:20px}
.stat-val{font-size:18px;font-weight:700;color:var(--blue)}
.stat-lbl{font-size:10px;color:var(--t2);text-transform:uppercase}
.left{background:var(--bg2);border-right:1px solid var(--border);overflow-y:auto;padding:12px}
.section-title{font-size:11px;font-weight:600;color:var(--t2);text-transform:uppercase;letter-spacing:.05em;margin:12px 0 8px}
.mat-item{display:flex;align-items:center;justify-content:space-between;padding:6px 10px;border-radius:5px;cursor:pointer;font-size:12px;transition:background .2s}
.mat-item:hover{background:var(--bg3)}.mat-item.active{background:var(--blue);color:white}
.mat-count{background:var(--bg3);padding:1px 6px;border-radius:8px;font-size:10px;color:var(--t2)}
.mat-item.active .mat-count{background:rgba(255,255,255,.2);color:white}
select,input[type=range]{width:100%;padding:6px;background:var(--bg3);border:1px solid var(--border);border-radius:5px;color:var(--t1);font-size:12px;margin-bottom:8px}
.btn{padding:6px 12px;border-radius:5px;border:none;cursor:pointer;font-size:12px;width:100%;margin-top:6px}
.btn-blue{background:var(--blue);color:white}.btn-blue:hover{background:#2563eb}
.graph-area{position:relative;overflow:hidden}
#graph-svg{width:100%;height:100%}
.g-controls{position:absolute;top:12px;left:12px;display:flex;gap:6px;z-index:5}
.g-btn{padding:6px 10px;background:var(--bg2);border:1px solid var(--border);border-radius:5px;color:var(--t1);cursor:pointer;font-size:11px}
.legend{position:absolute;bottom:12px;left:12px;background:var(--bg2);border:1px solid var(--border);border-radius:6px;padding:10px 14px;z-index:5}
.legend-title{font-size:10px;color:var(--t2);text-transform:uppercase;margin-bottom:6px}
.legend-row{display:flex;align-items:center;gap:6px;font-size:11px;margin-bottom:3px}
.dot{width:8px;height:8px;border-radius:50%}
.right{background:var(--bg2);border-left:1px solid var(--border);overflow-y:auto;padding:12px}
.tabs{display:flex;border-bottom:1px solid var(--border);margin-bottom:12px}
.tab{padding:6px 14px;font-size:12px;color:var(--t2);cursor:pointer;border-bottom:2px solid transparent}
.tab.active{color:var(--blue);border-bottom-color:var(--blue)}
.tab-content{display:none}.tab-content.active{display:block}
.card{background:var(--bg3);border-radius:6px;padding:12px;margin-bottom:10px;border:1px solid var(--border)}
.card:hover{border-color:var(--blue)}
.card-title{font-size:13px;font-weight:600;margin-bottom:6px;line-height:1.3}
.card-title a{color:var(--t1);text-decoration:none}.card-title a:hover{color:var(--blue)}
.card-meta{font-size:11px;color:var(--t2);margin-bottom:4px}
.badge{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:500}
.b-good{background:rgba(16,185,129,.2);color:var(--green)}
.b-mfg{background:rgba(245,158,11,.2);color:var(--amber)}
.b-unk{background:rgba(148,163,184,.2);color:var(--t2)}
.b-sub{background:rgba(244,63,94,.2);color:var(--rose)}
.conf-bar{height:3px;background:var(--bg1);border-radius:2px;margin-top:6px;overflow:hidden}
.conf-fill{height:100%;border-radius:2px;background:var(--blue)}
.sub-card{background:var(--bg3);border-radius:6px;padding:12px;margin-bottom:10px;border-left:3px solid var(--rose)}
.arrow{color:var(--rose);font-weight:700;margin:0 4px}
.empty{text-align:center;padding:40px 20px;color:var(--t2)}
.empty h3{font-size:14px;color:var(--t1);margin-bottom:6px}
.empty p{font-size:12px;line-height:1.5}
.tooltip{position:absolute;background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:10px;font-size:11px;pointer-events:none;z-index:100;max-width:280px;box-shadow:0 4px 12px rgba(0,0,0,.3);display:none}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.node circle{stroke-width:2px;cursor:pointer}.node:hover circle{stroke:white;stroke-width:3px}
.node text{font-size:9px;fill:var(--t2);pointer-events:none}
.link{stroke-opacity:.4;fill:none}
</style>
</head>
<body>
<div class="layout">
<header class="header">
<div><h1>CRM Patent Supply Chain Mapper</h1><span style="font-size:11px;color:var(--t2)">EU Critical Raw Materials - Patent Intelligence</span></div>
<div class="stats">
<div><div class="stat-val" id="s-pat">--</div><div class="stat-lbl">Patents</div></div>
<div><div class="stat-val" id="s-mat">--</div><div class="stat-lbl">Materials</div></div>
<div><div class="stat-val" id="s-lnk">--</div><div class="stat-lbl">Links</div></div>
<div><div class="stat-val" id="s-sub">--</div><div class="stat-lbl">Substitutions</div></div>
</div></header>
<aside class="left">
<div class="section-title">Materials</div>
<div id="mat-list"></div>
<div class="section-title">Filters</div>
<label style="font-size:11px;color:var(--t2)">Usage Type</label>
<select id="f-usage"><option value="">All</option><option value="good">Part of Good</option><option value="manufacturing">Manufacturing</option></select>
<label style="font-size:11px;color:var(--t2)">Min Confidence: <span id="f-conf-val">0%</span></label>
<input type="range" id="f-conf" min="0" max="1" step="0.05" value="0">
<button class="btn btn-blue" onclick="applyFilters()">Apply</button>
</aside>
<main class="graph-area">
<div class="g-controls">
<button class="g-btn" onclick="zIn()">+ Zoom</button>
<button class="g-btn" onclick="zOut()">- Zoom</button>
<button class="g-btn" onclick="zReset()">Reset</button>
</div>
<svg id="graph-svg"></svg>
<div class="legend">
<div class="legend-title">Nodes</div>
<div class="legend-row"><div class="dot" style="background:var(--green)"></div>Good</div>
<div class="legend-row"><div class="dot" style="background:var(--amber)"></div>Manufacturing</div>
<div class="legend-row"><div class="dot" style="background:var(--t2)"></div>Unclassified</div>
<div class="legend-title" style="margin-top:8px">Edges</div>
<div class="legend-row"><div style="width:16px;height:2px;background:var(--blue)"></div>Material in Good</div>
<div class="legend-row"><div style="width:16px;height:2px;background:var(--purple)"></div>Good in Good</div>
</div>
<div class="tooltip" id="tip"></div>
</main>
<aside class="right">
<div class="tabs">
<div class="tab active" onclick="stab('det')">Details</div>
<div class="tab" onclick="stab('pat')">Patents</div>
<div class="tab" onclick="stab('sub')">Substitutions</div>
</div>
<div class="tab-content active" id="t-det">
<div class="empty" id="det-empty"><h3>Select a Node</h3><p>Click a patent in the graph to view details and source links.</p></div>
<div id="det-content" style="display:none"></div>
</div>
<div class="tab-content" id="t-pat"><div id="pat-list"></div></div>
<div class="tab-content" id="t-sub"><div id="sub-list"></div></div>
</aside></div>
<script>
let gData={nodes:[],edges:[]},sim,svg,g,link,node,zm,selMat='',selUse='',minConf=0;
const uCol={good:'#10b981',manufacturing:'#f59e0b',unknown:'#94a3b8'};
const lCol={material_in_good:'#3b82f6',good_in_good:'#10b981',process_in_process:'#f59e0b'};
const mCol=['#3b82f6','#10b981','#f59e0b','#f43f5e','#8b5cf6','#06b6d4','#ec4899','#14b8a6'];
let mColMap={};

document.addEventListener('DOMContentLoaded',()=>{loadStats();loadMats();loadGraph();loadPats();loadSubs();
document.getElementById('f-conf').addEventListener('input',e=>{document.getElementById('f-conf-val').textContent=Math.round(e.target.value*100)+'%'})});

async function loadStats(){try{const r=await(await fetch('/api/stats')).json();
document.getElementById('s-pat').textContent=r.total_patents;
document.getElementById('s-mat').textContent=r.total_materials;
document.getElementById('s-lnk').textContent=r.total_supply_chain_links;
document.getElementById('s-sub').textContent=r.total_substitutions}catch(e){}}

async function loadMats(){try{const ms=await(await fetch('/api/materials')).json();
let h='<div class="mat-item active" data-m="" onclick="pickMat(this)"><span>All Materials</span><span class="mat-count">'+ms.reduce((a,m)=>a+m.patent_count,0)+'</span></div>';
ms.forEach((m,i)=>{mColMap[m.name]=mCol[i%mCol.length];
h+=`<div class="mat-item" data-m="${m.name}" onclick="pickMat(this)"><span>${m.name}${m.symbol?' ('+m.symbol+')':''}</span><span class="mat-count">${m.patent_count}</span></div>`});
document.getElementById('mat-list').innerHTML=h}catch(e){}}

function pickMat(el){document.querySelectorAll('.mat-item').forEach(i=>i.classList.remove('active'));
el.classList.add('active');selMat=el.dataset.m;applyFilters()}

async function loadGraph(){try{let u='/api/graph?';if(selMat)u+=`material=${encodeURIComponent(selMat)}&`;
if(selUse)u+=`usage_type=${selUse}&`;if(minConf)u+=`min_confidence=${minConf}&`;
gData=await(await fetch(u)).json();renderGraph()}catch(e){renderEmpty()}}

function renderGraph(){const c=document.querySelector('.graph-area'),w=c.clientWidth,h=c.clientHeight;
d3.select('#graph-svg').selectAll('*').remove();
svg=d3.select('#graph-svg').attr('width',w).attr('height',h);
zm=d3.zoom().scaleExtent([.1,4]).on('zoom',e=>g.attr('transform',e.transform));svg.call(zm);
g=svg.append('g');
if(!gData.nodes.length){renderEmpty();return}
link=g.append('g').selectAll('line').data(gData.edges).join('line').attr('class','link')
.attr('stroke',d=>lCol[d.link_type]||'#3b82f6').attr('stroke-width',d=>Math.max(1,d.confidence*3))
.on('mouseover',(e,d)=>{const t=document.getElementById('tip');t.innerHTML=`<b>${d.description||d.link_type}</b><br>Conf: ${Math.round(d.confidence*100)}%`;t.style.display='block';t.style.left=(e.pageX+10)+'px';t.style.top=(e.pageY-10)+'px'})
.on('mouseout',()=>document.getElementById('tip').style.display='none');
node=g.append('g').selectAll('.node').data(gData.nodes).join('g').attr('class','node')
.call(d3.drag().on('start',(e)=>{if(!e.active)sim.alphaTarget(.3).restart();e.subject.fx=e.subject.x;e.subject.fy=e.subject.y})
.on('drag',(e)=>{e.subject.fx=e.x;e.subject.fy=e.y}).on('end',(e)=>{if(!e.active)sim.alphaTarget(0);e.subject.fx=null;e.subject.fy=null}));
node.append('circle').attr('r',d=>5+(d.confidence||0)*7).attr('fill',d=>uCol[d.usage_type]||'#94a3b8')
.attr('stroke',d=>mColMap[d.material]||'#3b82f6')
.on('mouseover',(e,d)=>{const t=document.getElementById('tip');t.innerHTML=`<b>${d.title}</b><br>${d.id}<br>Material: ${d.material}<br>Type: ${d.usage_type}`;t.style.display='block';t.style.left=(e.pageX+10)+'px';t.style.top=(e.pageY-10)+'px'})
.on('mouseout',()=>document.getElementById('tip').style.display='none')
.on('click',(e,d)=>showDet(d));
node.append('text').attr('dx',12).attr('dy',3).text(d=>d.title?.substring(0,25)+'...');
sim=d3.forceSimulation(gData.nodes).force('link',d3.forceLink(gData.edges).id(d=>d.id).distance(80))
.force('charge',d3.forceManyBody().strength(-150)).force('center',d3.forceCenter(w/2,h/2))
.on('tick',()=>{link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
node.attr('transform',d=>`translate(${d.x},${d.y})`)})}

function renderEmpty(){const c=document.querySelector('.graph-area'),w=c.clientWidth,h=c.clientHeight;
svg=d3.select('#graph-svg').attr('width',w).attr('height',h);svg.selectAll('*').remove();
svg.append('text').attr('x',w/2).attr('y',h/2-10).attr('text-anchor','middle').attr('fill','#94a3b8').attr('font-size','16px').text('No Supply Chain Data Yet');
svg.append('text').attr('x',w/2).attr('y',h/2+15).attr('text-anchor','middle').attr('fill','#64748b').attr('font-size','12px').text('Run the scanner first, then refresh this page')}

function showDet(d){document.getElementById('det-empty').style.display='none';
const c=document.getElementById('det-content');c.style.display='block';
const bc=d.usage_type==='good'?'b-good':d.usage_type==='manufacturing'?'b-mfg':'b-unk';
c.innerHTML=`<div class="card" style="border-color:var(--blue)"><div class="card-title"><a href="${d.url}" target="_blank">${d.title}</a></div>
<div class="card-meta">Patent: ${d.id}</div><div class="card-meta">Material: <b>${d.material}</b></div>
${d.assignee?'<div class="card-meta">'+d.assignee+'</div>':''}
<span class="badge ${bc}">${d.usage_type}</span>
${d.usage_description?'<p style="margin-top:8px;font-size:12px;color:var(--t2)">'+d.usage_description+'</p>':''}
<div class="conf-bar"><div class="conf-fill" style="width:${(d.confidence||0)*100}%"></div></div>
<div style="font-size:10px;color:var(--t2);margin-top:3px">Confidence: ${Math.round((d.confidence||0)*100)}%</div></div>
<div class="section-title">Source</div><a href="${d.url}" target="_blank" style="color:var(--blue);font-size:12px;word-break:break-all">${d.url}</a>`;
stab('det')}

async function loadPats(){try{let u='/api/patents?per_page=50';if(selMat)u+=`&material=${encodeURIComponent(selMat)}`;
const d=await(await fetch(u)).json();const c=document.getElementById('pat-list');
if(!d.patents.length){c.innerHTML='<div class="empty"><h3>No Patents</h3><p>Run the scanner to find patents.</p></div>';return}
c.innerHTML=d.patents.map(p=>{const bc=p.usage_type==='good'?'b-good':p.usage_type==='manufacturing'?'b-mfg':'b-unk';
return`<div class="card"><div class="card-title"><a href="${p.url}" target="_blank">${p.title}</a></div>
<div class="card-meta">${p.patent_id} | ${p.material_name}</div>
<span class="badge ${bc}">${p.usage_type}</span>
<div class="conf-bar"><div class="conf-fill" style="width:${(p.confidence||0)*100}%"></div></div></div>`}).join('')}catch(e){}}

async function loadSubs(){try{const d=await(await fetch('/api/substitutions')).json();const c=document.getElementById('sub-list');
const ks=Object.keys(d);if(!ks.length){c.innerHTML='<div class="empty"><h3>No Substitutions</h3><p>Run analyzer to detect substitution attempts.</p></div>';return}
let h='';for(const m of ks){h+=`<div class="section-title">${m}</div>`;
for(const s of d[m])h+=`<div class="sub-card"><div style="font-size:12px;font-weight:600">${m} <span class="arrow">&rarr;</span> ${s.substitute}</div>
<div class="card-title" style="font-size:11px"><a href="${s.patent_url}" target="_blank">${s.patent_title}</a></div>
<span class="badge ${s.success_indicated?'b-good':'b-sub'}">${s.success_indicated?'Successful':'Attempted'}</span></div>`}
c.innerHTML=h}catch(e){}}

function applyFilters(){selUse=document.getElementById('f-usage').value;minConf=parseFloat(document.getElementById('f-conf').value);loadGraph();loadPats()}
function stab(n){document.querySelectorAll('.tab').forEach((t,i)=>{const id=['det','pat','sub'][i];t.classList.toggle('active',id===n)});
document.querySelectorAll('.tab-content').forEach(t=>t.classList.toggle('active',t.id==='t-'+n))}
function zIn(){svg.transition().duration(300).call(zm.scaleBy,1.5)}
function zOut(){svg.transition().duration(300).call(zm.scaleBy,.67)}
function zReset(){svg.transition().duration(300).call(zm.transform,d3.zoomIdentity)}
</script></body></html>
"""

app = Flask(__name__)


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/graph")
def api_graph():
    material_filter = request.args.get("material")
    usage_filter = request.args.get("usage_type")
    min_conf = float(request.args.get("min_confidence", 0))

    with get_db() as conn:
        nodes_data = conn.execute("""
            SELECT DISTINCT p.patent_id, p.title, p.url, p.assignee,
                   p.publication_date, pm.material_name, pm.usage_type,
                   pm.usage_description, pm.confidence
            FROM patents p JOIN patent_materials pm ON p.patent_id = pm.patent_id
            WHERE p.patent_id IN (
                SELECT upstream_patent_id FROM supply_chain_links
                UNION SELECT downstream_patent_id FROM supply_chain_links)
        """).fetchall()
        edges_data = conn.execute("""
            SELECT upstream_patent_id, downstream_patent_id,
                   link_type, link_description, confidence
            FROM supply_chain_links ORDER BY confidence DESC
        """).fetchall()

    nodes = [{"id":r["patent_id"],"title":r["title"],"url":r["url"],
              "assignee":r["assignee"],"publication_date":r["publication_date"],
              "material":r["material_name"],"usage_type":r["usage_type"],
              "usage_description":r["usage_description"],"confidence":r["confidence"]} for r in nodes_data]
    edges = [{"source":r["upstream_patent_id"],"target":r["downstream_patent_id"],
              "link_type":r["link_type"],"description":r["link_description"],
              "confidence":r["confidence"]} for r in edges_data]

    if material_filter:
        nodes = [n for n in nodes if n["material"] == material_filter]
        nids = {n["id"] for n in nodes}
        edges = [e for e in edges if e["source"] in nids and e["target"] in nids]
    if usage_filter:
        nodes = [n for n in nodes if n["usage_type"] == usage_filter]
        nids = {n["id"] for n in nodes}
        edges = [e for e in edges if e["source"] in nids and e["target"] in nids]
    if min_conf > 0:
        edges = [e for e in edges if e["confidence"] >= min_conf]

    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/materials")
def api_materials():
    with get_db() as conn:
        result = []
        for mat in EU_CRITICAL_RAW_MATERIALS:
            cnt = conn.execute("SELECT COUNT(*) as c FROM patent_materials WHERE material_name=?",
                               (mat.name,)).fetchone()["c"]
            result.append({"name":mat.name,"symbol":mat.symbol,"category":mat.category,
                          "patent_count":cnt,"applications":mat.applications})
    return jsonify(result)


@app.route("/api/patents")
def api_patents():
    material = request.args.get("material")
    per_page = int(request.args.get("per_page", 50))

    with get_db() as conn:
        q = """SELECT p.patent_id,p.title,p.abstract,p.assignee,p.url,
               p.publication_date,pm.material_name,pm.usage_type,
               pm.usage_description,pm.confidence
               FROM patents p JOIN patent_materials pm ON p.patent_id=pm.patent_id WHERE 1=1"""
        params = []
        if material:
            q += " AND pm.material_name=?"
            params.append(material)
        q += " ORDER BY p.publication_date DESC LIMIT ?"
        params.append(per_page)
        rows = conn.execute(q, params).fetchall()

    return jsonify({"patents": [dict(r) for r in rows], "total": len(rows)})


@app.route("/api/substitutions")
def api_substitutions():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT sa.*, p.title, p.url FROM substitution_attempts sa
            JOIN patents p ON sa.patent_id = p.patent_id
            ORDER BY sa.original_material
        """).fetchall()
    summary = defaultdict(list)
    for r in rows:
        summary[r["original_material"]].append({
            "patent_id":r["patent_id"],"patent_title":r["title"],"patent_url":r["url"],
            "substitute":r["substitute_material"],"description":r["description"],
            "success_indicated":bool(r["success_indicated"])})
    return jsonify(dict(summary))


@app.route("/api/stats")
def api_stats():
    with get_db() as conn:
        return jsonify({
            "total_patents": conn.execute("SELECT COUNT(*) as c FROM patents").fetchone()["c"],
            "total_materials": conn.execute("SELECT COUNT(DISTINCT material_name) as c FROM patent_materials").fetchone()["c"],
            "total_supply_chain_links": conn.execute("SELECT COUNT(*) as c FROM supply_chain_links").fetchone()["c"],
            "total_substitutions": conn.execute("SELECT COUNT(*) as c FROM substitution_attempts").fetchone()["c"],
        })


# ===========================================================================
# SECTION 9: MAIN - Run this file!
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("CRM Patent Supply Chain Mapper")
    print("=" * 60)
    print()
    print("Choose an action:")
    print("  1. Run full scan + launch dashboard")
    print("  2. Launch dashboard only (if you already scanned)")
    print("  3. Run scan only (no dashboard)")
    print("  4. List all EU Critical Raw Materials")
    print()

    choice = input("Enter choice (1-4): ").strip()

    if choice == "1":
        run_full_pipeline(incremental=False)
        print(f"\nStarting dashboard at http://localhost:{WEB_PORT}")
        print("Open that URL in your browser. Press Ctrl+C to stop.\n")
        app.run(host="0.0.0.0", port=WEB_PORT)

    elif choice == "2":
        init_db()
        print(f"\nStarting dashboard at http://localhost:{WEB_PORT}")
        print("Open that URL in your browser. Press Ctrl+C to stop.\n")
        app.run(host="0.0.0.0", port=WEB_PORT)

    elif choice == "3":
        run_full_pipeline(incremental=False)
        print("\nScan complete! Run again and choose option 2 to view the dashboard.")

    elif choice == "4":
        print(f"\nEU Critical Raw Materials ({len(EU_CRITICAL_RAW_MATERIALS)} materials):")
        print("-" * 50)
        for m in EU_CRITICAL_RAW_MATERIALS:
            sym = f" ({m.symbol})" if m.symbol else ""
            print(f"  {m.name}{sym} [{m.category}]")
            print(f"    Uses: {', '.join(m.applications)}")

    else:
        print("Invalid choice. Running dashboard...")
        init_db()
        app.run(host="0.0.0.0", port=WEB_PORT)
