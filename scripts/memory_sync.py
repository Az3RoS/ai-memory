"""
memory_sync.py — sync global DB → per-repo .ai-memory/ files.

Writes:
  .ai-memory/CONTEXT.md     — ambient inject (Copilot reads this automatically)
  .ai-memory/decisions.md   — architecture decisions ledger
  .ai-memory/index.json     — lightweight pointer for project detection

CONTEXT.md is kept deliberately lean (default 1500 tokens) so it doesn't
bloat every Copilot prompt. Deep context is fetched on-demand via /memory.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from memory_store import MemoryStore
from memory_config import Config
from memory_query import build_context_block, query_memory


# ── CONTEXT.md ────────────────────────────────────────────────────────────────

_CONTEXT_HEADER = """\
<!-- ai-memory: auto-generated — do not edit manually -->
<!-- Updated: {date} | Project: {project} -->
<!-- This file is injected into GitHub Copilot Chat as ambient context. -->
<!-- For deep search run: /memory <terms> in Copilot Chat -->

"""


def _write_context(
    store: MemoryStore,
    project: str,
    repo_dir: Path,
    token_budget: int = 1500,
):
    # Fetch decisions explicitly + recent entries, deduplicate by id
    decisions = query_memory(store, "decision", project=project, limit=20)
    recent    = query_memory(store, "",          project=project, limit=20)
    seen, entries = set(), []
    for e in decisions + recent:
        if e["id"] not in seen:
            seen.add(e["id"])
            entries.append(e)
    body    = build_context_block(entries, token_budget=token_budget, project=project)
    header  = _CONTEXT_HEADER.format(date=date.today(), project=project)
    content = header + body
    (repo_dir / "CONTEXT.md").write_text(content, encoding="utf-8")


# ── decisions.md ──────────────────────────────────────────────────────────────

def _write_decisions(store: MemoryStore, project: str, repo_dir: Path):
    rows = store.search("decision", project=project, limit=100)
    decisions = [r for r in rows if r.get("entry_type") == "decision"
                 or "decision" in (r.get("tags") or "")]

    lines = [
        f"# Architecture Decisions — {project}",
        f"_Last updated: {date.today()}_",
        "",
    ]

    if not decisions:
        lines.append("_No decisions recorded yet._")
    else:
        for d in decisions:
            lines += [
                f"## {d['date'][:10]} — {d['summary']}",
                "",
                d.get("detail") or "_No detail recorded._",
                "",
                f"**tags:** {d.get('tags','')}  |  **files:** {d.get('files','')}",
                "",
                "---",
                "",
            ]

    (repo_dir / "decisions.md").write_text("\n".join(lines), encoding="utf-8")


# ── index.json ────────────────────────────────────────────────────────────────

def _write_index(store: MemoryStore, project: str, repo_dir: Path, cfg: Config):
    proj_meta = cfg.get_project(project) or {}
    count = store.entry_count(project)
    cutoff = (date.today() - timedelta(days=7)).isoformat()

    recent = store.search("", project=project, limit=5)
    recent_summaries = [r["summary"] for r in recent if r.get("date", "") >= cutoff]

    index = {
        "slug":             project,
        "entry_count":      count,
        "last_sync":        date.today().isoformat(),
        "token_budget":     proj_meta.get("token_budget", 1500),
        "recent_summaries": recent_summaries,
        "global_db":        str(cfg.global_db_path()),
    }
    (repo_dir / "index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )


# ── .gitignore guard ──────────────────────────────────────────────────────────

def _ensure_gitignore(repo_dir: Path):
    """
    Ensure .ai-memory/ has a .gitignore that commits CONTEXT.md / decisions.md
    but ignores nothing (devs should be able to share them).
    Only blocks accidental large files.
    """
    gi = repo_dir / ".gitignore"
    if not gi.exists():
        gi.write_text("# ai-memory local overrides\n*.local\n", encoding="utf-8")


# ── Public API ────────────────────────────────────────────────────────────────

def sync_to_repo(
    store: MemoryStore,
    project: str,
    cfg: Config,
    token_budget: Optional[int] = None,
):
    repo_dir = cfg.repo_memory_dir(project)
    if repo_dir is None:
        return  # no repo registered, skip silently

    budget = token_budget or cfg.token_budget(project)

    _write_context(store, project, repo_dir, token_budget=budget)
    _write_decisions(store, project, repo_dir)
    _write_index(store, project, repo_dir, cfg)
    _ensure_gitignore(repo_dir)
