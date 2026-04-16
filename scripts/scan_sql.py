"""
scan_sql.py — SQL and migration file scanner using regex.

Functions:
    scan_file(file_path, project) -> (entities, relationships)
    parse_create_table(sql_content, file_path) -> entity dict
"""

from __future__ import annotations

import re
from pathlib import Path

# ── Patterns ───────────────────────────────────────────────────────────────────

_CREATE_TABLE = re.compile(
    r"CREATE\s+(?:TABLE|TABLE\s+IF\s+NOT\s+EXISTS)\s+[`\"\[]?(\w+)[`\"\]]?\s*\(([^;]+?)\)",
    re.IGNORECASE | re.DOTALL,
)
_ALTER_TABLE_ADD_FK = re.compile(
    r"ALTER\s+TABLE\s+[`\"\[]?(\w+)[`\"\]]?\s+ADD\s+(?:CONSTRAINT\s+\w+\s+)?FOREIGN\s+KEY\s*\([^)]+\)\s+REFERENCES\s+[`\"\[]?(\w+)[`\"\]]?",
    re.IGNORECASE,
)
_INLINE_FK = re.compile(
    r"REFERENCES\s+[`\"\[]?(\w+)[`\"\]]?",
    re.IGNORECASE,
)
_COLUMN = re.compile(
    r"^\s*[`\"\[]?(\w+)[`\"\]]?\s+(INTEGER|INT|BIGINT|SMALLINT|TINYINT|SERIAL|BIGSERIAL"
    r"|TEXT|VARCHAR|CHAR|CHARACTER\s+VARYING|CLOB"
    r"|REAL|FLOAT|DOUBLE|DECIMAL|NUMERIC|MONEY"
    r"|BOOLEAN|BOOL"
    r"|DATE|TIME|TIMESTAMP|DATETIME|INTERVAL"
    r"|BLOB|BYTEA|BINARY|VARBINARY|JSON|JSONB|UUID|ARRAY"
    r")(?:\s*\([^)]*\))?(.*?)$",
    re.IGNORECASE,
)
_PK_INLINE = re.compile(r"\bPRIMARY\s+KEY\b", re.IGNORECASE)
_NOT_NULL = re.compile(r"\bNOT\s+NULL\b", re.IGNORECASE)
_INDEX = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?\w+\s+ON\s+[`\"\[]?(\w+)[`\"\]]?",
    re.IGNORECASE,
)

# Alembic / Django migration markers
_ALEMBIC_CREATE = re.compile(
    r"op\.create_table\s*\(\s*['\"](\w+)['\"]",
    re.IGNORECASE,
)
_DJANGO_CREATE = re.compile(
    r"migrations\.CreateModel\s*\(\s*name\s*=\s*['\"](\w+)['\"]",
    re.IGNORECASE,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_create_table(sql_content: str, file_path: Path) -> dict:
    """
    Extract table name, columns with types/constraints, PKs, FKs from a
    CREATE TABLE statement body.
    """
    # Find all CREATE TABLE blocks
    entities = []
    for m in _CREATE_TABLE.finditer(sql_content):
        table_name = m.group(1)
        body = m.group(2)
        line_no = sql_content[: m.start()].count("\n") + 1

        columns: list[dict] = []
        primary_keys: list[str] = []
        foreign_keys: list[dict] = []

        for line in body.splitlines():
            line = line.strip().rstrip(",")
            if not line or line.upper().startswith("--"):
                continue

            # Table-level PK constraint
            if re.match(r"PRIMARY\s+KEY\s*\(", line, re.IGNORECASE):
                pk_cols = re.findall(r"\w+", line[line.index("(") + 1:])
                primary_keys.extend(pk_cols)
                continue

            # Table-level FK constraint
            fk_m = re.match(
                r"(?:CONSTRAINT\s+\w+\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+[`\"\[]?(\w+)[`\"\]]?",
                line, re.IGNORECASE,
            )
            if fk_m:
                foreign_keys.append({
                    "columns": [c.strip() for c in fk_m.group(1).split(",")],
                    "references": fk_m.group(2),
                })
                continue

            # Column definition
            col_m = _COLUMN.match(line)
            if col_m:
                col_name = col_m.group(1)
                col_type = col_m.group(2)
                rest = col_m.group(3)
                is_pk = bool(_PK_INLINE.search(rest))
                not_null = bool(_NOT_NULL.search(rest)) or is_pk

                # Inline FK
                inline_fk = _INLINE_FK.search(rest)
                if inline_fk:
                    foreign_keys.append({
                        "columns": [col_name],
                        "references": inline_fk.group(1),
                    })

                if is_pk:
                    primary_keys.append(col_name)

                columns.append({
                    "name": col_name,
                    "type": col_type.upper(),
                    "primary_key": is_pk,
                    "not_null": not_null,
                })

        entity = {
            "name": table_name,
            "type": "table",
            "file_path": str(file_path),
            "line_start": line_no,
            "line_end": line_no,
            "metadata": str({
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
            }),
        }
        entities.append(entity)

    return entities


def _parse_migration_file(content: str, file_path: Path) -> tuple[list[dict], list[dict]]:
    """Parse Alembic or Django migration files."""
    entities: list[dict] = []
    relationships: list[dict] = []

    # Alembic op.create_table(...)
    for m in _ALEMBIC_CREATE.finditer(content):
        table_name = m.group(1)
        line_no = content[: m.start()].count("\n") + 1
        entities.append({
            "name": table_name,
            "type": "table",
            "file_path": str(file_path),
            "line_start": line_no,
            "line_end": line_no,
            "metadata": str({"source": "alembic_migration"}),
        })

    # Django migrations.CreateModel(name=...)
    for m in _DJANGO_CREATE.finditer(content):
        model_name = m.group(1)
        line_no = content[: m.start()].count("\n") + 1
        entities.append({
            "name": model_name,
            "type": "table",
            "file_path": str(file_path),
            "line_start": line_no,
            "line_end": line_no,
            "metadata": str({"source": "django_migration"}),
        })

    return entities, relationships


# ── Public entry ───────────────────────────────────────────────────────────────

def scan_file(file_path: Path, project: str) -> tuple[list[dict], list[dict]]:
    """
    Parse a SQL or migration file. Returns (entities, relationships).
    Handles raw SQL, Alembic migrations, and Django migrations.
    """
    file_path = Path(file_path)
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [], []

    entities: list[dict] = []
    relationships: list[dict] = []

    # Detect file type
    path_str = str(file_path).lower()
    is_migration = "migration" in path_str or "alembic" in path_str

    if is_migration and file_path.suffix == ".py":
        ents, rels = _parse_migration_file(content, file_path)
        entities.extend(ents)
        relationships.extend(rels)
    else:
        # Raw SQL
        table_entities = parse_create_table(content, file_path)
        entities.extend(table_entities)

        # FK relationships from ALTER TABLE
        for m in _ALTER_TABLE_ADD_FK.finditer(content):
            relationships.append({
                "from": m.group(1),
                "relation": "references",
                "to": m.group(2),
            })

    # Build FK relationships from entity metadata
    for ent in entities:
        try:
            meta = eval(ent.get("metadata", "{}"))  # noqa: S307 — controlled internal data
            for fk in meta.get("foreign_keys", []):
                relationships.append({
                    "from": ent["name"],
                    "relation": "references",
                    "to": fk["references"],
                })
        except Exception:
            pass

    return entities, relationships
