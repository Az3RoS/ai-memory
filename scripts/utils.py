"""
utils.py — Shared utility functions for ai-memory
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Any

def timestamp_scratch_notes(scratch_path: Path):
    """Add timestamps to lines in scratch.md that lack them."""
    lines = scratch_path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        if line.strip() and not re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', line):
            ts = datetime.now().strftime("%Y-%m-%dT%H:%M")
            out.append(f"[{ts}] {line}")
        else:
            out.append(line)
    scratch_path.write_text("\n".join(out), encoding="utf-8")

def slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")

def estimate_tokens(md: str) -> int:
    # Rough estimate: 1 token ≈ 4 chars
    return len(md) // 4

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def get_project_slug(index_path: Path) -> str:
    data = read_json(index_path)
    return data.get("slug", "default")
