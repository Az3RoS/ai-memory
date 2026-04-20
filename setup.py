#!/usr/bin/env python3
"""
setup.py — one-command installer for ai-memory.

Usage:
    python setup.py                  # Install in current repo
    python setup.py --rebuild        # Wipe local DB and reimport from git history
    python setup.py --repo /path     # Install in specific repo
    python setup.py --project slug   # Override project slug (default: repo dir name)
    python setup.py --reinstall-hooks   # Reinstall git hooks only (skip full setup)
    python setup.py --feature "New feature name"    # Create a feature template after setup
    python setup.py --fix "Bug fix description"     # Create a fix template after setup

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
from wiki_gen import generate_wiki
from feature_init import create_feature, create_fix
from utils import slugify, estimate_tokens, read_json, write_json
from memory_sync import sync_to_repo
from backfill import backfill
from pointers import generate_pointers
from memory_store import MemoryStore
from detect import detect_all
from memory_config import Config


# ── Helpers ────────────────────────────────────────────────────────────────────

def _banner(title: str):
    width = 50
    print()
    print("-" * width)
    print(f"  {title}")
    print("-" * width)


def _create_docs_structure(mem_dir: Path, verbose: bool = True):
    """Create full docs structure under .ai-memory/: 00-project, 01-sdlc, 02-feature/_templates."""
    docs_root = mem_dir / "docs"
    
    # Create 00-project stub files
    project_dir = docs_root / "00-project"
    project_dir.mkdir(parents=True, exist_ok=True)
    stubs = {
        "overview.md": "# Project Overview\n\nAdd project overview here.\n",
        "arch.md": "# Architecture\n\nAdd architecture notes here.\n",
        "conventions.md": "# Conventions\n\nAdd coding conventions here.\n",
        "design.md": "# Design Decisions\n\nAdd design decisions here.\n",
    }
    for filename, content in stubs.items():
        stub_file = project_dir / filename
        if not stub_file.exists():
            stub_file.write_text(content, encoding="utf-8")
    
    # Create 02-feature/_templates stub files
    templates_dir = docs_root / "02-feature" / "_templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    template_stubs = {
        "feature.md": "# Feature: [Name]\n\nFeature description here.\n",
        "plan.md": "# Plan\n\nImplementation plan here.\n",
        "scratch.md": "# Scratch\n\nWorking notes here.\n",
        "test.md": "# Tests\n\nTest cases here.\n",
        "dod.md": "# Definition of Done\n\nDone criteria here.\n",
    }
    for filename, content in template_stubs.items():
        stub_file = templates_dir / filename
        if not stub_file.exists():
            stub_file.write_text(content, encoding="utf-8")
    
    if verbose:
        print(f"  [ok] created docs structure: 00-project, 01-sdlc, 02-feature/_templates")


def _copy_skills(mem_dir: Path, verbose: bool = True):
    """Copy skills/ from the tool repo to .ai-memory/docs/01-sdlc/."""
    # Try multiple ways to find the skills directory
    candidates = [
        Path(__file__).resolve().parent / "skills",  # Primary: based on __file__
        Path.cwd() / "skills",  # Fallback: current working directory
        Path.cwd().parent / "ai-memory" / "skills",  # Fallback: parent directory
    ]
    
    src = None
    for candidate in candidates:
        if candidate.exists() and (candidate / "architect.md").exists():
            src = candidate
            break
    
    dst = mem_dir / "docs" / "01-sdlc"

    if src is None:
        if verbose:
            print(f"  [~] skills/ directory not found - checked: {candidates}")
        return

    dst.mkdir(parents=True, exist_ok=True)
    copied = 0
    for skill_file in src.glob("*.md"):
        target = dst / skill_file.name
        shutil.copy2(skill_file, target)
        copied += 1

    if verbose and copied > 0:
        print(f"  [ok] copied {copied} skill files to .ai-memory/docs/01-sdlc/")


def _reinstall_hooks(repo_root: Path, project: str, verbose: bool = True, force: bool = False):
    """Install or update git hooks without touching .ai-memory/ content."""
    from memory_init import _install_hook, POST_COMMIT_HOOK, PRE_COMMIT_HOOK
    hooks_dir = repo_root / ".git" / "hooks"
    if not hooks_dir.exists():
        if verbose:
            print("  [~] .git/hooks not found - skipping hook install")
        return

    # Install post-commit and pre-commit with template-based formatting
    _install_hook(hooks_dir, "post-commit",
                  POST_COMMIT_HOOK.format(project=project), force=force)
    _install_hook(hooks_dir, "pre-commit",
                  PRE_COMMIT_HOOK.format(project=project), force=force)

    # Install pre-push and post-merge hooks from hooks/ directory
    hooks_src = Path(__file__).parent / "hooks"
    for hook_name in ("pre-push", "post-merge"):
        hook_src = hooks_src / hook_name
        if hook_src.exists():
            _install_hook(
                hooks_dir,
                hook_name,
                hook_src.read_text(encoding="utf-8").replace(
                    "{project}", project
                ),
                force=force,
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
    parser.add_argument("--feature", help="Create a new feature template after setup")
    parser.add_argument("--fix", help="Create a new fix template after setup")
    parser.add_argument("--pointers", nargs="+", metavar="NAME",
                        help="Only generate pointer files matching these names (e.g. copilot claude cursor)")
    parser.add_argument("--rebuild", action="store_true",
                        help="Wipe local memory.db entries for this project and reimport")
    parser.add_argument("--reinstall-hooks", action="store_true",
                        help="Reinstall git hooks only (skip full setup)")
    parser.add_argument("--quiet",   action="store_true", help="Suppress output")
    args = parser.parse_args()

    verbose = not args.quiet
    repo_root = Path(args.repo).resolve() if args.repo else Path.cwd()
    project = args.project or _slug_from_path(repo_root)

    # ── Fast path: reinstall hooks only ────────────────────────────────────────
    if args.reinstall_hooks:
        if verbose:
            _banner("Reinstalling git hooks")
            print(f"  Repo:    {repo_root}")
            print(f"  Project: {project}")
            print()
        _reinstall_hooks(repo_root, project, verbose=verbose, force=True)
        if verbose:
            print()
        return

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
    written = generate_pointers(repo_root, template_path=template_path, verbose=verbose, only=args.pointers)

    # ── Step 4: Create docs structure and copy skills ────────────────────
    if verbose:
        print()
        print(f"  [4/6] Creating docs structure and installing skills...")

    _create_docs_structure(mem_dir, verbose=verbose)
    _copy_skills(mem_dir, verbose=verbose)

    # ── Step 5: Backfill git history ──────────────────────────────────────────
    db_path = Path.home() / ".ai-memory" / "memory.db"
    store = MemoryStore(db_path)
    db = DBMemory(db_path)  # Keep for backfill compatibility

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

    cfg = Config()
    sync_to_repo(store, project, cfg)

    if verbose:
        print("  [ok] .ai-memory/CONTEXT.md generated")

    # ── Step 7: Generate wiki structure ──────────────────────────────────────
    if verbose:
        print()
        print(f"  [7/7] Generating .ai-wiki structure...")

    wiki_db_path = Path.home() / ".ai-memory" / "wiki" / f"{project}.db"
    wiki_db_path.parent.mkdir(parents=True, exist_ok=True)
    generate_wiki(project, repo_root, wiki_db_path)

    if verbose:
        print("  [ok] .ai-wiki/ structure generated")

    feature_dir = None
    fix_dir = None
    if args.feature or args.fix:
        context_block = ""
        ctx_file = mem_dir / "CONTEXT.md"
        if ctx_file.exists():
            lines = ctx_file.read_text(encoding="utf-8").splitlines()
            context_block = "\n".join(lines[:20])

    if args.feature:
        feature_dir = create_feature(mem_dir, args.feature, context_block=context_block)
        if verbose:
            print(f"  [ok] feature template created at {feature_dir}")

    if args.fix:
        fix_dir = create_fix(mem_dir, args.fix, context_block=context_block)
        if verbose:
            print(f"  [ok] fix template created at {fix_dir}")

    # ── Summary ───────────────────────────────────────────────────────────────
    if verbose:
        _banner("Setup complete")
        print(f"  Project '{project}' is ready.")
        print()
        print("  [ok] .ai-memory/ initialised")
        print(f"  [ok] {len(written)} IDE pointer files generated")
        print("  [ok] Skills installed at docs/01-sdlc/")
        print("  [ok] .ai-wiki/ structure initialised")
        if feature_dir:
            print(f"  [ok] feature template created at {feature_dir}")
        if fix_dir:
            print(f"  [ok] fix template created at {fix_dir}")
        if result.get("commits_imported", 0) > 0:
            print(f"  [ok] {result['commits_imported']} commits imported, "
                  f"{result['decisions_found']} decisions found")
        print()
        print("  What to do next:")
        print("  1. Commit .ai-memory/ to share context with your team")
        print("     git add .ai-memory/ CLAUDE.md .cursorrules AGENTS.md")
        print("     git commit -m 'chore: add ai-memory context'")
        print("  2. Optional: commit .ai-wiki/ if you want to share documentation")
        print("     git add .ai-wiki/")
        print("  3. Make a commit - hooks will auto-update CONTEXT.md")
        print("  4. Open your AI IDE - it will read .ai-memory/CONTEXT.md")
        print("  5. Optional: Open .bashrc in your profile and add an alias for the memory CLI:")
        print("     alias mem='path/to/python /path/to/ai-memory/scripts/memory_cli.py'")
        print("     Then you can run commands like:")
        print("     mem feature 'New feature name'")
        print("  6. Create a new feature with project:")
        print("     python scripts/memory_cli.py init --project 'Project name'")
        print("  7. Create a new feature with context:")
        print("     python scripts/memory_cli.py feature 'Feature name'")
        print("  8. Create a bug fix with context:")
        print("     python scripts/memory_cli.py fix 'Bug description'")
        print("  9. Query memory (search project history):")
        print("     python scripts/memory_cli.py query 'search term'")
        print(" 10. Reinstall hooks (if they break):")
        print("     python setup.py --reinstall-hooks")
        print()


if __name__ == "__main__":
    main()
