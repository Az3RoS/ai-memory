#!/usr/bin/env python3
"""
ai-memory: unified CLI for the AI memory system.

Usage:
    memory_cli.py ingest   [--project <slug>] [--message <msg>]
    memory_cli.py query    <search_terms>     [--project <slug>] [--limit <n>] [--format context|json]
    memory_cli.py log      [--project <slug>] [--message <msg>]
    memory_cli.py sync     [--project <slug>]
    memory_cli.py context  [--project <slug>] [--tokens <budget>]
    memory_cli.py graph    [--project <slug>]
    memory_cli.py init     --project <slug>   --repo <path>
    memory_cli.py status
"""

import argparse
import sys
import os
import io

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf=8", errors="replace")

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


COMMANDS = {
    "ingest":  cmd_ingest,
    "query":   cmd_query,
    "log":     cmd_log,
    "sync":    cmd_sync,
    "context": cmd_context,
    "graph":   cmd_graph,
    "init":    cmd_init,
    "status":  cmd_status,
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
    parser.add_argument("--limit",   "-l", type=int, default=10)
    parser.add_argument("--tokens",  "-t", type=int, default=2000,
                        help="Max token budget for context output")
    parser.add_argument("--format",  "-f", choices=["context","json"], default="context")

    args = parser.parse_args()
    cfg  = Config()
    COMMANDS[args.command](args, cfg)


if __name__ == "__main__":
    main()
