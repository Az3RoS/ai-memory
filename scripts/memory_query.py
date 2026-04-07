"""
memory_query.py — search memory and assemble token-budgeted context blocks.

Token budget strategy:
  1. Decisions and blockers always included first (highest signal).
  2. Recent entries next (last 7 days).
  3. FTS-ranked results fill remaining budget.
  4. Each entry is rendered as compact markdown to minimise token use.
  5. A rough 4-chars-per-token heuristic keeps us well within budget.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from memory_store import MemoryStore


# ── Token estimation ──────────────────────────────────────────────────────────

CHARS_PER_TOKEN = 4  # conservative approximation


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


# ── Entry rendering ───────────────────────────────────────────────────────────

ENTRY_ICONS = {
    "decision":    "📐",
    "blocker":     "🚧",
    "commit":      "📝",
    "note":        "💡",
    "test":        "🧪",
    "file_change": "📁",
}


def _render_entry(entry: dict[str, Any], compact: bool = False) -> str:
    icon  = ENTRY_ICONS.get(entry.get("entry_type", "note"), "•")
    date  = entry.get("date", "")[:10]
    summ  = entry.get("summary", "").strip()
    tags  = entry.get("tags", "")
    files = entry.get("files", "")

    tag_str  = f" [{tags}]"  if tags  else ""
    file_str = f"\n  files: {files}" if files and not compact else ""

    detail = entry.get("detail", "").strip()
    detail_str = f"\n  {detail}" if detail and not compact else ""

    return f"{icon} **{date}** {summ}{tag_str}{detail_str}{file_str}"


# ── Query ─────────────────────────────────────────────────────────────────────

def query_memory(
    store: MemoryStore,
    terms: str,
    project: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Returns a ranked list of entries relevant to `terms`.
    When terms is empty, returns recent entries sorted by date.
    """
    return store.search(terms, project=project, limit=limit)


# ── Context assembly ─────────────────────────────────────────────────────────

def build_context_block(
    entries: list[dict],
    token_budget: int = 2000,
    project: str | None = None,
) -> str:
    """
    Assemble a markdown context block from entries, respecting token budget.

    Structure:
        ## AI Memory Context
        ### Decisions & Architecture
        ...
        ### Recent Activity (last 7 days)
        ...
        ### Related Memory
        ...
        ---
        _Generated YYYY-MM-DD | N entries | ~T tokens_
    """
    if not entries:
        return "<!-- ai-memory: no relevant context found -->"

    decisions  = [e for e in entries if e.get("entry_type") == "decision" or "decision" in (e.get("tags") or "")]
    blockers   = [e for e in entries if "blocker" in (e.get("tags") or "")]
    cutoff     = (date.today() - timedelta(days=7)).isoformat()
    recent     = [e for e in entries if e.get("date", "") >= cutoff
                  and e not in decisions and e not in blockers]
    rest       = [e for e in entries if e not in decisions
                  and e not in blockers and e not in recent]

    sections: list[tuple[str, list[dict], bool]] = [
        ("Decisions & Architecture", decisions, False),
        ("Blockers", blockers, False),
        ("Recent Activity (last 7 days)", recent, True),
        ("Related Memory", rest, True),
    ]

    lines: list[str] = ["## AI Memory Context", ""]
    used_tokens = _estimate_tokens("## AI Memory Context\n")

    for heading, group, compact in sections:
        if not group:
            continue
        section_header = f"### {heading}\n"
        used_tokens += _estimate_tokens(section_header)
        if used_tokens >= token_budget:
            break
        lines.append(f"### {heading}")

        for entry in group:
            rendered = _render_entry(entry, compact=compact)
            cost = _estimate_tokens(rendered)
            if used_tokens + cost > token_budget:
                lines.append("_...truncated to fit token budget_")
                break
            lines.append(rendered)
            used_tokens += cost

        lines.append("")

    proj_tag = f"project: {project} | " if project else ""
    footer = (
        f"---\n_Generated {date.today()} | "
        f"{proj_tag}{len(entries)} entries | ~{used_tokens} tokens_"
    )
    lines.append(footer)

    return "\n".join(lines)


# ── Targeted fetch for /memory slash command ──────────────────────────────────

def fetch_for_copilot(
    store: MemoryStore,
    terms: str,
    project: str | None,
    token_budget: int = 1500,
) -> str:
    """
    Used by the VS Code slash command handler.
    Returns a tightly-budgeted context block for direct Copilot injection.
    """
    results = query_memory(store, terms, project=project, limit=15)
    return build_context_block(results, token_budget=token_budget, project=project)
