"""
db_wiki.py — Structural wiki database (wiki.db)

Schema: entities, relationships, entities_fts, scan_state
"""

import sqlite3
from pathlib import Path
from typing import Optional

DB_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    name TEXT NOT NULL,
    file TEXT,
    line INTEGER,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    from_entity TEXT NOT NULL,
    relation TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
    project,
    entity_type,
    name,
    file,
    metadata,
    content=entities,
    content_rowid=id,
    tokenize='porter ascii'
);

CREATE TABLE IF NOT EXISTS scan_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    file TEXT NOT NULL,
    hash TEXT NOT NULL,
    last_scanned TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

class DBWiki:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_schema(self):
        self.conn.executescript(DB_SCHEMA)
        self.conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # Add CRUD and query methods as needed for each table
