"""
memory_graph.py — knowledge graph builder.

Two outputs:
  ~/.ai-memory/entities/<project>.md   — human-readable entity map
  relations table in SQLite            — queryable edges

Entities are extracted heuristically from:
  - files (modules, classes inferred from path conventions)
  - tags  (technology names)
  - commit messages (noun phrases for known patterns)

Relations inferred:
  - file A modified alongside file B → "co-changes-with"
  - commit type "feat" adding a file → "implements"
  - commit type "fix" on a file → "fixes"
  - decision mentioning a file → "governs"

No LLM call — all heuristic, zero tokens at build time.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from memory_store import MemoryStore
from memory_config import Config


# ── Entity extraction ─────────────────────────────────────────────────────────

def _files_to_entities(files_str: str) -> list[str]:
    """Convert a comma-sep file list into entity names."""
    if not files_str:
        return []
    entities = []
    for f in files_str.split(","):
        f = f.strip()
        if not f:
            continue
        p = Path(f)
        # Use stem for source files, full relative path for configs
        if p.suffix in {".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs"}:
            entities.append(p.stem)
        elif p.suffix in {".yaml", ".yml", ".json", ".toml"}:
            entities.append(f)
        else:
            entities.append(p.name)
    return [e for e in entities if e]


def _tags_to_entities(tags_str: str) -> list[str]:
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


# ── Relation inference ────────────────────────────────────────────────────────

def _infer_relations(entry: dict) -> list[tuple[str, str, str]]:
    """Return list of (from, relation, to) triples."""
    relations = []
    entry_type = entry.get("entry_type", "")
    summary    = entry.get("summary", "")
    files      = _files_to_entities(entry.get("files", ""))
    tags       = _tags_to_entities(entry.get("tags", ""))

    # Co-change: files modified together
    for i, a in enumerate(files):
        for b in files[i+1:]:
            relations.append((a, "co-changes-with", b))

    # Type-based relations
    if entry_type == "decision":
        for f in files:
            relations.append(("decision", "governs", f))

    if entry_type in ("commit", "note"):
        for t in tags:
            for f in files:
                relations.append((f, "tagged-as", t))

    return relations


# ── Graph builder ─────────────────────────────────────────────────────────────

def update_graph(store: MemoryStore, project: str, cfg: Config):
    """
    Re-derive the knowledge graph for `project` from all stored entries.
    Updates both the SQLite relations table and the markdown entity file.
    """
    entries = store.all_for_project(project, limit=500)

    # Collect entities and edge counts
    entity_tags:   dict[str, set[str]]    = defaultdict(set)
    edge_counts:   dict[tuple, int]       = defaultdict(int)

    for entry in entries:
        files   = _files_to_entities(entry.get("files", ""))
        tags    = _tags_to_entities(entry.get("tags", ""))
        rels    = _infer_relations(entry)

        for f in files:
            entity_tags[f].update(tags)
        for rel in rels:
            edge_counts[rel] += 1

    # Write relations to DB (skip low-signal single occurrences for co-change)
    for (frm, rel, to), count in edge_counts.items():
        if rel == "co-changes-with" and count < 2:
            continue  # only persist repeated co-changes
        store.add_relation(project, frm, rel, to)

    # Write markdown entity map
    _write_entity_markdown(project, entity_tags, edge_counts, cfg)


def _write_entity_markdown(
    project: str,
    entity_tags: dict[str, set[str]],
    edge_counts: dict[tuple, int],
    cfg: Config,
):
    lines = [
        f"# Knowledge Graph — {project}",
        "",
        "## Entities",
        "",
    ]

    for entity in sorted(entity_tags.keys()):
        tags = ", ".join(sorted(entity_tags[entity]))
        lines.append(f"- **{entity}** — {tags}" if tags else f"- **{entity}**")

    # High-signal edges only
    lines += ["", "## Relations (count ≥ 2)", ""]
    high = [(k, v) for k, v in edge_counts.items() if v >= 2]
    high.sort(key=lambda x: -x[1])
    for (frm, rel, to), cnt in high[:50]:
        lines.append(f"- `{frm}` **{rel}** `{to}` ×{cnt}")

    out_path = cfg.entities_dir() / f"{project}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
