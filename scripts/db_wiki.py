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
            project TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY,
            from_entity TEXT,
            relation TEXT,
            to_entity TEXT,
            project TEXT
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

    def close(self):
        self.conn.close()
