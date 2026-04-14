"""
scan_python.py — Python-specific scanner using stdlib ast module.
"""
import ast
from pathlib import Path
from db_wiki import DBWiki

def scan_python_files(project: str, repo_dir: Path, db_path: Path):
    db = DBWiki(db_path)
    # TODO: Walk repo_dir, parse .py files, extract classes, functions, endpoints, models, etc.
    pass
