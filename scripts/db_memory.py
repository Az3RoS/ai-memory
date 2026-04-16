# db_memory.py
# New schema: memories, file_pairs, knowledge_graph, patterns, stacks, developers, sprints, schema_version + 11 functions
import sqlite3
from pathlib import Path
import json

class DBMemory:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY,
            project TEXT,
            entry_type TEXT,
            summary TEXT,
            detail TEXT,
            tags TEXT,
            files TEXT,
            date TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS file_pairs (
            id INTEGER PRIMARY KEY,
            file_a TEXT,
            file_b TEXT,
            count INTEGER
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS knowledge_graph (
            id INTEGER PRIMARY KEY,
            entity_a TEXT,
            relation TEXT,
            entity_b TEXT,
            project TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            project TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS stacks (
            id INTEGER PRIMARY KEY,
            stack_name TEXT,
            details TEXT,
            project TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS developers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            project TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sprints (
            id INTEGER PRIMARY KEY,
            name TEXT,
            start_date TEXT,
            end_date TEXT,
            project TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER
        )''')
        self.conn.commit()

    def add_memory(self, project, entry_type, summary, detail, tags, files, date):
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO memories (project, entry_type, summary, detail, tags, files, date)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (project, entry_type, summary, detail, tags, files, date))
        self.conn.commit()
        return cur.lastrowid

    def get_memories(self, project, limit=20):
        cur = self.conn.cursor()
        cur.execute('''SELECT * FROM memories WHERE project=? ORDER BY date DESC LIMIT ?''', (project, limit))
        return cur.fetchall()

    def add_file_pair(self, file_a, file_b, count):
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO file_pairs (file_a, file_b, count) VALUES (?, ?, ?)''', (file_a, file_b, count))
        self.conn.commit()

    def add_knowledge_edge(self, entity_a, relation, entity_b, project):
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO knowledge_graph (entity_a, relation, entity_b, project)
                       VALUES (?, ?, ?, ?)''', (entity_a, relation, entity_b, project))
        self.conn.commit()

    def add_pattern(self, name, description, project):
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO patterns (name, description, project) VALUES (?, ?, ?)''', (name, description, project))
        self.conn.commit()

    def add_stack(self, stack_name, details, project):
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO stacks (stack_name, details, project) VALUES (?, ?, ?)''', (stack_name, details, project))
        self.conn.commit()

    def add_developer(self, name, email, project):
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO developers (name, email, project) VALUES (?, ?, ?)''', (name, email, project))
        self.conn.commit()

    def add_sprint(self, name, start_date, end_date, project):
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO sprints (name, start_date, end_date, project) VALUES (?, ?, ?, ?)''', (name, start_date, end_date, project))
        self.conn.commit()

    def set_schema_version(self, version):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM schema_version')
        cur.execute('INSERT INTO schema_version (version) VALUES (?)', (version,))
        self.conn.commit()

    def get_schema_version(self):
        cur = self.conn.cursor()
        cur.execute('SELECT version FROM schema_version')
        row = cur.fetchone()
        return row[0] if row else None

    def close(self):
        self.conn.close()
"""
db_memory.py — Temporal memory database (memory.db)

Schema: memories, file_pairs, knowledge_graph, patterns, stacks, developers, sprints, schema_version
"""

import sqlite3
from pathlib import Path
from typing import Optional

DB_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    detail TEXT,
    tags TEXT,
    files TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    date TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS file_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    file_a TEXT NOT NULL,
    file_b TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    last_seen TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS knowledge_graph (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    from_entity TEXT NOT NULL,
    relation TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    pattern TEXT NOT NULL,
    confidence REAL NOT NULL,
    files TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    stack TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS developers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    joined_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""

class DBMemory:
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
