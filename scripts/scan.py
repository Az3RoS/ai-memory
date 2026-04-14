"""
scan.py — Orchestrates codebase scanning and coordinates language-specific scanners.
"""
from pathlib import Path
from db_wiki import DBWiki

def scan_codebase(project: str, repo_dir: Path, db_path: Path, incremental: bool = False):
    db = DBWiki(db_path)
    # TODO: Call language-specific scanners and update wiki.db
    # Example: scan_python, scan_javascript, scan_sql, scan_generic
    pass
