"""
memory_log.py — daily log writer.

Produces ~/.ai-memory/logs/YYYY-MM-DD.md for each project.
Captures: decisions, blockers, file changes, test mentions, free notes.
One log per calendar day; idempotent (safe to call multiple times).
"""

from __future__ import annotations

import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from memory_store import MemoryStore
from memory_config import Config


# ── Git helpers ───────────────────────────────────────────────────────────────

def _git(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git"] + cmd, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def _todays_commits() -> list[dict]:
    """Return list of {hash, subject} for today's commits in current repo."""
    today = date.today().isoformat()
    out = _git(["log", f"--since={today} 00:00:00", "--pretty=format:%H|%s"])
    commits = []
    for line in out.splitlines():
        if "|" in line:
            h, s = line.split("|", 1)
            commits.append({"hash": h[:8], "subject": s})
    return commits


def _todays_files() -> list[str]:
    """Distinct files changed in today's commits."""
    today = date.today().isoformat()
    out = _git(["log", f"--since={today} 00:00:00", "--name-only", "--pretty=format:"])
    return sorted(set(f for f in out.splitlines() if f.strip()))


def _test_summary() -> str:
    """Try to extract test result summary from recent git log."""
    log = _git(["log", "-5", "--pretty=%B"])
    import re
    m = re.search(r"(passed|failed|skipped|tests? ran|coverage)[^\n]*", log, re.IGNORECASE)
    return m.group(0) if m else ""


# ── Log builder ───────────────────────────────────────────────────────────────

def _log_path(cfg: Config, project: str, target_date: str | None = None) -> Path:
    dt = target_date or date.today().isoformat()
    return cfg.log_dir() / f"{project}-{dt}.md"


def _render_log(
    project: str,
    dt: str,
    entries: list[dict],
    commits: list[dict],
    files: list[str],
    test_summary: str,
    extra_note: str,
) -> str:
    lines = [
        f"# Daily Log — {project} — {dt}",
        f"_Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC_",
        "",
    ]

    # Summary section
    decisions = [e for e in entries if e.get("entry_type") == "decision"
                 or "decision" in (e.get("tags") or "")]
    blockers  = [e for e in entries if "blocker" in (e.get("tags") or "")]

    if decisions:
        lines += ["## Decisions", ""]
        for e in decisions:
            lines.append(f"- {e['summary']}")
            if e.get("detail"):
                lines.append(f"  > {e['detail']}")
        lines.append("")

    if blockers:
        lines += ["## Blockers / WIP", ""]
        for e in blockers:
            lines.append(f"- 🚧 {e['summary']}")
        lines.append("")

    if commits:
        lines += ["## Commits", ""]
        for c in commits:
            lines.append(f"- `{c['hash']}` {c['subject']}")
        lines.append("")

    if files:
        lines += ["## Files Changed", ""]
        for f in files[:40]:  # cap at 40
            lines.append(f"- `{f}`")
        if len(files) > 40:
            lines.append(f"- _...and {len(files)-40} more_")
        lines.append("")

    if test_summary:
        lines += ["## Tests", "", f"- {test_summary}", ""]

    # All entries for the day
    other = [e for e in entries if e not in decisions and e not in blockers]
    if other:
        lines += ["## Other Activity", ""]
        for e in other:
            tags = f" `{e.get('tags','')}` " if e.get("tags") else " "
            lines.append(f"- **{e.get('entry_type','note')}**{tags}{e['summary']}")
        lines.append("")

    if extra_note:
        lines += ["## Notes", "", extra_note, ""]

    return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def write_daily_log(
    store: MemoryStore,
    project: str,
    cfg: Optional[Config] = None,
    target_date: Optional[str] = None,
    extra_note: str = "",
):
    """
    Write (or overwrite) the daily log for `project`.
    Safe to call multiple times per day — always reflects latest state.
    """
    from memory_config import Config as _Config
    if cfg is None:
        cfg = _Config()

    dt      = target_date or date.today().isoformat()
    entries = store.recent_by_date(project, dt)
    commits = _todays_commits()
    files   = _todays_files()
    t_sum   = _test_summary()

    content = _render_log(project, dt, entries, commits, files, t_sum, extra_note)

    log_file = _log_path(cfg, project, dt)
    log_file.write_text(content, encoding="utf-8")
    return log_file

