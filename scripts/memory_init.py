"""
memory_init.py — initialise a new project in the memory system.

Creates:
  ~/.ai-memory/projects.json entry
  <repo>/.ai-memory/            directory
  <repo>/.ai-memory/index.json  slug pointer
  <repo>/.ai-memory/CONTEXT.md  empty placeholder
  <repo>/.ai-memory/decisions.md
  <repo>/.gitignore entry       (adds .ai-memory/*.local if not present)
  <repo>/.git/hooks/post-commit  git hook (non-destructive)
  <repo>/.git/hooks/pre-commit   git hook (non-destructive)
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from memory_config import Config


# ── Hook templates ────────────────────────────────────────────────────────────

POST_COMMIT_HOOK = """\
#!/bin/sh
# ai-memory post-commit hook — auto-ingests commit into memory
# Installed by: memory_cli.py init
set -e

MEMORY_CLI="{memory_cli}"
PROJECT="{project}"

# Ingest commit silently (failures don't block git)
python3 "$MEMORY_CLI" ingest --project "$PROJECT" || true
python3 "$MEMORY_CLI" log    --project "$PROJECT" || true
"""

PRE_COMMIT_HOOK = """\
#!/bin/sh
# ai-memory pre-commit hook — updates CONTEXT.md before each commit
# Installed by: memory_cli.py init
set -e

MEMORY_CLI="{memory_cli}"
PROJECT="{project}"

# Refresh CONTEXT.md so it's always committed with latest context
python3 "$MEMORY_CLI" sync --project "$PROJECT" || true

# Stage the updated files if they changed
if git diff --quiet .ai-memory/ 2>/dev/null; then
  :
else
  git add .ai-memory/CONTEXT.md .ai-memory/decisions.md .ai-memory/index.json 2>/dev/null || true
fi
"""

CONTEXT_PLACEHOLDER = """\
<!-- ai-memory: auto-generated — do not edit manually -->
<!-- Run: python3 scripts/memory_cli.py sync  to regenerate -->

## AI Memory Context

_No memory entries yet. Make your first commit to begin building context._
"""

DECISIONS_PLACEHOLDER = """\
# Architecture Decisions

_No decisions recorded yet._

<!-- Decisions are auto-extracted from commits containing:
     decided, chose, switched, migrated, replaced, adopted, deprecated, architecture, adr -->
"""


# ── Gitignore helper ──────────────────────────────────────────────────────────

def _patch_gitignore(repo_path: Path):
    gi = repo_path / ".gitignore"
    marker = "# ai-memory"
    block = f"\n{marker}\n.ai-memory/*.local\n"

    if gi.exists():
        content = gi.read_text(encoding="utf-8")
        if marker not in content:
            gi.write_text(content + block, encoding="utf-8")
    else:
        gi.write_text(block.strip() + "\n", encoding="utf-8")


# ── Hook installer ────────────────────────────────────────────────────────────

def _install_hook(hooks_dir: Path, name: str, content: str):
    hook_path = hooks_dir / name
    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8")
        if "ai-memory" in existing:
            return  # already installed
        # Append to existing hook
        separator = "\n\n# --- ai-memory ---\n"
        hook_path.write_text(existing.rstrip() + separator + content, encoding="utf-8")
    else:
        hook_path.write_text(content, encoding="utf-8")

    # Make executable
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# ── Public API ────────────────────────────────────────────────────────────────

def init_project(cfg: Config, slug: str, repo_path: str):
    repo = Path(repo_path).resolve()

    if not repo.exists():
        raise ValueError(f"Repo path does not exist: {repo}")

    # 1. Register in global config
    cfg.register_project(slug, str(repo), token_budget=1500)

    # 2. Create .ai-memory/ dir in repo
    mem_dir = repo / ".ai-memory"
    mem_dir.mkdir(exist_ok=True)

    # 3. Write index.json (slug pointer)
    index = {
        "slug":         slug,
        "repo_path":    str(repo),
        "global_db":    str(cfg.global_db_path()),
        "token_budget": 1500,
        "entry_count":  0,
        "last_sync":    None,
    }
    (mem_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")

    # 4. Write placeholder files
    ctx_file = mem_dir / "CONTEXT.md"
    if not ctx_file.exists():
        ctx_file.write_text(CONTEXT_PLACEHOLDER, encoding="utf-8")

    dec_file = mem_dir / "decisions.md"
    if not dec_file.exists():
        dec_file.write_text(DECISIONS_PLACEHOLDER, encoding="utf-8")

    # 5. Patch .gitignore
    _patch_gitignore(repo)

    # 6. Install git hooks
    hooks_dir = repo / ".git" / "hooks"
    memory_cli = str(Path(__file__).parent / "memory_cli.py")
    if hooks_dir.exists():
        _install_hook(
            hooks_dir, "post-commit",
            POST_COMMIT_HOOK.format(memory_cli=memory_cli, project=slug),
        )
        _install_hook(
            hooks_dir, "pre-commit",
            PRE_COMMIT_HOOK.format(memory_cli=memory_cli, project=slug),
        )
        # Install pre-push and post-merge if templates exist
        hooks_src = Path(__file__).parent.parent / "hooks"
        for hook_name in ("pre-push", "post-merge"):
            hook_src = hooks_src / hook_name
            if hook_src.exists():
                _install_hook(
                    hooks_dir, hook_name,
                    hook_src.read_text(encoding="utf-8").replace(
                        "{memory_cli}", memory_cli
                    ).replace("{project}", slug),
                )
    else:
        print(f"  [warn] .git/hooks not found at {hooks_dir} - hooks not installed")

    # 7. Copy skills directory and install to 01-sdlc
    skills_src = Path(__file__).parent.parent / "skills"
    if skills_src.exists():
        skills_dst = mem_dir / "skills"
        skills_dst.mkdir(exist_ok=True)
        for skill_file in skills_src.glob("*.md"):
            shutil.copy2(skill_file, skills_dst / skill_file.name)
        
        # Also install to docs/01-sdlc/
        sdlc_dst = mem_dir / "docs" / "01-sdlc"
        sdlc_dst.mkdir(parents=True, exist_ok=True)
        for skill_file in skills_src.glob("*.md"):
            shutil.copy2(skill_file, sdlc_dst / skill_file.name)
    else:
        print(f"  [warn] skills directory not found at {skills_src}")

    # 8. Generate IDE pointer files
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from pointers import generate_pointers
        template_path = Path(__file__).parent.parent / "templates" / "pointer.md.template"
        generate_pointers(repo, template_path=template_path, verbose=False)
    except Exception:
        pass  # pointers are optional at init time

    print("  [ok] global registry updated")
    print(f"  [ok] {mem_dir} created")
    print("  [ok] .gitignore patched")
    if hooks_dir.exists():
        print("  [ok] git hooks installed")
    print("  [ok] IDE pointer files generated")
    # This file is being deleted as it is obsolete.
