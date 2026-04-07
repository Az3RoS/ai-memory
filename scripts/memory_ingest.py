"""
memory_ingest.py — extract structured memory events from git commits.

Called by the post-commit hook. Analyses:
  - commit message  (summary, type, tags)
  - changed files   (paths, extensions)
  - diff stats      (lines added/removed)
  - test results    (if present in message or CI output)

Uses heuristics only — no LLM call, so zero token cost.
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from memory_store import MemoryStore


# ── Conventional-commit parser ────────────────────────────────────────────────

CC_PATTERN = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r": (?P<desc>.+)$",
    re.IGNORECASE,
)

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
    except subprocess.CalledProcessError:
        return ""


def _changed_files() -> list[str]:
    out = _git(["diff", "--name-only", "HEAD~1", "HEAD"])
    if not out:
        out = _git(["diff", "--cached", "--name-only"])
    return [f for f in out.splitlines() if f]


def _diff_stats() -> dict:
    out = _git(["diff", "--stat", "HEAD~1", "HEAD"])
    added = removed = 0
    for line in out.splitlines():
        m = re.search(r"(\d+) insertion", line)
        if m:
            added = int(m.group(1))
        m = re.search(r"(\d+) deletion", line)
        if m:
            removed = int(m.group(1))
    return {"added": added, "removed": removed}


def _classify_files(files: list[str]) -> list[str]:
    """Return descriptive tags based on file extensions/paths."""
    tags = set()
    for f in files:
        p = Path(f)
        ext = p.suffix.lower()
        name = p.name.lower()
        parts = p.parts

        if ext in {".py"}:      tags.add("python")
        if ext in {".ts", ".tsx"}: tags.add("typescript")
        if ext in {".js", ".jsx"}: tags.add("javascript")
        if ext in {".sql"}:     tags.add("sql")
        if ext in {".md"}:      tags.add("docs")
        if ext in {".yaml", ".yml"}: tags.add("config")
        if ext in {".json"}:    tags.add("config")
        if ext in {".sh"}:      tags.add("scripts")
        if "test" in name or "spec" in name: tags.add("tests")
        if "migration" in f.lower():         tags.add("migration")
        if any(p in parts for p in ("hooks", "scripts", "ci", ".github")): tags.add("ci")
    return sorted(tags)


def _parse_message(msg: str) -> dict:
    """Parse commit message into structured fields."""
    result = {
        "type": "note",
        "scope": None,
        "breaking": False,
        "desc": msg,
        "body": "",
        "tags": [],
    }
    lines = msg.strip().splitlines()
    subject = lines[0].strip()
    body = "\n".join(lines[1:]).strip()

    m = CC_PATTERN.match(subject)
    if m:
        result["type"]     = m.group("type").lower()
        result["scope"]    = m.group("scope")
        result["breaking"] = bool(m.group("breaking"))
        result["desc"]     = m.group("desc")

    result["body"] = body

    # Tag from semantic content
    if DECISION_KEYWORDS.search(subject + " " + body):
        result["tags"].append("decision")
    if BLOCKER_KEYWORDS.search(subject + " " + body):
        result["tags"].append("blocker")
    if result["breaking"]:
        result["tags"].append("breaking-change")

    return result


def _entry_type_from_commit(commit_type: str) -> str:
    mapping = {
        "feat":     "commit",
        "fix":      "commit",
        "refactor": "commit",
        "perf":     "commit",
        "docs":     "note",
        "test":     "test",
        "chore":    "commit",
        "ci":       "commit",
        "build":    "commit",
        "style":    "commit",
        "revert":   "commit",
        "note":     "note",
    }
    return mapping.get(commit_type, "commit")


# ── Public API ────────────────────────────────────────────────────────────────

def ingest_commit(store: MemoryStore, project: str, message: Optional[str] = None):
    """
    Main ingest entry point. Reads current HEAD commit and stores structured
    memory entries. Safe to call multiple times — appends, never replaces.
    """
    msg = message or _git(["log", "-1", "--pretty=%B"])
    if not msg:
        msg = "no commit message"

    files   = _changed_files()
    stats   = _diff_stats()
    parsed  = _parse_message(msg)
    tags    = parsed["tags"] + _classify_files(files)

    # Build detail block
    detail_parts = []
    if parsed["scope"]:
        detail_parts.append(f"scope: {parsed['scope']}")
    if stats["added"] or stats["removed"]:
        detail_parts.append(f"+{stats['added']} -{stats['removed']} lines")
    if parsed["body"]:
        detail_parts.append(parsed["body"])
    detail = " | ".join(detail_parts)

    entry_type = _entry_type_from_commit(parsed["type"])

    store.add_entry(
        project=project,
        entry_type=entry_type,
        summary=parsed["desc"],
        detail=detail,
        tags=list(set(tags)),
        files=files[:20],  # cap at 20 to keep tokens lean
    )

    # If this commit looks like an architecture decision, record it separately
    if "decision" in tags:
        store.add_entry(
            project=project,
            entry_type="decision",
            summary=f"[ADR] {parsed['desc']}",
            detail=parsed["body"] or parsed["desc"],
            tags=["decision", parsed["type"]],
            files=files[:5],
        )
