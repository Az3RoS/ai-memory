#!/usr/bin/env python3
"""
memory_slash.py — slash command handler for GitHub Copilot Chat.

Copilot Chat doesn't natively support custom slash commands, but you can wire
this script up via a VS Code task and invoke it from the terminal panel.

The recommended pattern is a keybinding that runs:
  python3 ~/.ai-memory-system/scripts/memory_slash.py "<your input>"

Supported commands:
  /memory <terms>    — deep search, returns ranked context block
  /memory            — recent entries
  /context           — show current CONTEXT.md
  /log <note>        — add note to today's log
  /decisions         — show decisions ledger
  /status            — project stats

Usage from terminal:
  python3 memory_slash.py "/memory asyncpg decisions"
  python3 memory_slash.py "/log decided to use JWT"
  python3 memory_slash.py "/decisions"
"""

import sys
import os
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(__file__))

from memory_config import Config
from memory_store import MemoryStore
from memory_query import fetch_for_copilot, query_memory, build_context_block
from memory_log import write_daily_log
from memory_sync import sync_to_repo


# ── Separator for visual clarity in terminal output ───────────────────────────
SEP = "\n" + "─" * 60 + "\n"


def handle(raw: str, cfg: Config):
    raw = raw.strip()

    # Strip leading slash if present
    if raw.startswith("/"):
        raw = raw[1:]

    parts = raw.split(None, 1)
    cmd   = parts[0].lower() if parts else "memory"
    args  = parts[1].strip() if len(parts) > 1 else ""

    project = cfg.detect_project()
    store   = MemoryStore(cfg.global_db_path())

    # ── /memory [terms] ───────────────────────────────────────────────────────
    if cmd == "memory":
        budget  = cfg.token_budget(project)
        result  = fetch_for_copilot(store, args, project=project, token_budget=budget)
        print(SEP)
        print(result)
        print(SEP)
        if args:
            print(f"[memory] searched: '{args}'  project: {project}")
        else:
            print(f"[memory] recent entries  project: {project}")

    # ── /context ──────────────────────────────────────────────────────────────
    elif cmd == "context":
        repo_dir = cfg.repo_memory_dir(project)
        if repo_dir and (repo_dir / "CONTEXT.md").exists():
            print(SEP)
            print((repo_dir / "CONTEXT.md").read_text())
            print(SEP)
        else:
            # Fall back to building it live
            entries = query_memory(store, "", project=project, limit=20)
            print(SEP)
            print(build_context_block(entries, token_budget=cfg.token_budget(project), project=project))
            print(SEP)

    # ── /log <note> ───────────────────────────────────────────────────────────
    elif cmd == "log":
        if not args:
            print("[memory] usage: /log <your note>")
            return
        store.add_entry(project, "note", args, tags=["note"])
        log_file = write_daily_log(store, project, cfg=cfg, extra_note=args)
        sync_to_repo(store, project, cfg)
        print(f"[memory] logged: \"{args}\"")
        print(f"[memory] log file: {log_file}")

    # ── /decisions ────────────────────────────────────────────────────────────
    elif cmd == "decisions":
        repo_dir = cfg.repo_memory_dir(project)
        if repo_dir and (repo_dir / "decisions.md").exists():
            print(SEP)
            print((repo_dir / "decisions.md").read_text())
            print(SEP)
        else:
            results = query_memory(store, "decision", project=project, limit=30)
            decisions = [r for r in results if r.get("entry_type") == "decision"
                         or "decision" in (r.get("tags") or "")]
            if not decisions:
                print("[memory] no decisions recorded yet")
            else:
                print(SEP)
                for d in decisions:
                    print(f"## {d['date'][:10]} — {d['summary']}")
                    if d.get("detail"):
                        print(f"   {d['detail']}")
                    print()
                print(SEP)

    # ── /status ───────────────────────────────────────────────────────────────
    elif cmd == "status":
        projects = cfg.list_projects()
        print(f"\nGlobal DB : {cfg.global_db_path()}")
        print(f"Projects  : {len(projects)}\n")
        for p in projects:
            count = store.entry_count(p["slug"])
            marker = " ◀ current" if p["slug"] == project else ""
            print(f"  {p['slug']:25s}  entries={count:4d}  repo={p.get('repo_path','?')}{marker}")
        print()

    else:
        print(f"[memory] unknown command: /{cmd}")
        print("[memory] available: /memory, /context, /log, /decisions, /status")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    raw = " ".join(sys.argv[1:])
    cfg = Config()
    handle(raw, cfg)


if __name__ == "__main__":
    main()
