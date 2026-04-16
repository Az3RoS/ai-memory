# db_wiki.py
# Structural database for wiki entities, relations, and documentation.
import sqlite3
from pathlib import Path

class DBWiki:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY,
            entity TEXT,
            entity_type TEXT,
            project TEXT,
            file_path TEXT DEFAULT '',
            metadata TEXT DEFAULT '',
            line_start INTEGER DEFAULT 0,
            line_end INTEGER DEFAULT 0,
            UNIQUE(entity, project, file_path)
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY,
            from_entity TEXT,
            relation TEXT,
            to_entity TEXT,
            project TEXT,
            UNIQUE(from_entity, relation, to_entity, project)
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS scan_state (
            id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            project TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            UNIQUE(file_path, project)
        )''')
        self.conn.commit()

    def add_entity(self, entity, entity_type, project):
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO entities (entity, entity_type, project) VALUES (?, ?, ?)''', (entity, entity_type, project))
        self.conn.commit()

    def add_relation(self, from_entity, relation, to_entity, project):
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO relations (from_entity, relation, to_entity, project) VALUES (?, ?, ?, ?)''', (from_entity, relation, to_entity, project))
        self.conn.commit()

    def get_entities(self, project):
        cur = self.conn.cursor()
        cur.execute('''SELECT entity, entity_type FROM entities WHERE project=?''', (project,))
        return cur.fetchall()

    def get_relations(self, project):
        cur = self.conn.cursor()
        cur.execute('''SELECT from_entity, relation, to_entity FROM relations WHERE project=?''', (project,))
        return cur.fetchall()

    def upsert_entity(self, entity, entity_type, project, file_path="", metadata="", line_start=0, line_end=0):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO entities (entity, entity_type, project, file_path, metadata, line_start, line_end)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (entity, entity_type, project, file_path, metadata, line_start, line_end),
        )
        self.conn.commit()
        return cur.lastrowid

    def upsert_relation(self, from_entity, relation, to_entity, project):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO relations (from_entity, relation, to_entity, project)"
            " VALUES (?, ?, ?, ?)",
            (from_entity, relation, to_entity, project),
        )
        self.conn.commit()

    def delete_entities_for_file(self, file_path, project):
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM entities WHERE file_path=? AND project=?",
            (file_path, project),
        )
        self.conn.commit()

    def get_scan_state(self, file_path, project) -> str | None:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT sha256 FROM scan_state WHERE file_path=? AND project=?",
            (file_path, project),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def set_scan_state(self, file_path, project, sha256):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO scan_state (file_path, project, sha256) VALUES (?, ?, ?)",
            (file_path, project, sha256),
        )
        self.conn.commit()

    def delete_scan_state(self, file_path, project):
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM scan_state WHERE file_path=? AND project=?",
            (file_path, project),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
