"""
CLI entry point for the CRM Patent Analyzer.

Usage:
    python -m crm_patent_analyzer scan [--full] [--material NAME] [--lookback DAYS]
    python -m crm_patent_analyzer serve [--port PORT]
    python -m crm_patent_analyzer schedule [--interval DAYS] [--run-now]
    python -m crm_patent_analyzer cron [--interval DAYS]
    python -m crm_patent_analyzer init
    python -m crm_patent_analyzer materials
"""

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crm_patent_analyzer")


def main():
    parser = argparse.ArgumentParser(
        prog="crm_patent_analyzer",
        description="CRM Patent Supply Chain Mapper - Analyze patents using EU Critical Raw Materials",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Run patent search and analysis pipeline")
    scan_parser.add_argument("--full", action="store_true", help="Full scan (not incremental)")
    scan_parser.add_argument("--material", type=str, help="Only scan for a specific material")
    scan_parser.add_argument("--lookback", type=int, default=30, help="Days to look back (default: 30)")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start the interactive web dashboard")
    serve_parser.add_argument("--host", type=str, default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8050)
    serve_parser.add_argument("--debug", action="store_true")

    # schedule command
    sched_parser = subparsers.add_parser("schedule", help="Start recurring scan scheduler")
    sched_parser.add_argument("--interval", type=int, default=30, help="Days between scans")
    sched_parser.add_argument("--run-now", action="store_true", help="Run scan immediately")

    # cron command
    cron_parser = subparsers.add_parser("cron", help="Generate crontab entry")
    cron_parser.add_argument("--interval", type=int, default=30, help="Days between scans")
    cron_parser.add_argument("--hour", type=int, default=2, help="Hour to run (0-23)")

    # init command
    subparsers.add_parser("init", help="Initialize the database")

    # materials command
    subparsers.add_parser("materials", help="List all EU Critical Raw Materials")

    args = parser.parse_args()

    if args.command == "scan":
        from crm_patent_analyzer.scheduler.scan_scheduler import run_full_pipeline
        run_full_pipeline(
            incremental=not args.full,
            lookback_days=args.lookback,
            material_name=args.material,
        )

    elif args.command == "serve":
        from crm_patent_analyzer.config import WEB_DEBUG, WEB_HOST, WEB_PORT
        from crm_patent_analyzer.web.app import app, start_web_server
        import crm_patent_analyzer.config as config
        if args.host:
            config.WEB_HOST = args.host
        if args.port:
            config.WEB_PORT = args.port
        if args.debug:
            config.WEB_DEBUG = True
        start_web_server()

    elif args.command == "schedule":
        from crm_patent_analyzer.scheduler.scan_scheduler import start_scheduler
        start_scheduler(interval_days=args.interval, run_now=args.run_now)

    elif args.command == "cron":
        from crm_patent_analyzer.scheduler.scan_scheduler import generate_cron_entry
        generate_cron_entry(interval_days=args.interval, hour=args.hour)

    elif args.command == "init":
        from crm_patent_analyzer.data.database import init_db
        init_db()
        print("Database initialized successfully.")

    elif args.command == "materials":
        from crm_patent_analyzer.data.critical_raw_materials import get_all_materials
        materials = get_all_materials()
        print(f"\nEU Critical Raw Materials ({len(materials)} materials):")
        print("-" * 60)
        for mat in materials:
            symbol_str = f" ({mat.symbol})" if mat.symbol else ""
            print(f"  {mat.name}{symbol_str} [{mat.category}]")
            if mat.applications:
                print(f"    Applications: {', '.join(mat.applications)}")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
