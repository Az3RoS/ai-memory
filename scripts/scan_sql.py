"""
scan_sql.py — SQL and migration file scanner using regex.
"""
import re
from pathlib import Path
from db_wiki import DBWiki

def scan_sql_files(project: str, repo_dir: Path, db_path: Path):
    db = DBWiki(db_path)
    # TODO: Walk repo_dir, parse .sql files, extract tables, columns, constraints, etc.
    pass
