"""
detect.py — auto-detect stack, IDE presence, and monorepo structure.

Used by setup.py and pointers.py. No external dependencies.
Returns structured information about the project environment.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


# ── Stack detection ────────────────────────────────────────────────────────────

STACK_SIGNALS: list[tuple[str, list[str]]] = [
    # (stack_name, [file_indicators])
    ("python",     ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile", "*.py"]),
    ("typescript", ["tsconfig.json", "*.ts", "*.tsx"]),
    ("javascript", ["package.json", "*.js", "*.jsx"]),
    ("go",         ["go.mod", "go.sum", "*.go"]),
    ("rust",       ["Cargo.toml", "Cargo.lock", "*.rs"]),
    ("java",       ["pom.xml", "build.gradle", "*.java"]),
    ("kotlin",     ["build.gradle.kts", "*.kt"]),
    ("ruby",       ["Gemfile", "*.rb"]),
    ("php",        ["composer.json", "*.php"]),
    ("csharp",     ["*.csproj", "*.sln", "*.cs"]),
    ("cpp",        ["CMakeLists.txt", "*.cpp", "*.hpp", "*.cc"]),
    ("c",          ["Makefile", "*.c", "*.h"]),
]

FRAMEWORK_SIGNALS: dict[str, list[str]] = {
    "fastapi":     ["fastapi", "uvicorn"],
    "django":      ["django", "manage.py"],
    "flask":       ["flask"],
    "nextjs":      ["next.config", "next.config.js", "next.config.ts"],
    "react":       ["react-dom", "react-scripts"],
    "vue":         ["vue.config.js", "@vue"],
    "sqlalchemy":  ["sqlalchemy", "alembic"],
    "prisma":      ["prisma/schema.prisma"],
    "pytest":      ["pytest.ini", "conftest.py"],
    "jest":        ["jest.config"],
}


def _file_exists_glob(root: Path, pattern: str) -> bool:
    """Check if any file matching pattern exists under root (non-recursive for speed)."""
    if "*" in pattern:
        ext = pattern.lstrip("*")
        return any(True for _ in root.glob(f"**/*{ext}") if not any(
            p in str(_) for p in ("node_modules", ".venv", "venv", "__pycache__", ".git")
        ))
    return (root / pattern).exists()


def detect_stack(root: Path) -> dict:
    """
    Return {
        "languages": ["python", "typescript", ...],
        "primary":   "python",
        "frameworks": ["fastapi", "sqlalchemy", ...],
        "package_managers": ["pip", "npm", ...],
    }
    """
    languages = []
    for lang, signals in STACK_SIGNALS:
        if any(_file_exists_glob(root, s) for s in signals):
            languages.append(lang)

    # Detect frameworks from config file content
    frameworks = []
    for fw, signals in FRAMEWORK_SIGNALS.items():
        for sig in signals:
            if _file_exists_glob(root, sig):
                frameworks.append(fw)
                break
        else:
            # Also check package.json / pyproject.toml content
            for cfg_file in ["package.json", "pyproject.toml", "requirements.txt"]:
                cfg_path = root / cfg_file
                if cfg_path.exists():
                    try:
                        content = cfg_path.read_text(encoding="utf-8", errors="ignore").lower()
                        if any(s in content for s in signals):
                            frameworks.append(fw)
                            break
                    except OSError:
                        pass

    # Package managers
    package_managers = []
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        package_managers.append("pip")
    if (root / "Pipfile").exists():
        package_managers.append("pipenv")
    if (root / "package.json").exists():
        package_managers.append("npm")
    if (root / "yarn.lock").exists():
        package_managers.append("yarn")
    if (root / "pnpm-lock.yaml").exists():
        package_managers.append("pnpm")
    if (root / "go.mod").exists():
        package_managers.append("go")
    if (root / "Cargo.toml").exists():
        package_managers.append("cargo")

    # Primary language: first detected (order matters in STACK_SIGNALS)
    primary = languages[0] if languages else "unknown"

    return {
        "languages": languages,
        "primary": primary,
        "frameworks": list(dict.fromkeys(frameworks)),  # dedup preserving order
        "package_managers": package_managers,
    }


# ── IDE detection ──────────────────────────────────────────────────────────────

IDE_SIGNALS: list[tuple[str, list[str]]] = [
    ("vscode",    [".vscode/settings.json", ".vscode/"]),
    ("cursor",    [".cursor/", ".cursorrules"]),
    ("claude",    [".claude/", "CLAUDE.md"]),
    ("jetbrains", [".idea/"]),
    ("vim",       [".vim/", ".vimrc"]),
    ("emacs",     [".emacs.d/", ".emacs"]),
    ("windsurf",  [".windsurfrules"]),
]


def detect_ides(root: Path) -> list[str]:
    """Return list of detected IDE names (e.g. ['vscode', 'claude'])."""
    found = []
    for ide, signals in IDE_SIGNALS:
        for sig in signals:
            p = root / sig
            if p.exists():
                found.append(ide)
                break
    return found


# ── Monorepo detection ─────────────────────────────────────────────────────────

def detect_monorepo(root: Path) -> dict:
    """
    Return {
        "is_monorepo": bool,
        "services": [relative_path_strings],
        "type": "npm_workspaces" | "pnpm_workspaces" | "gradle_multi" | "python_multi" | None
    }
    """
    services = []
    mono_type = None

    # npm/pnpm workspaces
    pkg = root / "package.json"
    if pkg.exists():
        try:
            import json
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if "workspaces" in data:
                mono_type = "npm_workspaces"
                workspaces = data["workspaces"]
                if isinstance(workspaces, list):
                    for ws in workspaces:
                        services.extend(str(p.parent) for p in root.glob(ws) if p.is_dir())
        except Exception:
            pass

    # Multiple pyproject.toml / setup.py at depth 2 (Python monorepo)
    if not mono_type:
        py_configs = [
            p for p in root.glob("*/pyproject.toml")
            if not any(skip in str(p) for skip in (".venv", "venv", "__pycache__"))
        ]
        if len(py_configs) >= 2:
            mono_type = "python_multi"
            services = [str(p.parent.relative_to(root)) for p in py_configs]

    # Gradle multi-project
    if not mono_type and (root / "settings.gradle").exists():
        try:
            content = (root / "settings.gradle").read_text(encoding="utf-8", errors="ignore")
            if "include" in content:
                mono_type = "gradle_multi"
        except OSError:
            pass

    is_monorepo = mono_type is not None or len(services) >= 2
    return {
        "is_monorepo": is_monorepo,
        "services": services[:20],  # cap at 20
        "type": mono_type,
    }


# ── Git info ───────────────────────────────────────────────────────────────────

def _git(cmd: list[str], cwd: Optional[Path] = None) -> str:
    try:
        return subprocess.check_output(
            ["git"] + cmd,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=str(cwd) if cwd else None,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def detect_git(root: Path) -> dict:
    """Return {root, branch, commit_count, has_history}."""
    git_root = _git(["rev-parse", "--show-toplevel"], cwd=root)
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    count_str = _git(["rev-list", "--count", "HEAD"], cwd=root)
    commit_count = int(count_str) if count_str.isdigit() else 0
    return {
        "root": git_root or str(root),
        "branch": branch or "unknown",
        "commit_count": commit_count,
        "has_history": commit_count > 0,
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_all(root: Optional[Path] = None) -> dict:
    """
    Run all detections and return a combined dict:
    {
        "stack":     {languages, primary, frameworks, package_managers},
        "ides":      [list of detected IDE names],
        "monorepo":  {is_monorepo, services, type},
        "git":       {root, branch, commit_count, has_history},
    }
    """
    root = Path(root) if root else Path.cwd()
    return {
        "stack":    detect_stack(root),
        "ides":     detect_ides(root),
        "monorepo": detect_monorepo(root),
        "git":      detect_git(root),
    }


if __name__ == "__main__":
    import json
    result = detect_all()
    print(json.dumps(result, indent=2))
