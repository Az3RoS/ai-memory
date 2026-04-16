"""
scan_generic.py — Language-agnostic structure and config extraction.

Functions:
    scan_file(file_path, project) -> (entities, relationships)   [per-file, called by scan.py]
    scan_project_structure(project_dir, project) -> (entities, relationships)
    scan_config_files(project_dir, project) -> (entities, relationships)
    map_test_to_source(project_dir) -> list of (source_path, test_path)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# ── Layer detection ────────────────────────────────────────────────────────────

_KNOWN_LAYERS = {
    "routes": "route",
    "controllers": "controller",
    "services": "service",
    "models": "model",
    "schemas": "schema",
    "repositories": "repository",
    "middleware": "middleware",
    "utils": "utility",
    "helpers": "utility",
    "config": "config",
    "tests": "test",
    "__tests__": "test",
    "migrations": "migration",
    "seeds": "seed",
}

_CONFIG_FILES = {
    "package.json", "pyproject.toml", "setup.py", "requirements.txt",
    "Pipfile", "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
    "docker-compose.yml", "docker-compose.yaml", ".env.example",
    "tsconfig.json", "jest.config.js", "jest.config.ts",
    "webpack.config.js", "vite.config.ts", "vite.config.js",
}

_TEST_PREFIXES = ("test_", "spec_")
_TEST_SUFFIXES = ("_test", "_spec", ".test", ".spec")
_TEST_DIRS = {"tests", "__tests__", "test", "spec"}

_SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt", ".rb", ".php"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_test_file(path: Path) -> bool:
    stem = path.stem.lower()
    name = path.name.lower()
    if any(stem.startswith(p) for p in _TEST_PREFIXES):
        return True
    if any(stem.endswith(s) for s in _TEST_SUFFIXES):
        return True
    if any(part in _TEST_DIRS for part in path.parts):
        return True
    return False


def _layer_for_path(path: Path) -> str:
    for part in path.parts:
        if part.lower() in _KNOWN_LAYERS:
            return _KNOWN_LAYERS[part.lower()]
    return "module"


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


# ── Per-file entry (called by scan.py dispatch for unknown extensions) ─────────

def scan_file(file_path: Path, project: str) -> tuple[list[dict], list[dict]]:
    """
    Handle a single file that no language-specific scanner covers.
    Creates a module entity for the file and a config entity for config files.
    """
    file_path = Path(file_path)
    entities: list[dict] = []
    relationships: list[dict] = []

    if file_path.name in _CONFIG_FILES:
        ents, rels = _parse_config_file(file_path, project)
        entities.extend(ents)
        relationships.extend(rels)
    elif file_path.suffix.lower() in _SOURCE_EXTENSIONS:
        layer = _layer_for_path(file_path)
        is_test = _is_test_file(file_path)
        entities.append({
            "name": str(file_path),
            "type": "test" if is_test else layer,
            "file_path": str(file_path),
            "line_start": 1,
            "line_end": 1,
            "metadata": str({"layer": layer}),
        })

    return entities, relationships


# ── Project-level scan ─────────────────────────────────────────────────────────

def scan_project_structure(project_dir: Path, project: str) -> tuple[list[dict], list[dict]]:
    """
    Walk the project tree and create module-level entities.
    Detects layers, marks test files.
    Returns (entities, relationships).
    """
    project_dir = Path(project_dir)
    entities: list[dict] = []
    relationships: list[dict] = []

    _IGNORE = {".git", "node_modules", "__pycache__", ".venv", "venv",
               "dist", "build", ".eggs", ".mypy_cache", ".next"}

    for path in sorted(project_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _IGNORE for part in path.parts):
            continue
        if path.suffix.lower() not in _SOURCE_EXTENSIONS:
            continue

        rel = path.relative_to(project_dir)
        layer = _layer_for_path(rel)
        is_test = _is_test_file(rel)

        entities.append({
            "name": str(rel),
            "type": "test" if is_test else layer,
            "file_path": str(rel),
            "line_start": 1,
            "line_end": 1,
            "metadata": str({"layer": layer, "is_test": is_test}),
        })

    # test→source relationships
    source_map = {e["name"]: e for e in entities if e["type"] != "test"}
    for ent in entities:
        if ent["type"] != "test":
            continue
        # Try to find the source file this test covers
        test_path = Path(ent["file_path"])
        stem = test_path.stem
        for prefix in _TEST_PREFIXES:
            if stem.startswith(prefix):
                stem = stem[len(prefix):]
                break
        for suffix in _TEST_SUFFIXES:
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break

        for src_name in source_map:
            if Path(src_name).stem == stem:
                relationships.append({
                    "from": ent["name"],
                    "relation": "tested_by",
                    "to": src_name,
                })
                break

    return entities, relationships


def scan_config_files(project_dir: Path, project: str) -> tuple[list[dict], list[dict]]:
    """
    Parse package.json / requirements.txt / .env files / docker-compose.
    Returns (entities, relationships).
    """
    project_dir = Path(project_dir)
    entities: list[dict] = []
    relationships: list[dict] = []

    for cfg_name in _CONFIG_FILES:
        cfg_path = project_dir / cfg_name
        if not cfg_path.exists():
            continue
        ents, rels = _parse_config_file(cfg_path, project)
        entities.extend(ents)
        relationships.extend(rels)

    return entities, relationships


def _parse_config_file(cfg_path: Path, project: str) -> tuple[list[dict], list[dict]]:
    """Parse a single config file into entities."""
    entities: list[dict] = []
    relationships: list[dict] = []
    name = cfg_path.name.lower()
    content = _safe_read(cfg_path)

    metadata: dict = {"source": name}

    if name == "package.json":
        try:
            data = json.loads(content)
            metadata["deps"] = list(data.get("dependencies", {}).keys())[:20]
            metadata["dev_deps"] = list(data.get("devDependencies", {}).keys())[:10]
            metadata["scripts"] = list(data.get("scripts", {}).keys())
        except Exception:
            pass

    elif name in ("requirements.txt", "pipfile"):
        pkgs = [
            re.split(r"[>=<!~\[;]", line.strip())[0].strip()
            for line in content.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        metadata["packages"] = pkgs[:30]

    elif name in ("docker-compose.yml", "docker-compose.yaml"):
        services = re.findall(r"^\s{2}(\w[\w-]*):", content, re.MULTILINE)
        metadata["services"] = services[:20]

    elif name.startswith(".env"):
        keys = [
            line.split("=")[0].strip()
            for line in content.splitlines()
            if "=" in line and not line.startswith("#")
        ]
        metadata["env_keys"] = keys[:20]

    entities.append({
        "name": str(cfg_path),
        "type": "config",
        "file_path": str(cfg_path),
        "line_start": 1,
        "line_end": 1,
        "metadata": str(metadata),
    })

    return entities, relationships


# ── Test→source mapping ────────────────────────────────────────────────────────

def map_test_to_source(project_dir: Path) -> list[tuple[str, str]]:
    """
    Match test files to source files by naming convention.
    Returns list of (source_path, test_path) as relative strings.
    """
    project_dir = Path(project_dir)
    _IGNORE = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

    source_files: dict[str, Path] = {}
    test_files: list[Path] = []

    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        if any(p in _IGNORE for p in path.parts):
            continue
        if path.suffix.lower() not in _SOURCE_EXTENSIONS:
            continue
        if _is_test_file(path):
            test_files.append(path)
        else:
            source_files[path.stem.lower()] = path

    pairs: list[tuple[str, str]] = []
    for test_path in test_files:
        stem = test_path.stem.lower()
        for prefix in _TEST_PREFIXES:
            if stem.startswith(prefix):
                stem = stem[len(prefix):]
                break
        for suffix in ("_test", "_spec", ".test", ".spec"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break

        if stem in source_files:
            src = source_files[stem]
            pairs.append((
                str(src.relative_to(project_dir)),
                str(test_path.relative_to(project_dir)),
            ))

    return pairs
