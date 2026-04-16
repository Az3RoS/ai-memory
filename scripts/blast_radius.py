"""
blast_radius.py — Impact analysis engine for code changes.

Functions:
    get_blast_radius(conn, project, changed_files, max_depth) -> dict
    format_blast_radius_md(blast_result, project) -> string
    get_risk_factors(blast_result, changed_files) -> list of strings
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

# ── Risk path patterns ─────────────────────────────────────────────────────────

_HIGH_RISK_PATHS = re.compile(
    r"(auth|security|payment|billing|password|secret|token|credential|permission|role|admin)",
    re.IGNORECASE,
)
_CONFIG_PATHS = re.compile(r"\.(env|config|yml|yaml|toml|json|ini)$", re.IGNORECASE)
_TEST_INDICATORS = re.compile(r"(test|spec|__test__|_test\.|\.test\.)", re.IGNORECASE)


# ── BFS traversal ─────────────────────────────────────────────────────────────

def _get_entity_ids_for_files(cur, project: str, changed_files: list[str]) -> set[int]:
    """Look up entity IDs for all entities in changed_files."""
    entity_ids: set[int] = set()
    for file_path in changed_files:
        cur.execute(
            "SELECT id FROM entities WHERE project=? AND file_path LIKE ?",
            (project, f"%{file_path}%"),
        )
        for row in cur.fetchall():
            entity_ids.add(row[0])
    return entity_ids


def _get_entity_names_for_ids(cur, entity_ids: set[int]) -> dict[int, str]:
    if not entity_ids:
        return {}
    placeholders = ",".join("?" for _ in entity_ids)
    cur.execute(
        f"SELECT id, entity FROM entities WHERE id IN ({placeholders})",
        list(entity_ids),
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def _get_dependents(cur, project: str, entity_names: set[str]) -> set[str]:
    """Return names of entities that import/call/depend on any of entity_names."""
    if not entity_names:
        return set()
    dependents: set[str] = set()
    for name in entity_names:
        cur.execute(
            """SELECT e.entity FROM relations r
               JOIN entities e ON e.entity = r.from_entity AND e.project = r.project
               WHERE r.project=? AND r.to_entity=?
               AND r.relation IN ('imports','calls','depends_on','inherits')""",
            (project, name),
        )
        for row in cur.fetchall():
            dependents.add(row[0])
    return dependents


def _get_test_entities(cur, project: str, entity_names: set[str]) -> set[str]:
    """Find test entities that test the given entities (tested_by relation)."""
    if not entity_names:
        return set()
    tests: set[str] = set()
    for name in entity_names:
        cur.execute(
            """SELECT e.entity FROM relations r
               JOIN entities e ON e.entity = r.from_entity AND e.project = r.project
               WHERE r.project=? AND r.to_entity=? AND r.relation='tested_by'""",
            (project, name),
        )
        for row in cur.fetchall():
            tests.add(row[0])
        # Also: entities with type 'test' that import this entity
        cur.execute(
            """SELECT e.entity FROM relations r
               JOIN entities e ON e.entity = r.from_entity AND e.project = r.project AND e.entity_type = 'test'
               WHERE r.project=? AND r.to_entity=? AND r.relation='imports'""",
            (project, name),
        )
        for row in cur.fetchall():
            tests.add(row[0])
    return tests


def _get_file_for_entity(cur, project: str, entity_name: str) -> Optional[str]:
    cur.execute(
        "SELECT file_path FROM entities WHERE project=? AND entity=? LIMIT 1",
        (project, entity_name),
    )
    row = cur.fetchone()
    return row[0] if row else None


# ── Public API ─────────────────────────────────────────────────────────────────

def get_blast_radius(conn, project: str, changed_files: list[str], max_depth: int = 2) -> dict:
    """
    BFS from entities in changed_files through import/call/dependency edges.
    Handles cycles via visited set.

    Returns:
        {
          direct_impact: {entity_name: file_path},   depth=1
          indirect_impact: {entity_name: file_path}, depth=2..max_depth
          test_impact: {entity_name: file_path},
          total_files: int,
          depth_map: {entity_name: depth},
        }
    """
    cur = conn.cursor()

    # Seed: all entity names in the changed files
    seed_ids = _get_entity_ids_for_files(cur, project, changed_files)
    seed_names = set(_get_entity_names_for_ids(cur, seed_ids).values())

    visited: set[str] = set(seed_names)
    direct_impact: dict[str, Optional[str]] = {}
    indirect_impact: dict[str, Optional[str]] = {}
    depth_map: dict[str, int] = {n: 0 for n in seed_names}

    frontier = seed_names.copy()

    for depth in range(1, max_depth + 1):
        if not frontier:
            break
        next_frontier: set[str] = set()
        dependents = _get_dependents(cur, project, frontier)
        for dep in dependents:
            if dep in visited:
                continue
            visited.add(dep)
            depth_map[dep] = depth
            fp = _get_file_for_entity(cur, project, dep)
            if depth == 1:
                direct_impact[dep] = fp
            else:
                indirect_impact[dep] = fp
            next_frontier.add(dep)
        frontier = next_frontier

    # Test impact
    all_impacted = set(seed_names) | set(direct_impact) | set(indirect_impact)
    test_names = _get_test_entities(cur, project, all_impacted)
    test_impact = {
        t: _get_file_for_entity(cur, project, t)
        for t in test_names
    }

    # Count distinct files
    all_files: set[str] = set(f for f in changed_files if f)
    for fp in list(direct_impact.values()) + list(indirect_impact.values()) + list(test_impact.values()):
        if fp:
            all_files.add(fp)

    return {
        "direct_impact": direct_impact,
        "indirect_impact": indirect_impact,
        "test_impact": test_impact,
        "total_files": len(all_files),
        "depth_map": depth_map,
        "seed_files": changed_files,
    }


def format_blast_radius_md(blast_result: dict, project: str) -> str:
    """Format blast radius result as a markdown report."""
    lines = [
        f"# Blast Radius — {project}",
        "",
        f"**Changed files:** {len(blast_result.get('seed_files', []))}  ",
        f"**Total files impacted:** {blast_result.get('total_files', 0)}  ",
        "",
    ]

    seed_files = blast_result.get("seed_files", [])
    if seed_files:
        lines += ["## Changed Files", ""]
        for f in seed_files:
            lines.append(f"- `{f}`")
        lines.append("")

    direct = blast_result.get("direct_impact", {})
    if direct:
        lines += ["## Direct Impact (depth 1)", ""]
        for entity, fp in sorted(direct.items()):
            fp_str = f" — `{fp}`" if fp else ""
            lines.append(f"- **{entity}**{fp_str}")
        lines.append("")

    indirect = blast_result.get("indirect_impact", {})
    if indirect:
        lines += ["## Indirect Impact (depth 2+)", ""]
        depth_map = blast_result.get("depth_map", {})
        for entity, fp in sorted(indirect.items()):
            depth = depth_map.get(entity, "?")
            fp_str = f" — `{fp}`" if fp else ""
            lines.append(f"- **{entity}** (depth {depth}){fp_str}")
        lines.append("")

    test_impact = blast_result.get("test_impact", {})
    if test_impact:
        lines += ["## Test Coverage", ""]
        for entity, fp in sorted(test_impact.items()):
            fp_str = f" — `{fp}`" if fp else ""
            lines.append(f"- {entity}{fp_str}")
        lines.append("")

    # Gaps: impacted entities with no test coverage
    all_impacted = set(direct) | set(indirect)
    tested_entities_files = set(test_impact.values()) - {None}
    untested = [
        (e, f) for e, f in {**direct, **indirect}.items()
        if f and not any(f in (tf or "") for tf in tested_entities_files)
    ]
    if untested:
        lines += ["## Test Gaps (impacted but not tested)", ""]
        for entity, fp in sorted(untested)[:10]:
            lines.append(f"- `{fp}` — {entity}")
        lines.append("")

    return "\n".join(lines)


def get_risk_factors(blast_result: dict, changed_files: list[str]) -> list[str]:
    """
    Return a list of risk factor strings based on the blast result and changed files.
    """
    risks: list[str] = []

    # High-risk path names
    for f in changed_files:
        if _HIGH_RISK_PATHS.search(f):
            risks.append(f"High-risk path changed: {f}")

    # Config file changes
    for f in changed_files:
        if _CONFIG_PATHS.search(f):
            risks.append(f"Configuration file changed: {f}")

    # Wide blast radius
    total = blast_result.get("total_files", 0)
    if total > 20:
        risks.append(f"Wide blast radius: {total} files affected")
    elif total > 10:
        risks.append(f"Moderate blast radius: {total} files affected")

    # Test coverage gap
    direct = blast_result.get("direct_impact", {})
    test_impact = blast_result.get("test_impact", {})
    if direct and not test_impact:
        risks.append("No test coverage found for directly impacted files")
    elif len(direct) > len(test_impact) * 2:
        risks.append(
            f"Test coverage gap: {len(direct)} impacted entities but only {len(test_impact)} test entities"
        )

    return risks


# ── CLI entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import subprocess
    import json

    parser = argparse.ArgumentParser(description="Compute blast radius for changed files")
    parser.add_argument("--project", "-p")
    parser.add_argument("--files", nargs="*")
    parser.add_argument("--depth", type=int, default=2)
    args = parser.parse_args()

    repo_dir = Path.cwd()
    project = args.project or repo_dir.name

    if args.files:
        changed = args.files
    else:
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            changed = [f for f in out.splitlines() if f.strip()]
        except Exception:
            changed = []

    db_path = Path.home() / ".ai-memory" / "wiki" / f"{project}.db"
    if not db_path.exists():
        print(f"wiki.db not found at {db_path}. Run 'memory scan' first.")
        sys.exit(1)

    from db_wiki import DBWiki
    db = DBWiki(db_path)
    result = get_blast_radius(db.conn, project, changed, max_depth=args.depth)
    risks = get_risk_factors(result, changed)
    result["risk_factors"] = risks

    md = format_blast_radius_md(result, project)
    print(md)
    db.close()
