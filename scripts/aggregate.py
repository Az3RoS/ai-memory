"""
aggregate.py — Sprint and cross-project aggregation.

Functions:
    generate_sprint_summary(db_path, project, start_date, end_date) -> dict
    export_sprint_md(summary) -> string
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_date(value: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return None


def _in_range(entry_date: str, start: Optional[date], end: Optional[date]) -> bool:
    d = _parse_date(entry_date or "")
    if d is None:
        return True  # include undated entries
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_sprint_summary(
    db_path: Path,
    project: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    cross_project: bool = False,
) -> dict:
    """
    Query memory.db for all entries within the date range and aggregate them.

    Returns a summary dict:
        {
          project, date_range,
          decisions: [...],
          blockers_resolved: [...],
          features_completed: [...],
          patterns_detected: [...],
          entry_counts: {entry_type: count},
          total_entries: int,
        }
    """
    from db_memory import DBMemory

    db_path = Path(db_path)
    db = DBMemory(db_path)
    cur = db.conn.cursor()

    start = _parse_date(start_date) if start_date else None
    end = _parse_date(end_date) if end_date else None

    # Query all relevant entries
    if cross_project:
        cur.execute(
            "SELECT project, entry_type, summary, detail, tags, files, date FROM memories ORDER BY date DESC"
        )
    else:
        cur.execute(
            "SELECT project, entry_type, summary, detail, tags, files, date FROM memories WHERE project=? ORDER BY date DESC",
            (project,),
        )

    rows = cur.fetchall()

    decisions: list[dict] = []
    blockers_resolved: list[dict] = []
    features_completed: list[dict] = []
    patterns_detected: list[dict] = []
    entry_counts: dict[str, int] = {}

    for row in rows:
        proj, entry_type, summary, detail, tags, files, entry_date = row

        if not _in_range(entry_date or "", start, end):
            continue

        entry_counts[entry_type] = entry_counts.get(entry_type, 0) + 1

        record = {
            "project": proj,
            "summary": summary,
            "date": entry_date,
            "tags": (tags or "").split(","),
        }

        if entry_type == "decision":
            decisions.append(record)
        elif entry_type in ("blocker_resolved", "fix"):
            blockers_resolved.append(record)
        elif entry_type == "feature_close":
            try:
                detail_data = json.loads(detail or "{}")
            except (json.JSONDecodeError, TypeError):
                detail_data = {}
            features_completed.append({
                **record,
                "feature": detail_data.get("feature", summary),
                "status": detail_data.get("status", "DONE"),
                "duration_days": detail_data.get("duration_days"),
            })
        elif entry_type == "pattern":
            patterns_detected.append(record)

    db.close()

    return {
        "project": project if not cross_project else "all",
        "date_range": {
            "start": start_date,
            "end": end_date,
        },
        "decisions": decisions,
        "blockers_resolved": blockers_resolved,
        "features_completed": features_completed,
        "patterns_detected": patterns_detected,
        "entry_counts": entry_counts,
        "total_entries": sum(entry_counts.values()),
    }


def export_sprint_md(summary: dict) -> str:
    """Format sprint summary as markdown."""
    project = summary.get("project", "")
    date_range = summary.get("date_range", {})
    start = date_range.get("start") or "—"
    end = date_range.get("end") or "—"
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# Sprint Summary — {project}",
        "",
        f"**Period:** {start} → {end}  ",
        f"**Total entries:** {summary.get('total_entries', 0)}  ",
        f"**Generated:** {generated}  ",
        "",
    ]

    # Entry counts
    counts = summary.get("entry_counts", {})
    if counts:
        lines += ["## Activity Breakdown", ""]
        for etype, count in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"- **{etype}**: {count}")
        lines.append("")

    # Features completed
    features = summary.get("features_completed", [])
    if features:
        lines += ["## Features Completed", ""]
        for f in features:
            status = f.get("status", "DONE")
            days = f.get("duration_days")
            duration_str = f" ({days}d)" if days is not None else ""
            proj_str = f" [{f.get('project', '')}]" if project == "all" else ""
            lines.append(f"- **{f.get('feature', f.get('summary', ''))}**{proj_str} — {status}{duration_str}")
            if f.get("date"):
                lines.append(f"  Closed: {f['date']}")
        lines.append("")

    # Decisions made
    decisions = summary.get("decisions", [])
    if decisions:
        lines += ["## Decisions Made", ""]
        for d in decisions:
            proj_str = f" [{d.get('project', '')}]" if project == "all" else ""
            lines.append(f"- {d.get('summary', '')}{proj_str}")
        lines.append("")

    # Blockers resolved
    blockers = summary.get("blockers_resolved", [])
    if blockers:
        lines += ["## Blockers Resolved", ""]
        for b in blockers:
            proj_str = f" [{b.get('project', '')}]" if project == "all" else ""
            lines.append(f"- {b.get('summary', '')}{proj_str}")
        lines.append("")

    # Patterns detected
    patterns = summary.get("patterns_detected", [])
    if patterns:
        lines += ["## Patterns Detected", ""]
        for p in patterns:
            lines.append(f"- {p.get('summary', '')}")
        lines.append("")

    # Empty sprint
    if not features and not decisions and not blockers and not patterns:
        lines += ["*No activity recorded for this period.*", ""]

    return "\n".join(lines)


# ── CLI entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate sprint summary from memory.db")
    parser.add_argument("--project", "-p")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    parser.add_argument("--cross-project", action="store_true", help="Aggregate across all projects")
    parser.add_argument("--output", help="Write markdown to file")
    args = parser.parse_args()

    project = args.project or Path.cwd().name
    db_path = Path.home() / ".ai-memory" / "memory.db"

    summary = generate_sprint_summary(
        db_path=db_path,
        project=project,
        start_date=args.start,
        end_date=args.end,
        cross_project=args.cross_project,
    )
    md = export_sprint_md(summary)

    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"Written to {args.output}")
    else:
        print(md)
