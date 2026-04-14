"""
wiki_gen.py — Generates markdown wiki pages from wiki.db data.
"""
from pathlib import Path
from db_wiki import DBWiki

def generate_wiki(project: str, repo_dir: Path, db_path: Path):
    db = DBWiki(db_path)
    # TODO: Query wiki.db and render markdown pages in .ai-wiki/wiki/
    pass
