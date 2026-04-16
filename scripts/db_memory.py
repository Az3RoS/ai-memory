"""
db_memory.py — Temporal memory database (memory.db)

Schema: memories, file_pairs, knowledge_graph, patterns, stacks, developers, sprints, schema_version
"""

import sqlite3
from pathlib import Path
from typing import Optional

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    entry_type  TEXT NOT NULL,
    summary     TEXT NOT NULL,
    detail      TEXT,
    tags        TEXT,
    files       TEXT,
    date        TEXT NOT NULL DEFAULT (date('now')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS file_pairs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL DEFAULT '',
    file_a      TEXT NOT NULL,
    file_b      TEXT NOT NULL,
    count       INTEGER NOT NULL DEFAULT 1,
    last_seen   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS knowledge_graph (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    entity_a    TEXT NOT NULL,
    relation    TEXT NOT NULL,
    entity_b    TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS patterns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    name        TEXT NOT NULL,
    description TEXT,
    confidence  REAL NOT NULL DEFAULT 1.0,
    files       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stacks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    stack_name  TEXT NOT NULL,
    details     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS developers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    name        TEXT NOT NULL,
    email       TEXT,
    joined_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sprints (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    name        TEXT NOT NULL,
    start_date  TEXT,
    end_date    TEXT,
    summary     TEXT,
    started_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""


class DBMemory:
    def __init__(self, db_path):
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
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # ── memories ───────────────────────────────────────────────────────────────

    def add_memory(self, project: str, entry_type: str, summary: str,
                   detail: str = "", tags: str = "", files: str = "",
                   date: str = "") -> int:
        cur = self.conn.cursor()
        if date:
            cur.execute(
                "INSERT INTO memories (project, entry_type, summary, detail, tags, files, date)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project, entry_type, summary, detail, tags, files, date),
            )
        else:
            cur.execute(
                "INSERT INTO memories (project, entry_type, summary, detail, tags, files)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (project, entry_type, summary, detail, tags, files),
            )
        self.conn.commit()
        return cur.lastrowid

    def get_memories(self, project: str, limit: int = 20) -> list:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM memories WHERE project=? ORDER BY date DESC, id DESC LIMIT ?",
            (project, limit),
        )
        return cur.fetchall()

    def all_for_project(self, project: str, limit: int = 100) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM memories WHERE project=? ORDER BY date DESC, id DESC LIMIT ?",
            (project, limit),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    # ── file_pairs ─────────────────────────────────────────────────────────────

    def add_file_pair(self, file_a: str, file_b: str, count: int = 1,
                      project: str = "") -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO file_pairs (project, file_a, file_b, count) VALUES (?, ?, ?, ?)",
            (project, file_a, file_b, count),
        )
        self.conn.commit()

    # ── knowledge_graph ────────────────────────────────────────────────────────

    def add_knowledge_edge(self, entity_a: str, relation: str, entity_b: str,
                           project: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO knowledge_graph (project, entity_a, relation, entity_b)"
            " VALUES (?, ?, ?, ?)",
            (project, entity_a, relation, entity_b),
        )
        self.conn.commit()

    # ── patterns ───────────────────────────────────────────────────────────────

    def add_pattern(self, name: str, description: str = "", project: str = "",
                    confidence: float = 1.0, files: str = "") -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO patterns (project, name, description, confidence, files)"
            " VALUES (?, ?, ?, ?, ?)",
            (project, name, description, confidence, files),
        )
        self.conn.commit()

    # ── stacks ─────────────────────────────────────────────────────────────────

    def add_stack(self, stack_name: str, details: str = "", project: str = "") -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO stacks (project, stack_name, details) VALUES (?, ?, ?)",
            (project, stack_name, details),
        )
        self.conn.commit()

    # ── developers ─────────────────────────────────────────────────────────────

    def add_developer(self, name: str, email: str = "", project: str = "") -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO developers (project, name, email) VALUES (?, ?, ?)",
            (project, name, email),
        )
        self.conn.commit()

    # ── sprints ────────────────────────────────────────────────────────────────

    def add_sprint(self, name: str, start_date: str = "", end_date: str = "",
                   project: str = "", summary: str = "") -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO sprints (project, name, start_date, end_date, summary)"
            " VALUES (?, ?, ?, ?, ?)",
            (project, name, start_date, end_date, summary),
        )
        self.conn.commit()

    # ── schema_version ─────────────────────────────────────────────────────────

    def set_schema_version(self, version: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM schema_version")
        cur.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        self.conn.commit()

    def get_schema_version(self) -> Optional[int]:
        cur = self.conn.cursor()
        cur.execute("SELECT version FROM schema_version")
        row = cur.fetchone()
        return row[0] if row else None

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
