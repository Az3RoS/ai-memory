"""
sync.py — Reads memory.db and generates .ai-memory/CONTEXT.md and patterns.md
"""

from pathlib import Path
from db_memory import DBMemory
from utils import estimate_tokens

def sync_to_repo(db: DBMemory, project: str, repo_dir: Path, token_budget: int = 1500):
    # Fetch recent entries and decisions
    cur = db.conn.execute("SELECT * FROM memories WHERE project=? ORDER BY date DESC, id DESC LIMIT 40", (project,))
    entries = cur.fetchall()
    lines = [f"# CONTEXT for {project}", ""]
    for e in entries:
        lines.append(f"- {e['date']} {e['entry_type']}: {e['summary']}")
    content = "\n".join(lines)
    (repo_dir / "CONTEXT.md").write_text(content, encoding="utf-8")
    # TODO: generate patterns.md from file_pairs
