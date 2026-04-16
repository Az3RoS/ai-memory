"""
scan_javascript.py — JavaScript/TypeScript scanner using regex patterns.

Functions:
    scan_file(file_path, project) -> (entities, relationships)
    extract_entity_from_match(match, pattern_name, file_path) -> entity dict
    detect_page_route(file_path) -> str | None
"""

from __future__ import annotations

import re
from pathlib import Path

# ── Regex patterns ─────────────────────────────────────────────────────────────

_PATTERNS: dict[str, re.Pattern] = {
    # React function component: function Foo(props) { return <JSX> }
    "function_component": re.compile(
        r"^(?:export\s+(?:default\s+)?)?function\s+([A-Z][A-Za-z0-9_]*)\s*\(",
        re.MULTILINE,
    ),
    # Arrow component: const Foo = (props) => (  or  = React.memo(...)
    "arrow_component": re.compile(
        r"^(?:export\s+(?:const|let)\s+)([A-Z][A-Za-z0-9_]*)\s*=\s*(?:React\.memo\()?(?:React\.forwardRef\()?\s*\(",
        re.MULTILINE,
    ),
    # Custom hook: function useXxx(
    "custom_hook": re.compile(
        r"^(?:export\s+(?:default\s+)?)?(?:function\s+|const\s+)(use[A-Z][A-Za-z0-9_]*)\s*[=(]",
        re.MULTILINE,
    ),
    # TypeScript interface
    "ts_interface": re.compile(
        r"^(?:export\s+)?interface\s+([A-Za-z][A-Za-z0-9_]*)\s*(?:extends\s+[^\{]+)?\{",
        re.MULTILINE,
    ),
    # TypeScript type alias
    "ts_type": re.compile(
        r"^(?:export\s+)?type\s+([A-Za-z][A-Za-z0-9_]*)\s*=",
        re.MULTILINE,
    ),
    # API call: fetch('/api/...') or axios.get('/api/...')
    "api_call": re.compile(
        r"(?:fetch|axios\.(?:get|post|put|patch|delete)|useSWR)\s*\(\s*['\"`]([^'\"` ]+)['\"`]",
        re.MULTILINE,
    ),
}

_IMPORT_PATTERN = re.compile(
    r"^(?:import\s+(?:[\w\s{},*]+\s+from\s+)?['\"`]([^'\"` ]+)['\"`]"
    r"|(?:const|let|var)\s+.*?=\s*require\(['\"`]([^'\"` ]+)['\"`]\))",
    re.MULTILINE,
)


# ── Page route detection ───────────────────────────────────────────────────────

def detect_page_route(file_path: Path) -> str | None:
    """
    Detect Next.js page route from file path.
    pages/about.tsx → /about
    app/dashboard/page.tsx → /dashboard
    """
    parts = file_path.parts
    try:
        # Next.js pages router
        if "pages" in parts:
            idx = parts.index("pages")
            route_parts = list(parts[idx + 1:])
            # Remove file extension from last part
            last = Path(route_parts[-1]).stem
            if last in ("index",):
                route_parts = route_parts[:-1]
            else:
                route_parts[-1] = last
            # Remove _app, _document, _error
            if route_parts and route_parts[-1].startswith("_"):
                return None
            return "/" + "/".join(route_parts) if route_parts else "/"

        # Next.js app router
        if "app" in parts:
            idx = parts.index("app")
            route_parts = list(parts[idx + 1:])
            last = Path(route_parts[-1]).stem
            if last == "page":
                route_parts = route_parts[:-1]
            else:
                return None  # Only page.tsx files define routes in app router
            # Strip dynamic segment brackets for display
            route_parts = [p for p in route_parts if not p.startswith("(")]
            return "/" + "/".join(route_parts) if route_parts else "/"
    except (ValueError, IndexError):
        pass
    return None


# ── Entity extractor ───────────────────────────────────────────────────────────

def extract_entity_from_match(match: re.Match, pattern_name: str, file_path: Path) -> dict:
    """Map a regex match to a structured entity dict."""
    name = match.group(1)
    line_num = match.string[: match.start()].count("\n") + 1

    type_map = {
        "function_component": "component",
        "arrow_component": "component",
        "custom_hook": "hook",
        "ts_interface": "interface",
        "ts_type": "type",
        "api_call": "api_call",
    }
    entity_type = type_map.get(pattern_name, "unknown")

    metadata: dict = {"raw_name": name}
    if entity_type == "api_call":
        metadata["endpoint"] = name
    if entity_type == "component":
        route = detect_page_route(file_path)
        if route:
            metadata["route"] = route

    return {
        "name": f"{file_path}::{name}",
        "type": entity_type,
        "file_path": str(file_path),
        "line_start": line_num,
        "line_end": line_num,
        "metadata": str(metadata),
    }


# ── Public entry ───────────────────────────────────────────────────────────────

def scan_file(file_path: Path, project: str) -> tuple[list[dict], list[dict]]:
    """
    Scan a JS/TS file with regex patterns.
    Returns (entities, relationships).
    """
    file_path = Path(file_path)
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [], []

    entities: list[dict] = []
    relationships: list[dict] = []
    from_module = str(file_path)

    # Extract imports/require
    for m in _IMPORT_PATTERN.finditer(content):
        module_path = m.group(1) or m.group(2) or ""
        if module_path:
            relationships.append({
                "from": from_module,
                "relation": "imports",
                "to": module_path,
            })

    # Extract entities from each pattern
    for pattern_name, pattern in _PATTERNS.items():
        for m in pattern.finditer(content):
            entity = extract_entity_from_match(m, pattern_name, file_path)
            entities.append(entity)

    return entities, relationships
