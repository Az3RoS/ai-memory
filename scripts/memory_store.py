"""
memory_store.py — SQLite + FTS5 persistence layer.

Schema:
  entries        — every memory event (commit, decision, blocker, note)
  entries_fts    — FTS5 virtual table over entries (full-text search)
  relations      — entity-to-entity edges (knowledge graph)

Design principles:
  - Append-only: entries are never deleted, only superseded.
  - FTS5 with porter tokeniser for broad matching.
  - Lean schema — only what's needed to support context assembly.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional


DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT    NOT NULL,
    entry_type  TEXT    NOT NULL,   -- commit|decision|blocker|note|file_change|test
    summary     TEXT    NOT NULL,
    detail      TEXT,
    tags        TEXT,               -- comma-separated
    files       TEXT,               -- comma-separated paths
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    date        TEXT    NOT NULL DEFAULT (date('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    project,
    entry_type,
    summary,
    detail,
    tags,
    files,
    content=entries,
    content_rowid=id,
    tokenize='porter ascii'
);

CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, project, entry_type, summary, detail, tags, files)
    VALUES (new.id, new.project, new.entry_type, new.summary, new.detail, new.tags, new.files);
END;

CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, project, entry_type, summary, detail, tags, files)
    VALUES ('delete', old.id, old.project, old.entry_type, old.summary, old.detail, old.tags, old.files);
END;

CREATE TABLE IF NOT EXISTS relations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT    NOT NULL,
    from_entity TEXT    NOT NULL,
    relation    TEXT    NOT NULL,   -- e.g. 'depends_on', 'implements', 'blocks'
    to_entity   TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_entries_project_date ON entries(project, date DESC);
CREATE INDEX IF NOT EXISTS idx_relations_project     ON relations(project);
"""


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_schema()

    # ── Connection ────────────────────────────────────────────────────────────

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_schema(self):
        self.conn.executescript(DDL)
        self.conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Write ─────────────────────────────────────────────────────────────────

    def add_entry(
        self,
        project: str,
        entry_type: str,
        summary: str,
        detail: str = "",
        tags: list[str] | None = None,
        files: list[str] | None = None,
        created_at: str | None = None,
    ) -> int:
        tag_str  = ",".join(tags or [])
        file_str = ",".join(files or [])
        ts = created_at or datetime.utcnow().isoformat(sep=" ", timespec="seconds")
        dt = ts[:10]
        cur = self.conn.execute(
            """INSERT INTO entries (project, entry_type, summary, detail, tags, files, created_at, date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (project, entry_type, summary, detail, tag_str, file_str, ts, dt),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_relation(self, project: str, from_entity: str, relation: str, to_entity: str):
        self.conn.execute(
            """INSERT OR IGNORE INTO relations (project, from_entity, relation, to_entity)
               VALUES (?, ?, ?, ?)""",
            (project, from_entity, relation, to_entity),
        )
        self.conn.commit()

    # ── Read — FTS ────────────────────────────────────────────────────────────

    def search(self, terms: str, project: str | None = None, limit: int = 10) -> list[dict]:
        """Full-text search via FTS5. Empty terms → recent entries."""
        if terms.strip():
            sql = """
                SELECT e.*, bm25(entries_fts) AS score
                FROM entries_fts f
                JOIN entries e ON e.id = f.rowid
                WHERE entries_fts MATCH ?
                  {project_filter}
                ORDER BY score
                LIMIT ?
            """
            proj_filter = "AND e.project = ?" if project else ""
            sql = sql.format(project_filter=proj_filter)
            params = [terms, project, limit] if project else [terms, limit]
        else:
            sql = """
                SELECT *, NULL AS score FROM entries
                WHERE 1=1 {project_filter}
                ORDER BY date DESC, id DESC
                LIMIT ?
            """
            proj_filter = "AND project = ?" if project else ""
            sql = sql.format(project_filter=proj_filter)
            params = [project, limit] if project else [limit]

        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def recent_by_date(self, project: str, target_date: str | None = None) -> list[dict]:
        """All entries for a given date (default: today)."""
        dt = target_date or date.today().isoformat()
        rows = self.conn.execute(
            "SELECT * FROM entries WHERE project=? AND date=? ORDER BY id",
            (project, dt),
        ).fetchall()
        return [dict(r) for r in rows]

    def all_for_project(self, project: str, limit: int = 200) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM entries WHERE project=? ORDER BY date DESC, id DESC LIMIT ?",
            (project, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def entry_count(self, project: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM entries WHERE project=?", (project,)
        ).fetchone()[0]

    def relations_for(self, project: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM relations WHERE project=? ORDER BY from_entity, relation",
            (project,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def tag_summary(self, project: str) -> dict[str, int]:
        """Return {tag: count} for a project."""
        rows = self.conn.execute(
            "SELECT tags FROM entries WHERE project=? AND tags != ''", (project,)
        ).fetchall()
        counts: dict[str, int] = {}
        for row in rows:
            for tag in row["tags"].split(","):
                tag = tag.strip()
                if tag:
                    counts[tag] = counts.get(tag, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

