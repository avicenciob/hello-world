"""
Flask web application for the interactive CRM Patent Supply Chain Mapper.

Serves the interactive visualization dashboard with:
- Force-directed supply chain graph (D3.js)
- Material filter panel
- Patent detail sidebar
- Substitution analysis view
- Statistics dashboard
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from crm_patent_analyzer.analysis.supply_chain import get_supply_chain_graph
from crm_patent_analyzer.analysis.substitution import get_substitution_summary
from crm_patent_analyzer.config import WEB_DEBUG, WEB_HOST, WEB_PORT
from crm_patent_analyzer.data.critical_raw_materials import get_all_materials
from crm_patent_analyzer.data.database import get_db, init_db

logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


@app.route("/")
def index():
    """Serve the main interactive dashboard."""
    materials = get_all_materials()
    return render_template("index.html", materials=materials)


@app.route("/api/graph")
def api_graph():
    """Return the supply chain graph data for D3.js visualization."""
    material_filter = request.args.get("material")
    usage_filter = request.args.get("usage_type")
    min_confidence = float(request.args.get("min_confidence", 0))

    graph = get_supply_chain_graph()

    # Apply filters
    if material_filter:
        graph["nodes"] = [n for n in graph["nodes"] if n["material"] == material_filter]
        node_ids = {n["id"] for n in graph["nodes"]}
        graph["edges"] = [
            e for e in graph["edges"]
            if e["source"] in node_ids and e["target"] in node_ids
        ]

    if usage_filter:
        graph["nodes"] = [n for n in graph["nodes"] if n["usage_type"] == usage_filter]
        node_ids = {n["id"] for n in graph["nodes"]}
        graph["edges"] = [
            e for e in graph["edges"]
            if e["source"] in node_ids and e["target"] in node_ids
        ]

    if min_confidence > 0:
        graph["edges"] = [e for e in graph["edges"] if e["confidence"] >= min_confidence]

    return jsonify(graph)


@app.route("/api/materials")
def api_materials():
    """Return the list of critical raw materials with patent counts."""
    materials = get_all_materials()
    result = []

    with get_db() as conn:
        for mat in materials:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM patent_materials WHERE material_name = ?",
                (mat.name,),
            ).fetchone()["cnt"]

            result.append({
                "name": mat.name,
                "symbol": mat.symbol,
                "category": mat.category,
                "patent_count": count,
                "applications": mat.applications,
            })

    return jsonify(result)


@app.route("/api/patents")
def api_patents():
    """Return patents with optional filtering."""
    material = request.args.get("material")
    usage_type = request.args.get("usage_type")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    offset = (page - 1) * per_page

    with get_db() as conn:
        query = """
            SELECT p.patent_id, p.title, p.abstract, p.assignee, p.url,
                   p.publication_date, pm.material_name, pm.usage_type,
                   pm.usage_description, pm.confidence
            FROM patents p
            JOIN patent_materials pm ON p.patent_id = pm.patent_id
            WHERE 1=1
        """
        params = []

        if material:
            query += " AND pm.material_name = ?"
            params.append(material)
        if usage_type:
            query += " AND pm.usage_type = ?"
            params.append(usage_type)

        query += " ORDER BY p.publication_date DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        rows = conn.execute(query, params).fetchall()

        # Get total count
        count_query = """
            SELECT COUNT(*) as cnt
            FROM patents p
            JOIN patent_materials pm ON p.patent_id = pm.patent_id
            WHERE 1=1
        """
        count_params = []
        if material:
            count_query += " AND pm.material_name = ?"
            count_params.append(material)
        if usage_type:
            count_query += " AND pm.usage_type = ?"
            count_params.append(usage_type)

        total = conn.execute(count_query, count_params).fetchone()["cnt"]

    patents = [dict(row) for row in rows]
    return jsonify({"patents": patents, "total": total, "page": page, "per_page": per_page})


@app.route("/api/substitutions")
def api_substitutions():
    """Return substitution analysis data."""
    summary = get_substitution_summary()
    return jsonify(summary)


@app.route("/api/stats")
def api_stats():
    """Return dashboard statistics."""
    with get_db() as conn:
        total_patents = conn.execute("SELECT COUNT(*) as cnt FROM patents").fetchone()["cnt"]
        total_materials = conn.execute(
            "SELECT COUNT(DISTINCT material_name) as cnt FROM patent_materials"
        ).fetchone()["cnt"]
        total_links = conn.execute(
            "SELECT COUNT(*) as cnt FROM supply_chain_links"
        ).fetchone()["cnt"]
        total_substitutions = conn.execute(
            "SELECT COUNT(*) as cnt FROM substitution_attempts"
        ).fetchone()["cnt"]

        # Usage type breakdown
        usage_breakdown = conn.execute("""
            SELECT usage_type, COUNT(*) as cnt
            FROM patent_materials
            GROUP BY usage_type
        """).fetchall()

        # Material breakdown (top 10)
        material_breakdown = conn.execute("""
            SELECT material_name, COUNT(*) as cnt
            FROM patent_materials
            GROUP BY material_name
            ORDER BY cnt DESC
            LIMIT 10
        """).fetchall()

        # Recent scans
        recent_scans = conn.execute("""
            SELECT * FROM scan_history ORDER BY started_at DESC LIMIT 5
        """).fetchall()

    return jsonify({
        "total_patents": total_patents,
        "total_materials": total_materials,
        "total_supply_chain_links": total_links,
        "total_substitutions": total_substitutions,
        "usage_breakdown": {row["usage_type"]: row["cnt"] for row in usage_breakdown},
        "top_materials": [
            {"name": row["material_name"], "count": row["cnt"]}
            for row in material_breakdown
        ],
        "recent_scans": [dict(row) for row in recent_scans],
    })


def start_web_server():
    """Start the Flask development server."""
    init_db()
    logger.info("Starting web server on %s:%d", WEB_HOST, WEB_PORT)
    app.run(host=WEB_HOST, port=WEB_PORT, debug=WEB_DEBUG)
