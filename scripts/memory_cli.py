#!/usr/bin/env python3
"""
ai-memory: unified CLI for the AI memory system.

Usage:
    memory_cli.py ingest     [--project <slug>] [--message <msg>]
    memory_cli.py query      <search_terms>     [--project <slug>] [--limit <n>] [--format context|json]
    memory_cli.py log        [--project <slug>] [--message <msg>]
    memory_cli.py sync       [--project <slug>]
    memory_cli.py context    [--project <slug>] [--tokens <budget>]
    memory_cli.py graph      [--project <slug>]
    memory_cli.py init       --project <slug>   --repo <path>
    memory_cli.py status
    memory_cli.py backfill   [--project <slug>] [--limit <n>] [--force]
    memory_cli.py review     [--project <slug>]
    memory_cli.py pr-context [--project <slug>]
"""

import argparse
import sys
import os

# Reconfigure stdout to UTF-8 so Unicode output works on all terminals
# (Windows cp1252 terminals would otherwise raise UnicodeEncodeError)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure package directory is on path when called from hooks
sys.path.insert(0, os.path.dirname(__file__))

from memory_store import MemoryStore
from memory_ingest import ingest_commit
from memory_query import query_memory, build_context_block
from memory_log import write_daily_log
from memory_sync import sync_to_repo
from memory_graph import update_graph
from memory_init import init_project
from memory_config import Config
from backfill import backfill as _backfill
from review import generate_review
from pr_context import generate_pr_description


def cmd_ingest(args, cfg):
    project = args.project or cfg.detect_project()
    msg = args.message or ""
    store = MemoryStore(cfg.global_db_path())
    ingest_commit(store, project, message=msg)
    sync_to_repo(store, project, cfg)
    print(f"[memory] ingested for project: {project}")


def cmd_query(args, cfg):
    project = args.project or cfg.detect_project()
    store = MemoryStore(cfg.global_db_path())
    results = query_memory(store, args.terms, project=project, limit=args.limit)
    if args.format == "json":
        import json
        print(json.dumps(results, indent=2, default=str))
    else:
        block = build_context_block(results, token_budget=args.tokens)
        print(block)


def cmd_log(args, cfg):
    project = args.project or cfg.detect_project()
    store = MemoryStore(cfg.global_db_path())
    write_daily_log(store, project, extra_note=args.message)
    sync_to_repo(store, project, cfg)
    print(f"[memory] daily log updated for project: {project}")


def cmd_sync(args, cfg):
    project = args.project or cfg.detect_project()
    store = MemoryStore(cfg.global_db_path())
    sync_to_repo(store, project, cfg)
    print(f"[memory] synced to repo for project: {project}")


def cmd_context(args, cfg):
    project = args.project or cfg.detect_project()
    store = MemoryStore(cfg.global_db_path())
    results = query_memory(store, "", project=project, limit=20)
    block = build_context_block(results, token_budget=args.tokens)
    print(block)


def cmd_graph(args, cfg):
    project = args.project or cfg.detect_project()
    store = MemoryStore(cfg.global_db_path())
    update_graph(store, project, cfg)
    print(f"[memory] knowledge graph updated for project: {project}")


def cmd_init(args, cfg):
    if not args.project:
        print("[memory] --project is required for init", file=sys.stderr)
        sys.exit(1)
    repo = args.repo or os.getcwd()
    init_project(cfg, args.project, repo)
    print(f"[memory] initialised project '{args.project}' at {repo}")


def cmd_status(args, cfg):
    store = MemoryStore(cfg.global_db_path())
    projects = cfg.list_projects()
    print(f"Global DB: {cfg.global_db_path()}")
    print(f"Projects registered: {len(projects)}")
    for p in projects:
        count = store.entry_count(p["slug"])
        print(f"  {p['slug']:20s}  entries={count:4d}  repo={p.get('repo_path','?')}")


def cmd_backfill(args, cfg):
    project = args.project or cfg.detect_project()
    store = MemoryStore(cfg.global_db_path())
    result = _backfill(
        store, project,
        limit=args.limit,
        force=getattr(args, "force", False),
        verbose=True,
    )
    if not result.get("already_done"):
        sync_to_repo(store, project, cfg)
        print(f"[memory] backfill complete for project: {project}")


def cmd_review(args, cfg):
    project = args.project or cfg.detect_project()
    store = MemoryStore(cfg.global_db_path())
    generate_review(store, project, cfg, verbose=True)


def cmd_pr_context(args, cfg):
    project = args.project or cfg.detect_project()
    generate_pr_description(project, cfg, verbose=True)


COMMANDS = {
    "ingest":      cmd_ingest,
    "query":       cmd_query,
    "log":         cmd_log,
    "sync":        cmd_sync,
    "context":     cmd_context,
    "graph":       cmd_graph,
    "init":        cmd_init,
    "status":      cmd_status,
    "backfill":    cmd_backfill,
    "review":      cmd_review,
    "pr-context":  cmd_pr_context,
}


def main():
    parser = argparse.ArgumentParser(
        description="AI memory system CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("command", choices=COMMANDS.keys())
    parser.add_argument("terms", nargs="?", default="", help="Search terms (query cmd)")
    parser.add_argument("--project", "-p", help="Project slug")
    parser.add_argument("--repo",    "-r", help="Repo path (init cmd)")
    parser.add_argument("--message", "-m", help="Commit message / note override")
    parser.add_argument("--limit",   "-l", type=int, default=200)
    parser.add_argument("--tokens",  "-t", type=int, default=2000,
                        help="Max token budget for context output")
    parser.add_argument("--format",  "-f", choices=["context","json"], default="context")
    parser.add_argument("--force",   action="store_true",
                        help="Force re-import (backfill cmd)")

    args = parser.parse_args()
    cfg  = Config()
    COMMANDS[args.command](args, cfg)


if __name__ == "__main__":
    main()
