"""
Recurring patent scan scheduler.

Provides multiple scheduling options:
1. APScheduler-based in-process scheduling (for standalone deployment)
2. Cron-compatible CLI entry point (for system cron integration)
3. Manual trigger via CLI

The scheduler runs the full pipeline:
  Search -> Classify -> Map Supply Chains -> Detect Substitutions
"""

import logging
import signal
import sys
from datetime import datetime

logger = logging.getLogger(__name__)


def run_full_pipeline(
    incremental: bool = True,
    lookback_days: int | None = None,
    material_name: str | None = None,
):
    """
    Run the complete analysis pipeline.

    Args:
        incremental: If True, only scan for new patents since last scan
        lookback_days: Number of days to look back (for incremental scans)
        material_name: If provided, only process this material
    """
    from crm_patent_analyzer.analysis.classifier import classify_all_patents
    from crm_patent_analyzer.analysis.substitution import detect_substitutions
    from crm_patent_analyzer.analysis.supply_chain import build_supply_chain_map
    from crm_patent_analyzer.data.critical_raw_materials import CRM_BY_NAME
    from crm_patent_analyzer.data.database import init_db
    from crm_patent_analyzer.search.patent_search import (
        incremental_scan,
        search_all_materials,
        search_single_material,
    )

    logger.info("=" * 60)
    logger.info("Starting CRM Patent Analysis Pipeline")
    logger.info("Time: %s", datetime.now().isoformat())
    logger.info("Mode: %s", "incremental" if incremental else "full")
    logger.info("=" * 60)

    # Step 0: Initialize database
    init_db()
    logger.info("[1/4] Database initialized")

    # Step 1: Search for patents
    if material_name:
        material = CRM_BY_NAME.get(material_name)
        if not material:
            logger.error("Unknown material: %s", material_name)
            return
        logger.info("[2/4] Searching patents for: %s", material_name)
        search_single_material(material)
    elif incremental:
        logger.info("[2/4] Running incremental patent scan...")
        incremental_scan(lookback_days)
    else:
        logger.info("[2/4] Running full patent scan...")
        search_all_materials()

    # Step 2: Classify patents
    logger.info("[3/4] Classifying patent usage types...")
    classify_all_patents(material_name)

    # Step 3: Build supply chain map
    logger.info("[3/4] Building supply chain map...")
    build_supply_chain_map()

    # Step 4: Detect substitutions
    logger.info("[4/4] Detecting material substitutions...")
    detect_substitutions()

    logger.info("=" * 60)
    logger.info("Pipeline complete at %s", datetime.now().isoformat())
    logger.info("=" * 60)


def start_scheduler(interval_days: int = 30, run_now: bool = False):
    """
    Start the APScheduler-based recurring scan.

    Args:
        interval_days: Days between scans
        run_now: If True, run the pipeline immediately before starting scheduler
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.error(
            "APScheduler not installed. Install with: pip install apscheduler\n"
            "Alternatively, use system cron with: python -m crm_patent_analyzer scan"
        )
        return

    if run_now:
        logger.info("Running initial pipeline scan...")
        run_full_pipeline(incremental=True)

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_full_pipeline,
        trigger=IntervalTrigger(days=interval_days),
        kwargs={"incremental": True},
        id="crm_patent_scan",
        name=f"CRM Patent Scan (every {interval_days} days)",
        replace_existing=True,
    )

    # Graceful shutdown
    def shutdown(signum, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info(
        "Scheduler started. Scanning every %d days. Press Ctrl+C to stop.",
        interval_days,
    )
    scheduler.start()


def generate_cron_entry(interval_days: int = 30, hour: int = 2) -> str:
    """
    Generate a crontab entry for system-level scheduling.

    Args:
        interval_days: Days between scans (approximate via cron)
        hour: Hour of day to run (0-23)

    Returns:
        Crontab line string
    """
    python_path = sys.executable
    # Monthly scan (closest cron approximation to 30 days)
    if interval_days >= 28:
        schedule = f"0 {hour} 1 * *"  # 1st of every month
        description = "monthly"
    elif interval_days >= 7:
        schedule = f"0 {hour} * * 0"  # Every Sunday
        description = "weekly"
    else:
        schedule = f"0 {hour} */{interval_days} * *"
        description = f"every {interval_days} days"

    cmd = f"{python_path} -m crm_patent_analyzer scan --incremental"
    entry = f"{schedule} {cmd}"

    print(f"Add this line to your crontab (crontab -e) for {description} scans:")
    print(f"  {entry}")
    return entry
