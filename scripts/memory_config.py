"""
memory_config.py — configuration and project registry.

Global memory lives at ~/.ai-memory/
  memory.db          — SQLite + FTS5 database
  projects.json      — project registry
  logs/              — daily markdown logs (per project)
  entities/          — knowledge graph markdown (per project)

Per-repo memory lives at <repo>/.ai-memory/
  CONTEXT.md         — ambient inject file (Copilot reads this)
  decisions.md       — architecture decisions log
  index.json         — lightweight pointer to global entries
"""

import json
import os
from pathlib import Path
from typing import Optional


GLOBAL_DIR = Path.home() / ".ai-memory"


class Config:
    def __init__(self, global_dir: Optional[Path] = None):
        self.global_dir = Path(global_dir) if global_dir else GLOBAL_DIR
        self.global_dir.mkdir(parents=True, exist_ok=True)
        (self.global_dir / "logs").mkdir(exist_ok=True)
        (self.global_dir / "entities").mkdir(exist_ok=True)
        self._registry: Optional[list] = None

    # ── Paths ────────────────────────────────────────────────────────────────

    def global_db_path(self) -> Path:
        return self.global_dir / "memory.db"

    def projects_path(self) -> Path:
        return self.global_dir / "projects.json"

    def log_dir(self) -> Path:
        return self.global_dir / "logs"

    def entities_dir(self) -> Path:
        return self.global_dir / "entities"

    # ── Project registry ─────────────────────────────────────────────────────

    def _load_registry(self) -> list:
        if self._registry is None:
            p = self.projects_path()
            if p.exists():
                with open(p) as f:
                    self._registry = json.load(f)
            else:
                self._registry = []
        return self._registry

    def _save_registry(self):
        with open(self.projects_path(), "w") as f:
            json.dump(self._registry, f, indent=2)

    def list_projects(self) -> list:
        return self._load_registry()

    def get_project(self, slug: str) -> Optional[dict]:
        return next((p for p in self._load_registry() if p["slug"] == slug), None)

    def register_project(self, slug: str, repo_path: str, token_budget: int = 2000):
        registry = self._load_registry()
        existing = next((p for p in registry if p["slug"] == slug), None)
        if existing:
            existing["repo_path"] = repo_path
            existing["token_budget"] = token_budget
        else:
            registry.append({
                "slug": slug,
                "repo_path": repo_path,
                "token_budget": token_budget,
            })
        self._registry = registry
        self._save_registry()

    def token_budget(self, slug: str) -> int:
        proj = self.get_project(slug)
        return proj.get("token_budget", 2000) if proj else 2000

    # ── Auto-detect project from cwd ─────────────────────────────────────────

    def detect_project(self) -> str:
        """
        Walk up from cwd looking for .ai-memory/index.json which contains
        the project slug. Falls back to the repo root directory name.
        """
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            index = parent / ".ai-memory" / "index.json"
            if index.exists():
                try:
                    data = json.loads(index.read_text())
                    return data["slug"]
                except Exception:
                    pass
            # Also detect git root as a fallback
            if (parent / ".git").exists():
                slug = parent.name.lower().replace(" ", "-")
                return slug
        return "default"

    # ── Repo .ai-memory path ─────────────────────────────────────────────────

    def repo_memory_dir(self, project_slug: str) -> Optional[Path]:
        proj = self.get_project(project_slug)
        if proj and proj.get("repo_path"):
            d = Path(proj["repo_path"]) / ".ai-memory"
            d.mkdir(exist_ok=True)
            return d
        # Try detecting from cwd
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            if (parent / ".git").exists():
                d = parent / ".ai-memory"
                d.mkdir(exist_ok=True)
                return d
        return None
