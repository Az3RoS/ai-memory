"""
lint.py — Knowledge base health checker for memory.db and wiki.db.
"""
from pathlib import Path
from db_memory import DBMemory
from db_wiki import DBWiki

def run_lint(project: str, db_memory_path: Path, db_wiki_path: Path):
    db_mem = DBMemory(db_memory_path)
    db_wiki = DBWiki(db_wiki_path)
    # TODO: Scan for contradicting decisions, stale entries, broken patterns, etc.
    pass
