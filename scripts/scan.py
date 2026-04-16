"""
scan.py — Orchestrates codebase scanning and coordinates language-specific scanners.

Functions:
    full_scan(project_dir, project) -> dict stats
    incremental_scan(project_dir, project, changed_files) -> dict stats
    resolve_references(conn, project, entities, relationships) -> resolved relationships
    get_ignored_patterns() -> list of glob patterns
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from db_wiki import DBWiki

# ── Ignore patterns ────────────────────────────────────────────────────────────

_DEFAULT_IGNORES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".eggs", ".mypy_cache", ".pytest_cache", ".tox",
    "coverage", ".coverage", "htmlcov", ".next", ".nuxt", "out",
    ".ai-memory", ".ai-wiki", "migrations", "__snapshots__",
}

_EXTENSION_SCANNER = {
    ".py": "python",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".sql": "sql",
    ".psql": "sql",
}


def get_ignored_patterns() -> list[str]:
    """Return default ignore patterns, extended by .ai-wiki-ignore if it exists."""
    patterns = list(_DEFAULT_IGNORES)
    ignore_file = Path(".ai-wiki-ignore")
    if ignore_file.exists():
        for line in ignore_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def _should_ignore(path: Path, ignored: set[str]) -> bool:
    """Return True if any part of the path is in the ignore set."""
    for part in path.parts:
        if part in ignored:
            return True
    return False


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ── Scanners ────────────────────────────────────────────────────────────────────

def _dispatch_file(file_path: Path, project: str) -> tuple[list[dict], list[dict]]:
    """Dispatch a single file to the appropriate language scanner."""
    ext = file_path.suffix.lower()
    scanner_type = _EXTENSION_SCANNER.get(ext, "generic")

    try:
        if scanner_type == "python":
            from scan_python import scan_file
            return scan_file(file_path, project)
        elif scanner_type == "javascript":
            from scan_javascript import scan_file
            return scan_file(file_path, project)
        elif scanner_type == "sql":
            from scan_sql import scan_file
            return scan_file(file_path, project)
        else:
            from scan_generic import scan_config_files
            # scan_generic operates at project level; for individual files return empty
            return [], []
    except Exception:
        return [], []


def _insert_entities_and_relations(db: DBWiki, project: str, entities: list[dict], relationships: list[dict]):
    """Write entities and relationships into wiki.db."""
    for ent in entities:
        db.upsert_entity(
            entity=ent.get("name", ""),
            entity_type=ent.get("type", "unknown"),
            project=project,
            file_path=ent.get("file_path", ""),
            metadata=ent.get("metadata", ""),
            line_start=ent.get("line_start", 0),
            line_end=ent.get("line_end", 0),
        )
    for rel in relationships:
        db.upsert_relation(
            from_entity=rel.get("from", ""),
            relation=rel.get("relation", "imports"),
            to_entity=rel.get("to", ""),
            project=project,
        )


# ── Public API ─────────────────────────────────────────────────────────────────

def full_scan(project_dir: Path, project: str, db_path: Optional[Path] = None) -> dict:
    """
    Walk project tree, dispatch each file to its language scanner,
    insert results into wiki.db, regenerate wiki pages.
    Returns stats dict.
    """
    project_dir = Path(project_dir)
    if db_path is None:
        db_path = Path.home() / ".ai-memory" / "wiki" / f"{project}.db"

    db = DBWiki(db_path)
    ignored = set(get_ignored_patterns())

    stats = {"files_scanned": 0, "entities": 0, "relationships": 0, "errors": 0}
    all_entities: list[dict] = []
    all_relationships: list[dict] = []

    for file_path in sorted(project_dir.rglob("*")):
        if not file_path.is_file():
            continue
        if _should_ignore(file_path.relative_to(project_dir), ignored):
            continue
        try:
            sha = _file_sha256(file_path)
            rel_path = str(file_path.relative_to(project_dir))
            # Skip if unchanged
            if db.get_scan_state(rel_path, project) == sha:
                continue

            entities, relationships = _dispatch_file(file_path, project)
            _insert_entities_and_relations(db, project, entities, relationships)
            db.set_scan_state(rel_path, project, sha)

            all_entities.extend(entities)
            all_relationships.extend(relationships)
            stats["files_scanned"] += 1
            stats["entities"] += len(entities)
            stats["relationships"] += len(relationships)
        except Exception:
            stats["errors"] += 1

    # Resolve cross-file references
    if all_entities or all_relationships:
        resolve_references(db.conn, project, all_entities, all_relationships)

    # Regenerate wiki pages
    try:
        from wiki_gen import generate_all
        wiki_dir = project_dir / ".ai-wiki" / "wiki"
        generate_all(db.conn, project, wiki_dir)
    except Exception:
        pass

    db.close()
    return stats


def incremental_scan(project_dir: Path, project: str, changed_files: list[str],
                     db_path: Optional[Path] = None) -> dict:
    """
    Re-scan only changed files. Skip if SHA unchanged.
    For deleted files: remove entities + scan_state.
    Regenerate affected wiki pages.
    Returns stats dict.
    """
    project_dir = Path(project_dir)
    if db_path is None:
        db_path = Path.home() / ".ai-memory" / "wiki" / f"{project}.db"

    db = DBWiki(db_path)
    stats = {"files_scanned": 0, "files_deleted": 0, "entities": 0, "relationships": 0, "errors": 0}

    affected_pages: set[str] = set()

    for rel_path in changed_files:
        file_path = project_dir / rel_path
        try:
            if not file_path.exists():
                # Deleted file — remove entities and scan state
                db.delete_entities_for_file(rel_path, project)
                db.delete_scan_state(rel_path, project)
                stats["files_deleted"] += 1
                continue

            sha = _file_sha256(file_path)
            if db.get_scan_state(rel_path, project) == sha:
                continue  # unchanged

            # Remove stale entities for this file
            db.delete_entities_for_file(rel_path, project)

            entities, relationships = _dispatch_file(file_path, project)
            _insert_entities_and_relations(db, project, entities, relationships)
            db.set_scan_state(rel_path, project, sha)

            stats["files_scanned"] += 1
            stats["entities"] += len(entities)
            stats["relationships"] += len(relationships)

            # Track which page types are affected
            ext = Path(rel_path).suffix.lower()
            if ext == ".py":
                affected_pages.update({"architecture", "endpoints", "models", "services", "coverage"})
            elif ext in {".ts", ".tsx", ".js", ".jsx"}:
                affected_pages.update({"architecture", "endpoints", "components", "coverage"})
            elif ext in {".sql", ".psql"}:
                affected_pages.add("database")
            affected_pages.add("index")

        except Exception:
            stats["errors"] += 1

    # Regenerate only affected wiki pages
    if affected_pages:
        try:
            from wiki_gen import generate_all
            wiki_dir = project_dir / ".ai-wiki" / "wiki"
            generate_all(db.conn, project, wiki_dir)
        except Exception:
            pass

    db.close()
    return stats


def resolve_references(conn, project: str, entities: list[dict],
                       relationships: list[dict]) -> list[dict]:
    """
    Build name→id lookup from inserted entities.
    For unresolvable import targets: create stub entity (type='external').
    Return relationships with source_id and target_id populated.
    """
    import sqlite3

    # Build name lookup from db
    cur = conn.cursor()
    cur.execute(
        "SELECT id, entity FROM entities WHERE project = ?", (project,)
    )
    name_to_id: dict[str, int] = {row[1]: row[0] for row in cur.fetchall()}

    resolved = []
    for rel in relationships:
        from_name = rel.get("from", "")
        to_name = rel.get("to", "")

        source_id = name_to_id.get(from_name)
        target_id = name_to_id.get(to_name)

        if target_id is None and to_name:
            # Create external stub
            try:
                cur.execute(
                    "INSERT INTO entities (entity, entity_type, project, file_path, metadata, line_start, line_end)"
                    " VALUES (?, 'external', ?, '', '', 0, 0)",
                    (to_name, project),
                )
                conn.commit()
                target_id = cur.lastrowid
                name_to_id[to_name] = target_id
            except Exception:
                pass

        resolved.append({**rel, "source_id": source_id, "target_id": target_id})

    return resolved


# ── CLI entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scan codebase into wiki.db")
    parser.add_argument("--project", "-p", help="Project slug")
    parser.add_argument("--incremental", action="store_true", help="Incremental scan (uses git diff)")
    parser.add_argument("--files", nargs="*", help="Explicit file list for incremental scan")
    args = parser.parse_args()

    import subprocess
    project_dir = Path.cwd()
    project = args.project or project_dir.name

    if args.incremental:
        if args.files:
            changed = args.files
        else:
            try:
                out = subprocess.check_output(
                    ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                    stderr=subprocess.DEVNULL, text=True
                ).strip()
                changed = [f for f in out.splitlines() if f.strip()]
            except Exception:
                changed = []
        if changed:
            result = incremental_scan(project_dir, project, changed)
        else:
            result = {"files_scanned": 0, "note": "no changed files"}
    else:
        result = full_scan(project_dir, project)

    print(f"scan: {result}")
