"""
scan_javascript.py — JavaScript/TypeScript scanner using regex patterns.
"""
import re
from pathlib import Path
from db_wiki import DBWiki

def scan_javascript_files(project: str, repo_dir: Path, db_path: Path):
    db = DBWiki(db_path)
    # TODO: Walk repo_dir, parse .js/.ts files, extract components, hooks, imports, etc.
    pass
