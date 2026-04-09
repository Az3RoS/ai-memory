"""
review.py — pre-push advisory code review.

Reads git diff, memory.db decisions/patterns, and guidelines.md.
Writes .ai-memory/review.md (not committed).
Prints advisory summary to terminal.
NEVER blocks the push.

Called by the pre-push hook.
"""

from __future__ import annotations

import re
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(__file__))

from memory_store import MemoryStore
from memory_config import Config


# ── Git helpers ────────────────────────────────────────────────────────────────

def _git(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git"] + cmd, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _changed_files_in_branch() -> list[str]:
    """Files changed vs main/master in this branch."""
    for base in ("main", "master", "HEAD~1"):
        out = _git(["diff", "--name-only", f"{base}...HEAD"])
        if out:
            return [f for f in out.splitlines() if f.strip()]
    return []


def _diff_stat_in_branch() -> str:
    for base in ("main", "master", "HEAD~1"):
        out = _git(["diff", "--stat", f"{base}...HEAD"])
        if out:
            return out
    return ""


def _current_branch() -> str:
    return _git(["rev-parse", "--abbrev-ref", "HEAD"])


def _commits_in_branch() -> list[str]:
    for base in ("main", "master"):
        out = _git(["log", f"{base}...HEAD", "--pretty=format:%s"])
        if out:
            return [l for l in out.splitlines() if l.strip()]
    return []


# ── Analysis ───────────────────────────────────────────────────────────────────

HIGH_RISK_PATHS = re.compile(
    r"(auth|security|payment|billing|password|secret|token|credential|permission|role|admin)",
    re.IGNORECASE,
)
MIGRATION_PATH = re.compile(r"(migration|alembic|flyway|liquibase)", re.IGNORECASE)
CONFIG_PATH = re.compile(r"\.(env|config|yml|yaml|toml|json)$", re.IGNORECASE)


def _score_risk(files: list[str], commit_messages: list[str]) -> str:
    """Return LOW, MEDIUM, or HIGH risk level."""
    score = 0

    for f in files:
        if HIGH_RISK_PATHS.search(f):
            score += 3
        if MIGRATION_PATH.search(f):
            score += 2
        if CONFIG_PATH.search(f):
            score += 1

    if score >= 6:
        return "HIGH"
    elif score >= 2:
        return "MEDIUM"
    return "LOW"


def _check_file_pairs(files: list[str], decisions: list[dict]) -> list[str]:
    """
    Basic pattern check: if src file changed but no corresponding test file.
    Returns list of warnings.
    """
    warnings = []
    src_files = [f for f in files if not re.search(r"test|spec|__test__", f, re.IGNORECASE)]
    test_files = set(f for f in files if re.search(r"test|spec|__test__", f, re.IGNORECASE))

    for src in src_files:
        # Heuristic: look for a test file with a related name
        base = Path(src).stem
        has_test = any(base.lower() in t.lower() for t in test_files)
        # Only warn for non-config, non-docs files
        ext = Path(src).suffix.lower()
        if not has_test and ext in {".py", ".ts", ".js", ".go", ".rs", ".java", ".kt"}:
            warnings.append(f"No test file found for {src}")

    # Cap at 3 warnings to avoid noise
    return warnings[:3]


def _extract_decisions_from_branch(commit_messages: list[str]) -> list[str]:
    """Find decision-flavored commit messages in this branch."""
    DECISION_WORDS = re.compile(
        r"\b(decided|chose|switched|migrated|replaced|adopted|removed|deprecated|architecture|adr)\b",
        re.IGNORECASE,
    )
    return [m for m in commit_messages if DECISION_WORDS.search(m)]


def _load_guidelines(mem_dir: Path) -> list[str]:
    """Load guidelines.md and extract rule lines."""
    guidelines_path = mem_dir / "guidelines.md"
    if not guidelines_path.exists():
        return []
    content = guidelines_path.read_text(encoding="utf-8", errors="ignore")
    # Extract lines that look like rules (start with - or *)
    rules = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ", "• ")):
            rules.append(line.lstrip("-*• ").strip())
    return rules[:20]


# ── Report generation ──────────────────────────────────────────────────────────

def generate_review(
    store: MemoryStore,
    project: str,
    cfg: Config,
    verbose: bool = True,
) -> dict:
    """
    Run the pre-push review analysis.
    Returns review data dict and writes .ai-memory/review.md.
    """
    branch = _current_branch()
    files  = _changed_files_in_branch()
    stat   = _diff_stat_in_branch()
    msgs   = _commits_in_branch()

    # Get decisions from memory
    all_entries = store.all_for_project(project, limit=100)
    decisions = [e for e in all_entries if e.get("entry_type") == "decision"]

    # Analysis
    risk = _score_risk(files, msgs)
    pair_warnings = _check_file_pairs(files, decisions)
    branch_decisions = _extract_decisions_from_branch(msgs)
    guidelines = _load_guidelines(cfg.repo_memory_dir(project) or Path(".ai-memory"))

    # Modules touched (top-level dirs)
    modules = sorted(set(f.split("/")[0] for f in files if "/" in f))

    review_data = {
        "branch":           branch,
        "files_changed":    len(files),
        "modules_touched":  modules,
        "risk":             risk,
        "pair_warnings":    pair_warnings,
        "branch_decisions": branch_decisions,
        "commit_count":     len(msgs),
        "generated_at":     datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

    # Write review.md
    mem_dir = cfg.repo_memory_dir(project)
    if mem_dir:
        _write_review_md(mem_dir, review_data, files, stat)

    # Print terminal summary
    if verbose:
        _print_summary(review_data)

    return review_data


def _write_review_md(mem_dir: Path, data: dict, files: list[str], stat: str):
    lines = [
        f"<!-- ai-memory: pre-push review — generated {data['generated_at']} -->",
        f"",
        f"## Review: {data['branch']}",
        f"",
        f"**Risk:** {data['risk']}  ",
        f"**Changes:** {data['files_changed']} files across {len(data['modules_touched'])} modules  ",
        f"**Commits:** {data['commit_count']}  ",
        f"**Generated:** {data['generated_at']}  ",
        f"",
    ]

    if data["branch_decisions"]:
        lines += ["### Decisions made in this branch", ""]
        for d in data["branch_decisions"]:
            lines.append(f"- {d}")
        lines.append("")

    if data["pair_warnings"]:
        lines += ["### Warnings", ""]
        for w in data["pair_warnings"]:
            lines.append(f"⚠ {w}")
        lines.append("")

    if data["modules_touched"]:
        lines += ["### Modules touched", ""]
        for m in data["modules_touched"]:
            lines.append(f"- `{m}`")
        lines.append("")

    if stat:
        lines += ["### Diff stat", "", "```", stat, "```", ""]

    if files:
        lines += ["### Files changed", ""]
        for f in files[:30]:
            lines.append(f"- {f}")
        if len(files) > 30:
            lines.append(f"- ... and {len(files) - 30} more")
        lines.append("")

    (mem_dir / "review.md").write_text("\n".join(lines), encoding="utf-8")


def _print_summary(data: dict):
    risk_icons = {"LOW": "[ok]", "MEDIUM": "[!]", "HIGH": "[!!]"}
    icon = risk_icons.get(data["risk"], "")

    width = 52
    sep = "-" * width
    print()
    print(sep)
    print("  ai-memory pre-push review")
    print(sep)
    print(f"  Risk:    {data['risk']}")
    print(f"  {icon} {data['files_changed']} files changed across "
          f"{len(data['modules_touched'])} modules")

    if data["branch_decisions"]:
        print(f"  [d] {len(data['branch_decisions'])} decision(s) in this branch")

    for w in data["pair_warnings"]:
        print(f"  [!] {w}")

    if data.get("branch_decisions"):
        print(f"  PR description: .ai-memory/pr-description.md")

    print(sep)
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", "-p")
    args = parser.parse_args()

    cfg = Config()
    project = args.project or cfg.detect_project()
    store = MemoryStore(cfg.global_db_path())
    generate_review(store, project, cfg)
