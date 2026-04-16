"""
feature_close.py — Detects and processes feature completion.

Functions:
    detect_feature_close(diff_file_list, repo_dir) -> str | None  (feature dir path)
    close_feature(project, feature_dir, db_path) -> dict summary
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

# ── Status detection ───────────────────────────────────────────────────────────

_STATUS_PATTERN = re.compile(
    r"^Status:\s*(DONE|PARTIAL|ABANDONED)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_DATE_PATTERN = re.compile(r"^Date:\s*(.+)$", re.MULTILINE)
_START_DATE_PATTERN = re.compile(r"^Start[-_\s]?[Dd]ate:\s*(.+)$", re.MULTILINE)
_DECISION_PATTERN = re.compile(
    r"^[-*]\s*(decided|chose|switched|migrated|replaced|adopted|used|selected)\b.+",
    re.MULTILINE | re.IGNORECASE,
)
_ANTIPATTERN_PATTERN = re.compile(
    r"^[-*]\s*(avoided|don.?t|never|anti.?pattern|pitfall|issue|problem|bug):.+",
    re.MULTILINE | re.IGNORECASE,
)


def _read_file(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_feature_close(diff_file_list: list[str], repo_dir: Path) -> Optional[str]:
    """
    Scan diff_file_list for a commit.md whose Status is DONE/PARTIAL/ABANDONED.
    Returns the feature folder path (as string) if found, else None.

    A commit.md lives at:  .ai-memory/docs/02-feature/<FEAT_NNN_slug>/commit.md
    or at the feature root: features/<slug>/commit.md  (legacy)
    """
    repo_dir = Path(repo_dir)
    for rel_path in diff_file_list:
        p = Path(rel_path)
        if p.name != "commit.md":
            continue
        full_path = repo_dir / p
        content = _read_file(full_path)
        if content is None:
            continue
        if _STATUS_PATTERN.search(content):
            return str(p.parent)
    return None


def close_feature(project: str, feature_dir: Path, db_path: Optional[Path] = None) -> dict:
    """
    Process a completed feature:
    - Read commit.md for status, decisions, anti-patterns
    - Auto-fill completion date + duration in commit.md
    - Write a memory.db entry (type=feature_close)
    - Append to decisions.md in .ai-memory root
    - Update knowledge_graph in memory.db
    Returns summary dict.
    """
    feature_dir = Path(feature_dir)
    commit_md = feature_dir / "commit.md"
    content = _read_file(commit_md) or ""

    # Parse status
    status_match = _STATUS_PATTERN.search(content)
    status = status_match.group(1).upper() if status_match else "DONE"

    # Parse dates
    date_match = _DATE_PATTERN.search(content)
    start_match = _START_DATE_PATTERN.search(content)
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = start_match.group(1).strip() if start_match else ""

    # Calculate duration
    duration_days: Optional[int] = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            duration_days = (end_dt - start_dt).days
        except ValueError:
            pass

    # Auto-fill end date in commit.md if not set
    if date_match is None and commit_md.exists():
        updated = content + f"\nDate: {end_date}\n"
        if duration_days is not None:
            updated += f"Duration: {duration_days} days\n"
        try:
            commit_md.write_text(updated, encoding="utf-8")
        except OSError:
            pass

    # Extract decisions and anti-patterns from all feature docs
    decisions: list[str] = []
    antipatterns: list[str] = []
    for md_file in feature_dir.glob("*.md"):
        text = _read_file(md_file) or ""
        decisions.extend(m.group(0).strip() for m in _DECISION_PATTERN.finditer(text))
        antipatterns.extend(m.group(0).strip() for m in _ANTIPATTERN_PATTERN.finditer(text))

    # Get feature name from folder name
    feature_name = feature_dir.name

    # Count changed files (from scratch.md or notes)
    scratch = _read_file(feature_dir / "scratch.md") or ""
    files_changed: list[str] = re.findall(r"`([^`]+\.[a-zA-Z]+)`", scratch)[:20]

    summary = {
        "project": project,
        "feature": feature_name,
        "status": status,
        "end_date": end_date,
        "start_date": start_date,
        "duration_days": duration_days,
        "decisions": decisions,
        "antipatterns": antipatterns,
        "files_changed": files_changed,
    }

    # Write to memory.db
    if db_path is None:
        db_path = Path.home() / ".ai-memory" / "memory.db"

    try:
        from db_memory import DBMemory
        db = DBMemory(db_path)
        db.add_memory(
            project=project,
            entry_type="feature_close",
            summary=f"Feature {feature_name} closed: {status}",
            detail=json.dumps(summary),
            tags="feature,close," + status.lower(),
            files=",".join(files_changed),
            date=end_date,
        )

        # Add knowledge_graph edges for each decision
        for dec in decisions:
            db.add_knowledge_edge(
                entity_a=feature_name,
                relation="decision",
                entity_b=dec[:200],
                project=project,
            )
        db.close()
    except Exception:
        pass

    # Append decisions to .ai-memory/decisions.md
    _append_decisions_md(feature_dir, feature_name, decisions, antipatterns, end_date, status)

    return summary


def _append_decisions_md(
    feature_dir: Path,
    feature_name: str,
    decisions: list[str],
    antipatterns: list[str],
    date: str,
    status: str,
):
    """Append a decisions block to .ai-memory/decisions.md (walk up to find it)."""
    # Walk up to find .ai-memory
    cur = feature_dir
    decisions_file = None
    for _ in range(6):
        candidate = cur / "decisions.md"
        if candidate.exists():
            decisions_file = candidate
            break
        # Also check if parent is .ai-memory
        parent_candidate = cur.parent / ".ai-memory" / "decisions.md"
        if parent_candidate.exists():
            decisions_file = parent_candidate
            break
        cur = cur.parent

    if decisions_file is None:
        return

    if not decisions and not antipatterns:
        return

    block_lines = [
        f"\n## {feature_name} — {status} ({date})\n",
    ]
    if decisions:
        block_lines.append("**Decisions:**\n")
        for d in decisions[:10]:
            block_lines.append(f"- {d}\n")
    if antipatterns:
        block_lines.append("\n**Anti-patterns to avoid:**\n")
        for a in antipatterns[:5]:
            block_lines.append(f"- {a}\n")

    try:
        with decisions_file.open("a", encoding="utf-8") as f:
            f.writelines(block_lines)
    except OSError:
        pass


# ── CLI entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import subprocess

    parser = argparse.ArgumentParser(description="Detect and close completed features")
    parser.add_argument("--project", "-p")
    parser.add_argument("--feature-dir", help="Explicit feature dir to close")
    args = parser.parse_args()

    repo_dir = Path.cwd()
    project = args.project or repo_dir.name

    if args.feature_dir:
        feature_dir = Path(args.feature_dir)
        result = close_feature(project, feature_dir)
        print(json.dumps(result, indent=2))
    else:
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            diff_files = [f for f in out.splitlines() if f.strip()]
        except Exception:
            diff_files = []

        feature_dir_rel = detect_feature_close(diff_files, repo_dir)
        if feature_dir_rel:
            feature_dir = repo_dir / feature_dir_rel
            result = close_feature(project, feature_dir)
            print(json.dumps(result, indent=2))
        else:
            print("No feature close detected in this commit.")
