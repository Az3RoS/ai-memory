#!/usr/bin/env python3
"""
setup.py — one-command installer for ai-memory.

Usage:
    python setup.py                  # Install in current repo
    python setup.py --rebuild        # Wipe local DB and reimport from git history
    python setup.py --repo /path     # Install in specific repo
    python setup.py --project slug   # Override project slug (default: repo dir name)

What it does:
  1. Detects stack, IDEs, monorepo structure
  2. Initialises .ai-memory/ (or updates hooks if already exists)
  3. Generates all IDE pointer files (CLAUDE.md, .cursorrules, etc.)
  4. Copies skills/ directory to .ai-memory/skills/
  5. Backfills git history (last 200 commits)
  6. Generates initial CONTEXT.md
  7. Prints a summary of everything created

No external dependencies. Python stdlib only.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

# Reconfigure stdout to UTF-8 so Unicode output works on all terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Allow importing scripts from the same directory as setup.py
SCRIPT_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

# Import new modules
from db_memory import DBMemory
from db_wiki import DBWiki
from utils import slugify, estimate_tokens, read_json, write_json
from sync import sync_to_repo
from backfill import backfill
from pointers import generate_pointers
from detect import detect_all


# ── Helpers ────────────────────────────────────────────────────────────────────

def _banner(title: str):
    width = 50
    print()
    print("-" * width)
    print(f"  {title}")
    print("-" * width)


def _copy_skills(repo_root: Path, verbose: bool = True):
    """Copy skills/ from the tool repo to <repo>/docs/01-sdlc/."""
    # Use absolute path from this file's location
    tool_root = Path(__file__).resolve().parent
    src = tool_root / "skills"
    dst = repo_root / "docs" / "01-sdlc"

    if not src.exists():
        if verbose:
            print(f"  [~] skills/ directory not found at {src} - skipping")
        return

    dst.mkdir(parents=True, exist_ok=True)
    copied = 0
    for skill_file in src.glob("*.md"):
        target = dst / skill_file.name
        shutil.copy2(skill_file, target)
        copied += 1

    if verbose and copied > 0:
        print(f"  [ok] copied {copied} skill files to docs/01-sdlc/")


def _reinstall_hooks(repo_root: Path, project: str, verbose: bool = True):
    """Install or update git hooks without touching .ai-memory/ content."""
    from memory_init import _install_hook, POST_COMMIT_HOOK, PRE_COMMIT_HOOK
    hooks_dir = repo_root / ".git" / "hooks"
    if not hooks_dir.exists():
        if verbose:
            print("  [~] .git/hooks not found - skipping hook install")
        return

    memory_cli = str(SCRIPT_DIR / "memory_cli.py")
    _install_hook(hooks_dir, "post-commit",
                  POST_COMMIT_HOOK.format(memory_cli=memory_cli, project=project))
    _install_hook(hooks_dir, "pre-commit",
                  PRE_COMMIT_HOOK.format(memory_cli=memory_cli, project=project))

    # Install pre-push and post-merge hooks from hooks/ directory
    hooks_src = Path(__file__).parent / "hooks"
    for hook_name in ("pre-push", "post-merge"):
        hook_src = hooks_src / hook_name
        if hook_src.exists():
            _install_hook(
                hooks_dir,
                hook_name,
                hook_src.read_text(encoding="utf-8").replace(
                    "{memory_cli}", memory_cli
                ).replace(
                    "{project}", project
                ),
            )

    if verbose:
        print("  [ok] git hooks installed (pre-commit, post-commit, pre-push, post-merge)")


def _slug_from_path(path: Path) -> str:
    return path.name.lower().replace(" ", "-").replace("_", "-")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Install ai-memory in a git repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--repo",    "-r", help="Path to target repo (default: cwd)")
    parser.add_argument("--project", "-p", help="Project slug (default: repo dir name)")
    parser.add_argument("--rebuild", action="store_true",
                        help="Wipe local memory.db entries for this project and reimport")
    parser.add_argument("--quiet",   action="store_true", help="Suppress output")
    args = parser.parse_args()

    verbose = not args.quiet
    repo_root = Path(args.repo).resolve() if args.repo else Path.cwd()
    project = args.project or _slug_from_path(repo_root)

    if verbose:
        _banner("ai-memory setup")
        print(f"  Repo:    {repo_root}")
        print(f"  Project: {project}")

    # ── Step 1: Detect environment ─────────────────────────────────────────────
    if verbose:
        print()
        print("  [1/6] Detecting environment...")

    env = detect_all(repo_root)
    stack = env["stack"]
    ides  = env["ides"]
    git   = env["git"]
    mono  = env["monorepo"]

    if verbose:
        lang_str = ", ".join(stack["languages"]) or "unknown"
        fw_str   = ", ".join(stack["frameworks"][:4]) or "none detected"
        ide_str  = ", ".join(ides) if ides else "none detected"
        print(f"    Stack:    {lang_str}")
        print(f"    Frameworks: {fw_str}")
        print(f"    IDEs:     {ide_str}")
        print(f"    Commits:  {git['commit_count']}")
        if mono["is_monorepo"]:
            print(f"    Monorepo: yes ({mono['type']})")

    # ── Step 2: Init or update .ai-memory/ ────────────────────────────────────

    # Use new DB and utility classes
    mem_dir = repo_root / ".ai-memory"
    already_exists = mem_dir.exists() and (mem_dir / "index.json").exists()

    if verbose:
        print()
        if already_exists:
            print("  [2/6] Existing project detected - updating hooks...")
        else:
            print("  [2/6] Initialising .ai-memory/...")

    # For now, just ensure .ai-memory exists
    mem_dir.mkdir(exist_ok=True)
    # TODO: Replace with new project registry logic if needed
    _reinstall_hooks(repo_root, project, verbose=verbose)

    # ── Step 3: Generate IDE pointer files ────────────────────────────────────
    if verbose:
        print()
        print(f"  [3/6] Generating IDE pointer files...")

    template_path = Path(__file__).parent / "templates" / "pointer.md.template"
    written = generate_pointers(repo_root, template_path=template_path, verbose=verbose)

    # ── Step 4: Copy skills ───────────────────────────────────────────────────
    if verbose:
        print()
        print(f"  [4/6] Installing skill files...")

    _copy_skills(repo_root, verbose=verbose)

    # ── Step 5: Backfill git history ──────────────────────────────────────────
    db_path = Path.home() / ".ai-memory" / "memory.db"
    db = DBMemory(db_path)

    if verbose:
        print()
        print(f"  [5/6] Importing git history...")

    if git["has_history"]:
        result = backfill(
            db, project,
            limit=200,
            force=args.rebuild,
            verbose=verbose,
        )
    else:
        if verbose:
            print("  [~] no commits found - skipping backfill")
        result = {"commits_imported": 0, "decisions_found": 0, "already_done": False}

    # ── Step 6: Generate CONTEXT.md ───────────────────────────────────────────
    if verbose:
        print()
        print(f"  [6/6] Generating CONTEXT.md...")

    sync_to_repo(db, project, mem_dir)

    if verbose:
        print("  [ok] .ai-memory/CONTEXT.md generated")

    # ── Summary ───────────────────────────────────────────────────────────────
    if verbose:
        _banner("Setup complete")
        print(f"  Project '{project}' is ready.")
        print()
        print("  [ok] .ai-memory/ initialised")
        print(f"  [ok] {len(written)} IDE pointer files generated")
        print("  [ok] Skills installed at docs/01-sdlc/")
        if result.get("commits_imported", 0) > 0:
            print(f"  [ok] {result['commits_imported']} commits imported, "
                  f"{result['decisions_found']} decisions found")
        print()
        print("  What to do next:")
        print("  1. Commit .ai-memory/ to share context with your team")
        print("     git add .ai-memory/ CLAUDE.md .cursorrules AGENTS.md")
        print("     git commit -m 'chore: add ai-memory context'")
        print("  2. Make a commit - hooks will auto-update CONTEXT.md")
        print("  3. Open your AI IDE - it will read .ai-memory/CONTEXT.md")
        print()


if __name__ == "__main__":
    main()
