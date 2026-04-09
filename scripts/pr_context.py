"""
pr_context.py — generate PR description from review data and branch decisions.

Reads .ai-memory/review.md (written by review.py).
Writes .ai-memory/pr-description.md.
Prints a short notice to terminal.

Called by the pre-push hook, after review.py.
"""

from __future__ import annotations

import re
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(__file__))

from memory_config import Config


def _git(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git"] + cmd, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _branch_commits() -> list[tuple[str, str]]:
    """Return (type, subject) tuples for commits in this branch."""
    results = []
    for base in ("main", "master"):
        out = _git(["log", f"{base}...HEAD", "--pretty=format:%s"])
        if out:
            for line in out.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Try to detect type from conventional commit
                m = re.match(r"^(feat|fix|docs|refactor|test|chore|perf|ci|build)(?:\([^)]+\))?: (.+)$", line, re.IGNORECASE)
                if m:
                    results.append((m.group(1).lower(), m.group(2)))
                else:
                    results.append(("other", line))
            return results
    return results


def _read_review_data(mem_dir: Path) -> dict:
    """Parse key fields from review.md."""
    review_path = mem_dir / "review.md"
    if not review_path.exists():
        return {}

    content = review_path.read_text(encoding="utf-8", errors="ignore")
    data = {}

    # Branch
    m = re.search(r"## Review: (.+)", content)
    if m:
        data["branch"] = m.group(1).strip()

    # Risk
    m = re.search(r"\*\*Risk:\*\* (LOW|MEDIUM|HIGH)", content)
    if m:
        data["risk"] = m.group(1)

    # Files changed
    m = re.search(r"\*\*Changes:\*\* (\d+) files", content)
    if m:
        data["files_changed"] = int(m.group(1))

    # Branch decisions
    decisions = []
    in_decisions = False
    for line in content.splitlines():
        if "### Decisions made" in line:
            in_decisions = True
            continue
        if in_decisions:
            if line.startswith("###"):
                break
            if line.startswith("- "):
                decisions.append(line[2:].strip())
    data["branch_decisions"] = decisions

    # Warnings
    warnings = []
    for line in content.splitlines():
        if line.startswith("⚠ "):
            warnings.append(line[2:].strip())
    data["warnings"] = warnings

    return data


def generate_pr_description(
    project: str,
    cfg: Config,
    verbose: bool = True,
) -> Path | None:
    """
    Generate .ai-memory/pr-description.md from review data + branch commits.
    Returns path to the written file, or None if mem_dir not found.
    """
    mem_dir = cfg.repo_memory_dir(project)
    if not mem_dir:
        return None

    review_data = _read_review_data(mem_dir)
    commits = _branch_commits()
    branch = review_data.get("branch") or _git(["rev-parse", "--abbrev-ref", "HEAD"])
    risk = review_data.get("risk", "LOW")
    files_changed = review_data.get("files_changed", len(commits))
    branch_decisions = review_data.get("branch_decisions", [])
    warnings = review_data.get("warnings", [])

    # Group commits by type
    by_type: dict[str, list[str]] = {}
    for ctype, subject in commits:
        by_type.setdefault(ctype, []).append(subject)

    # Build PR description
    lines = [
        f"<!-- ai-memory: pr-description — branch {branch} -->",
        f"",
        f"## Summary",
        f"",
    ]

    # Features
    if "feat" in by_type:
        for s in by_type["feat"]:
            lines.append(f"- {s}")

    # Fixes
    if "fix" in by_type:
        for s in by_type["fix"]:
            lines.append(f"- fix: {s}")

    # Refactors
    if "refactor" in by_type:
        for s in by_type["refactor"]:
            lines.append(f"- refactor: {s}")

    # Other types
    for ctype, subjects in by_type.items():
        if ctype not in ("feat", "fix", "refactor"):
            for s in subjects:
                lines.append(f"- {ctype}: {s}")

    if not commits:
        lines.append(f"- Changes in {files_changed} file(s)")

    lines.append("")

    # Decisions made
    if branch_decisions:
        lines += ["## Decisions made", ""]
        for d in branch_decisions:
            lines.append(f"- {d}")
        lines.append("")

    # Risk
    lines += [
        "## Risk assessment",
        "",
        f"**Risk level:** {risk}",
        "",
    ]
    if warnings:
        lines += ["**Warnings:**", ""]
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Test plan
    lines += [
        "## Test plan",
        "",
        "- [ ] All existing tests pass",
        "- [ ] New functionality covered by tests",
        "- [ ] Manual smoke test performed",
        "",
        f"---",
        f"*Generated by ai-memory on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
    ]

    out_path = mem_dir / "pr-description.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")

    if verbose:
        print(f"  ✓ PR description ready: .ai-memory/pr-description.md")

    return out_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", "-p")
    args = parser.parse_args()

    cfg = Config()
    project = args.project or cfg.detect_project()
    generate_pr_description(project, cfg)
