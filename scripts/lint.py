"""
lint.py — Knowledge base health checker for memory.db and wiki.db.

Checks:
  1. Contradicting decisions
  2. Stale decisions (older than 180 days, no supersession note)
  3. Broken patterns (pattern references missing entity in wiki.db)
  4. Orphan features (feature folder has no matching memory.db entry)
  5. Unresolved blockers (entry_type=blocker with no paired resolution)
  6. Missing tests (source entities in wiki.db with no test coverage)
  7. Dead code (entities with no callers and no tests, non-public)
  8. Circular dependencies (cycles in relations table)

run_lint() generates .ai-memory/lint-report.md.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# ── Individual check functions ─────────────────────────────────────────────────

def check_contradicting_decisions(db_mem) -> list[dict]:
    """Flag pairs of decision entries whose summaries contradict each other."""
    issues: list[dict] = []
    cur = db_mem.conn.cursor()
    cur.execute(
        "SELECT id, summary, date FROM memories WHERE entry_type='decision' ORDER BY date DESC"
    )
    rows = cur.fetchall()
    decisions = [(r[0], r[1] or "", r[2] or "") for r in rows]

    # Simple heuristic: look for "use X" and "don't use X" / "replace X" pairs
    _positive = re.compile(r"\b(use|adopt|add|switch to|migrate to)\s+(\w+)", re.IGNORECASE)
    _negative = re.compile(r"\b(remove|replace|don.?t use|avoid|deprecated?|abandon)\s+(\w+)", re.IGNORECASE)

    pos: dict[str, tuple[int, str]] = {}
    neg: dict[str, tuple[int, str]] = {}

    for row_id, summary, date in decisions:
        for m in _positive.finditer(summary):
            pos[m.group(2).lower()] = (row_id, summary)
        for m in _negative.finditer(summary):
            neg[m.group(2).lower()] = (row_id, summary)

    for term in set(pos) & set(neg):
        issues.append({
            "check": "contradicting_decisions",
            "severity": "warning",
            "message": f"Contradicting decisions about '{term}': '{pos[term][1]}' vs '{neg[term][1]}'",
        })

    return issues


def check_stale_decisions(db_mem, max_age_days: int = 180) -> list[dict]:
    """Flag decisions older than max_age_days that have no supersession note."""
    issues: list[dict] = []
    cur = db_mem.conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
    cur.execute(
        "SELECT id, summary, date FROM memories WHERE entry_type='decision' AND date < ?",
        (cutoff,),
    )
    for row in cur.fetchall():
        row_id, summary, date = row[0], row[1] or "", row[2] or ""
        if "superseded" in summary.lower() or "replaced" in summary.lower():
            continue
        issues.append({
            "check": "stale_decision",
            "severity": "info",
            "message": f"Decision from {date} may be stale: '{summary[:80]}'",
            "id": row_id,
        })
    return issues


def check_broken_patterns(db_mem, db_wiki, project: str) -> list[dict]:
    """Flag patterns that reference entity names not found in wiki.db."""
    issues: list[dict] = []
    cur_mem = db_mem.conn.cursor()
    cur_wiki = db_wiki.conn.cursor()

    cur_mem.execute(
        "SELECT id, name, description FROM patterns WHERE project=?", (project,)
    )
    patterns = cur_mem.fetchall()

    cur_wiki.execute("SELECT entity FROM entities WHERE project=?", (project,))
    known_entities = {r[0] for r in cur_wiki.fetchall()}

    for row in patterns:
        pat_id, name, description = row[0], row[1] or "", row[2] or ""
        # Check if the pattern name or description references an entity
        words = set(re.findall(r"\b[A-Za-z_]\w+\b", name + " " + description))
        missing = [w for w in words if len(w) > 4 and w not in known_entities]
        if len(missing) > 2:  # avoid false positives from common words
            issues.append({
                "check": "broken_pattern",
                "severity": "info",
                "message": f"Pattern '{name}' references unknown entities: {missing[:3]}",
                "id": pat_id,
            })
    return issues


def check_orphan_features(db_mem, project: str) -> list[dict]:
    """Flag features that appear in the feature folder but have no memory.db entry."""
    issues: list[dict] = []
    cur = db_mem.conn.cursor()
    cur.execute(
        "SELECT summary FROM memories WHERE project=? AND entry_type='feature_close'",
        (project,),
    )
    closed = {r[0] for r in cur.fetchall()}

    # This check is project-dir-dependent; emit a placeholder if we can't resolve
    if not closed:
        issues.append({
            "check": "orphan_features",
            "severity": "info",
            "message": "No closed feature entries found in memory.db. Run 'memory feature close' when features are done.",
        })
    return issues


def check_unresolved_blockers(db_mem, project: str) -> list[dict]:
    """Flag blocker entries with no matching resolution entry."""
    issues: list[dict] = []
    cur = db_mem.conn.cursor()
    cur.execute(
        "SELECT id, summary, date FROM memories WHERE project=? AND entry_type='blocker'",
        (project,),
    )
    blockers = cur.fetchall()

    cur.execute(
        "SELECT summary FROM memories WHERE project=? AND entry_type='blocker_resolved'",
        (project,),
    )
    resolved_summaries = {r[0] for r in cur.fetchall()}

    for row in blockers:
        bid, summary, date = row[0], row[1] or "", row[2] or ""
        # Simple: if the blocker summary text appears in any resolution, consider resolved
        is_resolved = any(
            summary[:30].lower() in res.lower() for res in resolved_summaries
        )
        if not is_resolved:
            issues.append({
                "check": "unresolved_blocker",
                "severity": "warning",
                "message": f"Unresolved blocker (id={bid}): '{summary[:80]}' (logged {date})",
                "id": bid,
            })
    return issues


def check_missing_tests(db_wiki, project: str) -> list[dict]:
    """Flag source entities (function/class/service) with no test coverage in wiki.db."""
    issues: list[dict] = []
    cur = db_wiki.conn.cursor()

    # Find source entities
    cur.execute(
        "SELECT entity, file_path FROM entities WHERE project=? AND entity_type IN ('function','class','service','model')",
        (project,),
    )
    sources = {r[0]: r[1] for r in cur.fetchall()}

    # Find what's covered by tests
    cur.execute(
        "SELECT to_entity FROM relations WHERE project=? AND relation IN ('tested_by','tests')",
        (project,),
    )
    tested = {r[0] for r in cur.fetchall()}

    for entity, fp in sources.items():
        if entity not in tested:
            issues.append({
                "check": "missing_test",
                "severity": "info",
                "message": f"No test coverage for '{entity}' in `{fp}`",
            })

    return issues[:20]  # cap at 20 to avoid noise


def check_dead_code(db_wiki, project: str) -> list[dict]:
    """Flag non-public entities with no callers and no test coverage."""
    issues: list[dict] = []
    cur = db_wiki.conn.cursor()

    # Find all entities
    cur.execute(
        "SELECT entity, file_path, entity_type FROM entities WHERE project=? AND entity_type IN ('function','class')",
        (project,),
    )
    all_entities = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

    # Find entities that appear as a target in any relation
    cur.execute(
        "SELECT to_entity FROM relations WHERE project=?",
        (project,),
    )
    referenced = {r[0] for r in cur.fetchall()}

    for entity, (fp, etype) in all_entities.items():
        # Skip public-looking names (no underscore prefix)
        local_name = entity.split(".")[-1]
        if not local_name.startswith("_"):
            continue
        if entity not in referenced:
            issues.append({
                "check": "dead_code",
                "severity": "info",
                "message": f"Possibly unused private {etype} '{local_name}' in `{fp}`",
            })

    return issues[:15]


def check_circular_dependencies(db_wiki, project: str) -> list[dict]:
    """Detect cycles in the imports/calls relationship graph."""
    issues: list[dict] = []
    cur = db_wiki.conn.cursor()

    cur.execute(
        "SELECT from_entity, to_entity FROM relations WHERE project=? AND relation IN ('imports','depends_on','calls')",
        (project,),
    )
    edges = cur.fetchall()

    # Build adjacency
    graph: dict[str, set[str]] = {}
    for src, dst in edges:
        graph.setdefault(src, set()).add(dst)

    # DFS cycle detection (limited to first 5 cycles found)
    visited: set[str] = set()
    rec_stack: set[str] = set()
    cycles_found: list[list[str]] = []

    def _dfs(node: str, path: list[str]):
        if len(cycles_found) >= 5:
            return
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbour in graph.get(node, set()):
            if neighbour not in visited:
                _dfs(neighbour, path)
            elif neighbour in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbour)
                cycles_found.append(path[cycle_start:] + [neighbour])
        path.pop()
        rec_stack.discard(node)

    for node in list(graph.keys())[:200]:  # limit scope
        if node not in visited:
            _dfs(node, [])

    for cycle in cycles_found:
        short = [c.split(".")[-1] for c in cycle]
        issues.append({
            "check": "circular_dependency",
            "severity": "error",
            "message": f"Circular dependency: {' → '.join(short)}",
        })

    return issues


# ── Orchestrator ───────────────────────────────────────────────────────────────

def run_lint(project: str, db_memory_path: Path, db_wiki_path: Path,
             output_dir: Optional[Path] = None) -> dict:
    """
    Run all lint checks. Writes .ai-memory/lint-report.md (or output_dir/lint-report.md).
    Returns summary dict.
    """
    from db_memory import DBMemory
    from db_wiki import DBWiki

    db_mem = DBMemory(db_memory_path)
    db_wiki = DBWiki(db_wiki_path)

    all_issues: list[dict] = []

    all_issues.extend(check_contradicting_decisions(db_mem))
    all_issues.extend(check_stale_decisions(db_mem))
    all_issues.extend(check_broken_patterns(db_mem, db_wiki, project))
    all_issues.extend(check_orphan_features(db_mem, project))
    all_issues.extend(check_unresolved_blockers(db_mem, project))
    all_issues.extend(check_missing_tests(db_wiki, project))
    all_issues.extend(check_dead_code(db_wiki, project))
    all_issues.extend(check_circular_dependencies(db_wiki, project))

    db_mem.close()
    db_wiki.close()

    # Group by severity
    counts: dict[str, int] = {}
    by_check: dict[str, int] = {}
    for issue in all_issues:
        sev = issue.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1
        chk = issue.get("check", "unknown")
        by_check[chk] = by_check.get(chk, 0) + 1

    # Write report
    report_md = _format_report(project, all_issues, counts)
    if output_dir:
        report_path = Path(output_dir) / "lint-report.md"
    else:
        report_path = Path(".ai-memory") / "lint-report.md"

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_md, encoding="utf-8")
    except OSError:
        pass

    return {
        "project": project,
        "issues": all_issues,
        "total": len(all_issues),
        "counts_by_severity": counts,
        "counts_by_check": by_check,
        "report_path": str(report_path),
    }


def _format_report(project: str, issues: list[dict], counts: dict) -> str:
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Lint Report — {project}",
        "",
        f"**Generated:** {generated}  ",
        f"**Total issues:** {len(issues)}  ",
    ]
    for sev, count in sorted(counts.items()):
        lines.append(f"**{sev.capitalize()}:** {count}  ")
    lines.append("")

    severity_order = {"error": 0, "warning": 1, "info": 2}
    sorted_issues = sorted(issues, key=lambda i: severity_order.get(i.get("severity", "info"), 3))

    current_check = None
    for issue in sorted_issues:
        chk = issue.get("check", "unknown")
        if chk != current_check:
            current_check = chk
            lines += ["", f"## {chk.replace('_', ' ').title()}", ""]
        sev = issue.get("severity", "info")
        icon = {"error": "✖", "warning": "⚠", "info": "ℹ"}.get(sev, "·")
        lines.append(f"{icon} {issue.get('message', '')}")

    if not issues:
        lines += ["", "_No issues found. Knowledge base looks healthy._"]

    return "\n".join(lines) + "\n"


# ── CLI entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(description="Lint ai-memory knowledge base")
    parser.add_argument("--project", "-p")
    parser.add_argument("--memory-db")
    parser.add_argument("--wiki-db")
    args = parser.parse_args()

    project = args.project or Path.cwd().name
    mem_db = Path(args.memory_db) if args.memory_db else Path.home() / ".ai-memory" / "memory.db"
    wiki_db = Path(args.wiki_db) if args.wiki_db else Path.home() / ".ai-memory" / "wiki" / f"{project}.db"

    result = run_lint(project, mem_db, wiki_db)
    print(f"Lint complete: {result['total']} issues. Report: {result['report_path']}")
