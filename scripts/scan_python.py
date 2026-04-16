"""
scan_python.py — Python-specific scanner using stdlib ast module.

Functions:
    scan_file(file_path, project) -> (entities, relationships)
    extract_class(node, file_path) -> entity dict
    extract_function(node, file_path) -> entity dict
    extract_imports(node, file_path) -> list of relationship dicts
    build_qualified_name(file_path, entity_name) -> string
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Optional

# Decorator patterns that indicate an HTTP endpoint
_ENDPOINT_DECORATORS = re.compile(
    r"^(app|router|blueprint|api)\.(get|post|put|patch|delete|head|options|route)$",
    re.IGNORECASE,
)
# Base class names that indicate a SQLAlchemy model
_MODEL_BASES = {"Base", "Model", "DeclarativeBase", "db.Model"}
# Base class names that indicate a Pydantic schema
_SCHEMA_BASES = {"BaseModel", "Schema"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def build_qualified_name(file_path: Path, entity_name: str) -> str:
    """Convert file path to module path and append entity name.

    e.g. src/services/auth.py + AuthService → src.services.auth.AuthService
    """
    parts = list(file_path.with_suffix("").parts)
    module = ".".join(parts)
    return f"{module}.{entity_name}" if entity_name else module


def _decorator_name(node: ast.expr) -> str:
    """Extract flat decorator name from AST node."""
    if isinstance(node, ast.Attribute):
        return f"{_decorator_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _first_line_docstring(node: ast.AST) -> str:
    """Return the first line of the docstring for a class/function node."""
    try:
        doc = ast.get_docstring(node)
        if doc:
            return doc.splitlines()[0][:200]
    except Exception:
        pass
    return ""


def _arg_sig(arg: ast.arg) -> str:
    name = arg.arg
    if arg.annotation:
        try:
            return f"{name}: {ast.unparse(arg.annotation)}"
        except Exception:
            pass
    return name


def _return_annotation(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    if node.returns:
        try:
            return ast.unparse(node.returns)
        except Exception:
            pass
    return ""


# ── Extractors ─────────────────────────────────────────────────────────────────

def extract_class(node: ast.ClassDef, file_path: Path) -> dict:
    """Extract class entity dict from an AST ClassDef node."""
    bases = [ast.unparse(b) for b in node.bases] if node.bases else []

    # Determine subtype
    base_set = set(bases)
    if base_set & _MODEL_BASES:
        subtype = "model"
    elif base_set & _SCHEMA_BASES:
        subtype = "schema"
    elif "TestCase" in base_set or "unittest.TestCase" in base_set:
        subtype = "test"
    elif "services" in file_path.parts or "service" in str(file_path).lower():
        subtype = "service"
    else:
        subtype = "class"

    decorators = [_decorator_name(d) for d in node.decorator_list]
    methods = [
        n.name for n in ast.walk(node)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.col_offset > node.col_offset
    ]

    # For models: extract Column() field names
    columns: list[str] = []
    if subtype == "model":
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        # Check if value is a Column() call
                        if isinstance(stmt.value, ast.Call):
                            func = stmt.value.func
                            func_name = ast.unparse(func) if func else ""
                            if "Column" in func_name or "mapped_column" in func_name:
                                columns.append(t.id)

    # For schemas: extract field annotations
    fields: list[str] = []
    if subtype == "schema":
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fields.append(stmt.target.id)

    return {
        "name": build_qualified_name(file_path, node.name),
        "type": subtype,
        "file_path": str(file_path),
        "line_start": node.lineno,
        "line_end": node.end_lineno or node.lineno,
        "metadata": str({
            "bases": bases,
            "decorators": decorators,
            "methods": methods,
            "columns": columns,
            "fields": fields,
            "docstring": _first_line_docstring(node),
        }),
    }


def extract_function(node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path) -> dict:
    """Extract function entity dict."""
    decorators = [_decorator_name(d) for d in node.decorator_list]
    is_endpoint = any(_ENDPOINT_DECORATORS.match(d) for d in decorators)

    # Build arg list (skip self/cls)
    args = node.args
    skip = {"self", "cls"}
    arg_parts = [_arg_sig(a) for a in args.args if a.arg not in skip]
    if args.vararg:
        arg_parts.append(f"*{args.vararg.arg}")
    arg_parts += [_arg_sig(a) for a in args.kwonlyargs]
    if args.kwarg:
        arg_parts.append(f"**{args.kwarg.arg}")
    sig = f"({'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}{node.name}({', '.join(arg_parts)}))"
    ret = _return_annotation(node)
    if ret:
        sig += f" -> {ret}"

    entity_type = "endpoint" if is_endpoint else "function"

    return {
        "name": build_qualified_name(file_path, node.name),
        "type": entity_type,
        "file_path": str(file_path),
        "line_start": node.lineno,
        "line_end": node.end_lineno or node.lineno,
        "metadata": str({
            "signature": sig,
            "decorators": decorators,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "return_type": ret,
            "docstring": _first_line_docstring(node),
        }),
    }


def extract_imports(tree: ast.Module, file_path: Path) -> list[dict]:
    """Extract import relationships from an AST module."""
    relationships: list[dict] = []
    from_module = build_qualified_name(file_path, "")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                relationships.append({
                    "from": from_module,
                    "relation": "imports",
                    "to": alias.name,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level and node.level > 0:
                # Relative import: resolve against file's package
                parts = list(file_path.parent.parts)
                levels_up = node.level
                base_parts = parts[: max(0, len(parts) - levels_up + 1)]
                if module:
                    base_parts.append(module)
                module = ".".join(base_parts)
            for alias in node.names:
                target = f"{module}.{alias.name}" if alias.name != "*" else module
                relationships.append({
                    "from": from_module,
                    "relation": "imports",
                    "to": target,
                })

    return relationships


# ── Public entry ───────────────────────────────────────────────────────────────

def scan_file(file_path: Path, project: str) -> tuple[list[dict], list[dict]]:
    """
    Parse a Python file with ast and extract entities + relationships.
    Returns (entities, relationships). Handles SyntaxError gracefully.
    """
    file_path = Path(file_path)
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [], []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return [], []

    entities: list[dict] = []
    relationships: list[dict] = []

    # Extract imports first
    relationships.extend(extract_imports(tree, file_path))

    # Walk top-level and nested definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            entities.append(extract_class(node, file_path))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            entities.append(extract_function(node, file_path))

    return entities, relationships
