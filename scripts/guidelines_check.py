"""
guidelines_check.py — Checks changed files against project guidelines.

Functions:
    check_missing_tests(changed_files, repo_dir) -> list of issue dicts
    check_wrong_layer_imports(changed_files, repo_dir) -> list of issue dicts
    check_hardcoded_values(changed_files, repo_dir) -> list of issue dicts
    check_logging_patterns(changed_files, repo_dir) -> list of issue dicts
    check_guidelines(project, changed_files, repo_dir) -> dict summary
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

# ── Layer import rules ─────────────────────────────────────────────────────────
# Key: layer directory name, Value: forbidden import patterns from other layers
_LAYER_RULES: dict[str, list[re.Pattern]] = {
    "routes": [
        re.compile(r"from\s+['\"]?.*models", re.MULTILINE),
        re.compile(r"import\s+.*models", re.MULTILINE),
    ],
    "controllers": [
        re.compile(r"from\s+['\"]?.*database", re.MULTILINE),
        re.compile(r"import\s+.*database", re.MULTILINE),
    ],
    "schemas": [
        re.compile(r"from\s+['\"]?.*services", re.MULTILINE),
    ],
}

# ── Hardcoded value patterns ───────────────────────────────────────────────────
_HARDCODED_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("hardcoded_secret", re.compile(
        r'(?:password|secret|api_key|token|passwd)\s*=\s*["\'][^"\']{4,}["\']',
        re.IGNORECASE | re.MULTILINE,
    )),
    ("hardcoded_url", re.compile(
        r'https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0):\d+',
        re.MULTILINE,
    )),
    ("hardcoded_ip", re.compile(
        r'(?<![.\d])(?:10|172|192)\.(?:\d{1,3}\.){2}\d{1,3}(?![.\d])',
        re.MULTILINE,
    )),
]

# ── Logging patterns ───────────────────────────────────────────────────────────
_PRINT_INSTEAD_OF_LOG = re.compile(
    r'^\s*print\s*\((?!.*#\s*noqa)',
    re.MULTILINE,
)
_BARE_EXCEPT = re.compile(r'except\s*:', re.MULTILINE)
_SWALLOWED_EXCEPTION = re.compile(r'except.*:\s*\n\s*pass', re.MULTILINE)

# Source file extensions that should have matching test files
_SOURCE_EXTENSIONS = {".py", ".ts", ".js", ".go", ".rs", ".java", ".kt"}
_TEST_INDICATORS = re.compile(r"(test|spec|__test__|_test\.|\.test\.)", re.IGNORECASE)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _read_file(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _is_source_file(path: Path) -> bool:
    return (
        path.suffix.lower() in _SOURCE_EXTENSIONS
        and not _TEST_INDICATORS.search(str(path))
    )


def _has_test_file(source_path: Path, repo_dir: Path) -> bool:
    """Check if a test file exists for the given source file."""
    stem = source_path.stem
    # Candidates: test_foo.py, foo_test.py, foo.test.ts, foo.spec.ts, tests/test_foo.py
    candidates = [
        source_path.parent / f"test_{stem}{source_path.suffix}",
        source_path.parent / f"{stem}_test{source_path.suffix}",
        source_path.parent / f"{stem}.test{source_path.suffix}",
        source_path.parent / f"{stem}.spec{source_path.suffix}",
        repo_dir / "tests" / f"test_{stem}{source_path.suffix}",
        repo_dir / "tests" / f"test_{stem}.py",
        repo_dir / "__tests__" / f"{stem}.test{source_path.suffix}",
        repo_dir / "__tests__" / f"{stem}.spec{source_path.suffix}",
    ]
    return any(c.exists() for c in candidates)


# ── Check functions ────────────────────────────────────────────────────────────

def check_missing_tests(changed_files: list[str], repo_dir: Path) -> list[dict]:
    """
    Check for source files that have no corresponding test file.
    Returns list of issue dicts: {file, rule, message}.
    """
    issues = []
    for rel_path in changed_files:
        path = repo_dir / rel_path
        if not path.exists():
            continue
        if not _is_source_file(path):
            continue
        if not _has_test_file(path, repo_dir):
            issues.append({
                "file": rel_path,
                "rule": "missing_test",
                "message": f"No test file found for {rel_path}",
                "severity": "warning",
            })
    return issues


def check_wrong_layer_imports(changed_files: list[str], repo_dir: Path) -> list[dict]:
    """
    Detect wrong-layer imports (e.g. model import in route layer).
    Returns list of issue dicts.
    """
    issues = []
    for rel_path in changed_files:
        path = repo_dir / rel_path
        content = _read_file(path)
        if content is None:
            continue

        # Determine which layer this file is in
        parts = Path(rel_path).parts
        for layer, forbidden_patterns in _LAYER_RULES.items():
            if layer not in parts:
                continue
            for pattern in forbidden_patterns:
                for m in pattern.finditer(content):
                    line_no = content[: m.start()].count("\n") + 1
                    issues.append({
                        "file": rel_path,
                        "rule": "wrong_layer_import",
                        "message": f"Layer violation in {rel_path}:{line_no} — {layer} layer importing from forbidden layer",
                        "severity": "error",
                        "line": line_no,
                    })
    return issues


def check_hardcoded_values(changed_files: list[str], repo_dir: Path) -> list[dict]:
    """
    Detect hardcoded secrets, URLs, and IP addresses.
    Returns list of issue dicts.
    """
    issues = []
    for rel_path in changed_files:
        path = repo_dir / rel_path
        # Skip test files, templates, and env examples for secret checks
        if re.search(r"(test|spec|example|\.env\.example|\.md)$", rel_path, re.IGNORECASE):
            continue
        content = _read_file(path)
        if content is None:
            continue

        for rule_name, pattern in _HARDCODED_PATTERNS:
            for m in pattern.finditer(content):
                line_no = content[: m.start()].count("\n") + 1
                issues.append({
                    "file": rel_path,
                    "rule": rule_name,
                    "message": f"{rule_name} detected in {rel_path}:{line_no}",
                    "severity": "error" if "secret" in rule_name else "warning",
                    "line": line_no,
                })
    return issues


def check_logging_patterns(changed_files: list[str], repo_dir: Path) -> list[dict]:
    """
    Check for bad logging patterns: print() instead of logger, bare except, swallowed exceptions.
    Returns list of issue dicts.
    """
    issues = []
    for rel_path in changed_files:
        path = repo_dir / rel_path
        if path.suffix.lower() not in {".py"}:
            continue
        if _TEST_INDICATORS.search(rel_path):
            continue
        content = _read_file(path)
        if content is None:
            continue

        for m in _PRINT_INSTEAD_OF_LOG.finditer(content):
            line_no = content[: m.start()].count("\n") + 1
            issues.append({
                "file": rel_path,
                "rule": "print_instead_of_logger",
                "message": f"Use logger instead of print() in {rel_path}:{line_no}",
                "severity": "warning",
                "line": line_no,
            })

        for m in _BARE_EXCEPT.finditer(content):
            line_no = content[: m.start()].count("\n") + 1
            issues.append({
                "file": rel_path,
                "rule": "bare_except",
                "message": f"Bare except clause in {rel_path}:{line_no} — catch specific exceptions",
                "severity": "warning",
                "line": line_no,
            })

        for m in _SWALLOWED_EXCEPTION.finditer(content):
            line_no = content[: m.start()].count("\n") + 1
            issues.append({
                "file": rel_path,
                "rule": "swallowed_exception",
                "message": f"Exception silently swallowed in {rel_path}:{line_no}",
                "severity": "warning",
                "line": line_no,
            })

    return issues


# ── Orchestrator ───────────────────────────────────────────────────────────────

def check_guidelines(project: str, changed_files: list[str], repo_dir: Path) -> dict:
    """
    Run all guideline checks against changed_files.
    Returns summary dict: {issues, counts_by_severity, counts_by_rule}.
    """
    repo_dir = Path(repo_dir)
    all_issues: list[dict] = []

    all_issues.extend(check_missing_tests(changed_files, repo_dir))
    all_issues.extend(check_wrong_layer_imports(changed_files, repo_dir))
    all_issues.extend(check_hardcoded_values(changed_files, repo_dir))
    all_issues.extend(check_logging_patterns(changed_files, repo_dir))

    counts_by_severity: dict[str, int] = {}
    counts_by_rule: dict[str, int] = {}
    for issue in all_issues:
        sev = issue.get("severity", "warning")
        counts_by_severity[sev] = counts_by_severity.get(sev, 0) + 1
        rule = issue.get("rule", "unknown")
        counts_by_rule[rule] = counts_by_rule.get(rule, 0) + 1

    return {
        "project": project,
        "issues": all_issues,
        "total": len(all_issues),
        "counts_by_severity": counts_by_severity,
        "counts_by_rule": counts_by_rule,
    }


# ── CLI entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import subprocess
    import json

    parser = argparse.ArgumentParser(description="Check guidelines against changed files")
    parser.add_argument("--project", "-p")
    parser.add_argument("--files", nargs="*")
    args = parser.parse_args()

    repo_dir = Path.cwd()
    project = args.project or repo_dir.name

    if args.files:
        changed = args.files
    else:
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            changed = [f for f in out.splitlines() if f.strip()]
        except Exception:
            changed = []

    result = check_guidelines(project, changed, repo_dir)
    print(json.dumps(result, indent=2))
