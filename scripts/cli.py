"""
cli.py — Unified CLI entrypoint for ai-memory

Commands: init, scan, ingest, sync, query, status, feature, fix, lint, review, sprint, onboard, rebuild
"""

import argparse
import sys
from pathlib import Path

# Import new modules (to be implemented)
from db_memory import DBMemory
from db_wiki import DBWiki
import utils


def main():
    parser = argparse.ArgumentParser(description="ai-memory CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Example: init command
    subparsers.add_parser("init", help="Initialize ai-memory for this repo")
    subparsers.add_parser("scan", help="Scan the codebase and update wiki")
    subparsers.add_parser("ingest", help="Ingest the latest commit into memory")
    subparsers.add_parser("sync", help="Regenerate CONTEXT.md and related files")
    subparsers.add_parser("query", help="Query memory entries")
    subparsers.add_parser("status", help="Show project and memory status")
    # ...add other commands as needed

    args = parser.parse_args()
    db_path = Path.home() / ".ai-memory" / "memory.db"
    db = DBMemory(db_path)

    if args.command == "init":
        print("[init] Initializing ai-memory...")
        # ...call init logic
    elif args.command == "scan":
        print("[scan] Scanning codebase...")
        # ...call scan logic
    elif args.command == "ingest":
        print("[ingest] Ingesting latest commit...")
        # ...call ingest logic
    elif args.command == "sync":
        print("[sync] Regenerating CONTEXT.md...")
        # ...call sync logic
    elif args.command == "query":
        print("[query] Querying memory...")
        # ...call query logic
    elif args.command == "status":
        print("[status] Showing status...")
        # ...call status logic
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
