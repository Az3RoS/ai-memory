"""
backfill.py — import existing git history into memory.db.

Called by setup.py on first install for repos with existing commits.
Scans:
  - Last 200 commits fully (diff stats, files changed)
  - ALL commit messages for decision/blocker keywords
  - Builds file co-occurrence data for pattern detection

Safe to call multiple times — skips if already backfilled.
Uses memory_ingest logic directly (no subprocess, same parsing).
"""

from __future__ import annotations

import re
import subprocess
import sys
import os
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
from typing import Optional

# Allow running from any directory
sys.path.insert(0, os.path.dirname(__file__))


from db_memory import DBMemory
from memory_ingest import _parse_message, _classify_files, _entry_type_from_commit

DECISION_KEYWORDS = re.compile(
    r"\b(decided|chose|switched|migrated|replaced|adopted|removed|deprecated|architecture|adr)\b",
    re.IGNORECASE,
)
BLOCKER_KEYWORDS = re.compile(
    r"\b(blocked|blocker|wip|todo|fixme|workaround|hack|debt|broken)\b",
    re.IGNORECASE,
)


def _git(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git"] + cmd, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _git_lines(cmd: list[str]) -> list[str]:
    out = _git(cmd)
    return [l for l in out.splitlines() if l.strip()]


def _get_commit_hashes(limit: int = 200) -> list[str]:
    """Get last N commit hashes, oldest first."""
    out = _git(["log", f"--max-count={limit}", "--pretty=format:%H", "--reverse"])
    return [h for h in out.splitlines() if h.strip()]


def _get_all_commit_messages() -> list[tuple[str, str, str]]:
    """
    Get ALL commit messages for decision/blocker scanning.
    Returns list of (hash, date, message).
    """
    out = _git(["log", "--pretty=format:%H%x1f%ad%x1f%s", "--date=short"])
    results = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 3:
            results.append((parts[0], parts[1], parts[2]))
    return results


def _get_commit_detail(commit_hash: str) -> dict:
    """Get full detail for a single commit."""
    # Message
    msg = _git(["show", "-s", "--pretty=format:%B", commit_hash])
    # Date
    date_str = _git(["show", "-s", "--pretty=format:%ad", "--date=short", commit_hash])
    # Author
    author = _git(["show", "-s", "--pretty=format:%an", commit_hash])
    # Files changed
    files_out = _git(["diff-tree", "--no-commit-id", "-r", "--name-only", commit_hash])
    files = [f for f in files_out.splitlines() if f.strip()]
    # Diff stats
    stat_out = _git(["diff-tree", "--no-commit-id", "-r", "--stat", commit_hash])
    added = removed = 0
    for line in stat_out.splitlines():
        m = re.search(r"(\d+) insertion", line)
        if m:
            added = int(m.group(1))
        m = re.search(r"(\d+) deletion", line)
        if m:
            removed = int(m.group(1))

    return {
        "hash":    commit_hash[:12],
        "msg":     msg,
        "date":    date_str or datetime.utcnow().strftime("%Y-%m-%d"),
        "author":  author,
        "files":   files,
        "added":   added,
        "removed": removed,
    }



def _already_backfilled(db: DBMemory, project: str) -> bool:
    cur = db.conn.cursor()
    cur.execute("SELECT COUNT(*) FROM memories WHERE project=?", (project,))
    count = cur.fetchone()[0]
    return count > 3


def backfill(
    db: DBMemory,
    project: str,
    limit: int = 200,
    force: bool = False,
    verbose: bool = True,
) -> dict:
    """
    Import existing git history into memory.db.

    Returns {"commits_imported": N, "decisions_found": M, "already_done": bool}
    """
    if not force and _already_backfilled(db, project):
        if verbose:
            print(f"  ~ backfill already done for '{project}'")
        return {"commits_imported": 0, "decisions_found": 0, "already_done": True}

    # Early exit if no git history (new project)
    if verbose:
        print(f"  Scanning git history (up to {limit} commits)...")
    hashes = _get_commit_hashes(limit=limit)
    if not hashes:
        if verbose:
            print("  No git history found. Skipping backfill.")
        return {"commits_imported": 0, "decisions_found": 0, "already_done": True}

    commits_imported = 0
    decisions_found = 0

    # Phase 1: Full ingest of last N commits
    for i, commit_hash in enumerate(hashes):
        detail = _get_commit_detail(commit_hash)
        msg = detail["msg"]
        if not msg:
            continue

        parsed = _parse_message(msg)
        tags = parsed["tags"] + _classify_files(detail["files"])

        # Build detail string
        detail_parts = []
        if parsed["scope"]:
            detail_parts.append(f"scope: {parsed['scope']}")
        if detail["added"] or detail["removed"]:
            detail_parts.append(f"+{detail['added']} -{detail['removed']} lines")
        if parsed["body"]:
            detail_parts.append(parsed["body"])
        if detail["author"]:
            detail_parts.append(f"by {detail['author']}")
        detail_str = " | ".join(detail_parts)

        entry_type = _entry_type_from_commit(parsed["type"])

        # Use the commit's actual timestamp
        created_at = f"{detail['date']} 12:00:00"

        db.conn.execute(
            """
            INSERT INTO memories (project, entry_type, summary, detail, tags, files, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project,
                entry_type,
                parsed["desc"],
                detail_str,
                ",".join(set(tags)),
                ",".join(detail["files"][:20]),
                created_at,
            ),
        )
        commits_imported += 1

        # Decision entries
        if "decision" in tags:
            db.conn.execute(
                """
                INSERT INTO memories (project, entry_type, summary, detail, tags, files, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project,
                    "decision",
                    f"[ADR] {parsed['desc']}",
                    parsed["body"] or parsed["desc"],
                    "decision," + parsed["type"],
                    ",".join(detail["files"][:5]),
                    created_at,
                ),
            )
            decisions_found += 1

        if verbose and (i + 1) % 50 == 0:
            print(f"    ... processed {i + 1}/{len(hashes)} commits")

    db.conn.commit()

    # Phase 2: Scan ALL commit messages for decisions not captured above
    if verbose:
        print(f"  Scanning all commit messages for decisions...")

    all_messages = _get_all_commit_messages()
    already_in_recent = set(hashes)

    for commit_hash, date_str, subject in all_messages:
        if commit_hash in already_in_recent:
            continue  # already ingested above
        if DECISION_KEYWORDS.search(subject):
            db.conn.execute(
                """
                INSERT INTO memories (project, entry_type, summary, detail, tags, files, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project,
                    "decision",
                    f"[ADR] {subject}",
                    f"from git history (commit {commit_hash[:8]})",
                    "decision",
                    "",
                    f"{date_str} 12:00:00",
                ),
            )
            decisions_found += 1
        elif BLOCKER_KEYWORDS.search(subject):
            db.conn.execute(
                """
                INSERT INTO memories (project, entry_type, summary, detail, tags, files, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project,
                    "blocker",
                    subject,
                    f"from git history (commit {commit_hash[:8]})",
                    "blocker",
                    "",
                    f"{date_str} 12:00:00",
                ),
            )

    db.conn.commit()

    if verbose:
        print(f"  ✓ imported {commits_imported} commits, found {decisions_found} decisions")

    return {
        "commits_imported": commits_imported,
        "decisions_found":  decisions_found,
        "already_done":     False,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backfill git history into memory.db")
    parser.add_argument("--project", "-p", required=True)
    parser.add_argument("--db", required=True, help="Path to memory.db")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--force", action="store_true", help="Re-import even if already done")
    args = parser.parse_args()

    db = DBMemory(args.db)
    backfill(db, args.project, limit=args.limit, force=args.force)
    db.close()
