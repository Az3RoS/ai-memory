"""
ingest.py — Parses the latest git commit and stores structured data in memory.db.
"""

import re
import subprocess
from pathlib import Path
from db_memory import DBMemory
from utils import slugify

def _git(cmd):
    try:
        return subprocess.check_output(["git"] + cmd, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""

def _changed_files():
    out = _git(["diff", "--name-only", "HEAD~1", "HEAD"])
    if not out:
        out = _git(["diff", "--cached", "--name-only"])
    return [f for f in out.splitlines() if f]

def _diff_stats():
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

def ingest_commit(db: DBMemory, project: str):
    msg = _git(["log", "-1", "--pretty=%B"])
    files = _changed_files()
    stats = _diff_stats()
    # ...parse message, classify, and insert into db...
    db.conn.execute("INSERT INTO memories (project, entry_type, summary, detail, tags, files) VALUES (?, ?, ?, ?, ?, ?)",
                   (project, "commit", msg.strip().splitlines()[0], str(stats), "", ",".join(files)))
    db.conn.commit()
