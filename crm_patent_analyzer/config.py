"""Configuration for the CRM Patent Analyzer."""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data storage
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "patents.db"

# Google Patents search via SerpApi
# Get a free API key at https://serpapi.com/
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")

# Lens.org API (alternative patent source)
# Register at https://www.lens.org/lens/user/subscriptions
LENS_API_KEY = os.environ.get("LENS_API_KEY", "")

# Search settings
MAX_RESULTS_PER_MATERIAL = 100
SEARCH_LOOKBACK_DAYS = 30  # For recurring scans

# Google Patents base URL for direct linking
GOOGLE_PATENTS_BASE_URL = "https://patents.google.com/patent/"
GOOGLE_PATENTS_SEARCH_URL = "https://patents.google.com/"

# Web server
WEB_HOST = os.environ.get("CRM_WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.environ.get("CRM_WEB_PORT", "8050"))
WEB_DEBUG = os.environ.get("CRM_WEB_DEBUG", "false").lower() == "true"

# Scheduler
SCAN_INTERVAL_DAYS = int(os.environ.get("CRM_SCAN_INTERVAL_DAYS", "30"))
SCAN_CRON_HOUR = int(os.environ.get("CRM_SCAN_CRON_HOUR", "2"))  # 2 AM
