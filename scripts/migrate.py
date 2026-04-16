"""
migrate.py — Schema migration handler for memory.db and wiki.db.
"""
from pathlib import Path

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from db_memory import DBMemory
from db_wiki import DBWiki


def migrate_db_memory(db_path, target_version=1):
    db = DBMemory(db_path)
    current = db.get_schema_version()
    if current != target_version:
        db.set_schema_version(target_version)
    db.close()

def migrate_db_wiki(db_path):
    db = DBWiki(db_path)
    # For now, just ensure schema exists
    db.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: migrate.py <db_memory_path> <db_wiki_path>')
        exit(1)
    migrate_db_memory(sys.argv[1])
    migrate_db_wiki(sys.argv[2])
    print('Migration complete.')
