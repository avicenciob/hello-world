"""
Run this script in Spyder to operate the CRM Patent Analyzer.

Instructions:
    1. Set your API key below
    2. Choose which action to run (uncomment the one you want)
    3. Run the script (F5 in Spyder)
"""

import os
import sys

# ============================================================
# STEP 1: Set your API key here
# ============================================================
os.environ["SERPAPI_KEY"] = "1accd4c96bf783ae8b0bfd3adba7a698e1e1d1dddca917f15922c7d980c01838"

# Make sure the project root is on the Python path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


# ============================================================
# STEP 2: Initialize the database (run this once)
# ============================================================
from crm_patent_analyzer.data.database import init_db

init_db()
print("Database initialized.")


# ============================================================
# STEP 3: Choose an action below (uncomment what you need)
# ============================================================

# --- Option A: List all EU Critical Raw Materials ---
# from crm_patent_analyzer.data.critical_raw_materials import get_all_materials
# for mat in get_all_materials():
#     print(f"{mat.name} ({mat.symbol}) [{mat.category}] - {', '.join(mat.applications)}")


# --- Option B: Run a FULL scan (search + classify + map + substitutions) ---
# from crm_patent_analyzer.scheduler.scan_scheduler import run_full_pipeline
# run_full_pipeline(incremental=False)


# --- Option C: Run an INCREMENTAL scan (last 30 days only) ---
# from crm_patent_analyzer.scheduler.scan_scheduler import run_full_pipeline
# run_full_pipeline(incremental=True, lookback_days=30)


# --- Option D: Scan for a SINGLE material ---
# from crm_patent_analyzer.scheduler.scan_scheduler import run_full_pipeline
# run_full_pipeline(material_name="Cobalt")


# --- Option E: Launch the interactive web dashboard ---
# Opens at http://localhost:8050 - click the link in Spyder's console
# from crm_patent_analyzer.web.app import start_web_server
# start_web_server()
