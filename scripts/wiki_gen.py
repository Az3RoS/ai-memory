"""
wiki_gen.py — Generates markdown wiki pages from wiki.db data.
"""
from pathlib import Path
from db_wiki import DBWiki

def _read_template(template_name: str) -> str:
    """Read a wiki template file."""
    template_path = Path(__file__).parent.parent / "templates" / f"wiki-{template_name}.md.template"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return f"# {template_name.replace('-', ' ').title()}\n\nTo be documented.\n"

def generate_all(conn, project: str, wiki_dir: Path) -> list[str]:
    """
    Entry point called by scan.py after scanning.
    conn  — open sqlite3 connection to wiki.db
    Returns list of written file paths.
    """
    wiki_dir = Path(wiki_dir)
    wiki_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []

    page_map = {
        "INDEX.md":                    "index",
        "ARCHITECTURE.md":             "architecture",
        "api/endpoints.md":            "endpoints",
        "models/overview.md":          "models",
        "services/overview.md":        "services",
        "database/tables.md":          "database",
        "components/overview.md":      "components",
        "tests/coverage-map.md":       "coverage",
    }

    for rel_path, template_name in page_map.items():
        out_path = wiki_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = _render_page(conn, project, template_name)
        out_path.write_text(content, encoding="utf-8")
        written.append(str(out_path))

    return written


def _render_page(conn, project: str, page: str) -> str:
    """Query wiki.db for relevant entities and render a wiki page."""
    template = _read_template(page)

    try:
        cur = conn.cursor()
        if page == "index":
            cur.execute(
                "SELECT entity_type, COUNT(*) as cnt FROM entities WHERE project=? GROUP BY entity_type",
                (project,),
            )
            rows = cur.fetchall()
            stats = "\n".join(f"- **{r[0]}**: {r[1]}" for r in rows) or "_No entities scanned yet._"
            return f"# Wiki Index — {project}\n\n## Entity Summary\n\n{stats}\n\n{template}"

        elif page == "architecture":
            cur.execute(
                "SELECT DISTINCT file_path FROM entities WHERE project=? ORDER BY file_path",
                (project,),
            )
            files = [r[0] for r in cur.fetchall() if r[0]]
            listing = "\n".join(f"- `{f}`" for f in files[:50]) or "_No files scanned yet._"
            return f"# Architecture — {project}\n\n## Scanned Files\n\n{listing}\n\n{template}"

        elif page == "endpoints":
            cur.execute(
                "SELECT entity, file_path, metadata FROM entities WHERE project=? AND entity_type='endpoint'",
                (project,),
            )
            rows = cur.fetchall()
            lines = [f"- `{r[0]}` — `{r[1]}`" for r in rows] or ["_No endpoints found._"]
            return f"# API Endpoints — {project}\n\n" + "\n".join(lines) + f"\n\n{template}"

        elif page == "models":
            cur.execute(
                "SELECT entity, file_path FROM entities WHERE project=? AND entity_type='model'",
                (project,),
            )
            rows = cur.fetchall()
            lines = [f"- `{r[0]}` — `{r[1]}`" for r in rows] or ["_No models found._"]
            return f"# Models — {project}\n\n" + "\n".join(lines) + f"\n\n{template}"

        elif page == "services":
            cur.execute(
                "SELECT entity, file_path FROM entities WHERE project=? AND entity_type='service'",
                (project,),
            )
            rows = cur.fetchall()
            lines = [f"- `{r[0]}` — `{r[1]}`" for r in rows] or ["_No services found._"]
            return f"# Services — {project}\n\n" + "\n".join(lines) + f"\n\n{template}"

        elif page == "database":
            cur.execute(
                "SELECT entity, file_path FROM entities WHERE project=? AND entity_type='table'",
                (project,),
            )
            rows = cur.fetchall()
            lines = [f"- `{r[0]}` — `{r[1]}`" for r in rows] or ["_No tables found._"]
            return f"# Database — {project}\n\n" + "\n".join(lines) + f"\n\n{template}"

        elif page == "components":
            cur.execute(
                "SELECT entity, file_path FROM entities WHERE project=? AND entity_type IN ('component','hook')",
                (project,),
            )
            rows = cur.fetchall()
            lines = [f"- `{r[0]}` — `{r[1]}`" for r in rows] or ["_No components found._"]
            return f"# Components — {project}\n\n" + "\n".join(lines) + f"\n\n{template}"

        elif page == "coverage":
            cur.execute(
                "SELECT entity, file_path FROM entities WHERE project=? AND entity_type='test'",
                (project,),
            )
            rows = cur.fetchall()
            lines = [f"- `{r[0]}` — `{r[1]}`" for r in rows] or ["_No test entities found._"]
            return f"# Test Coverage Map — {project}\n\n" + "\n".join(lines) + f"\n\n{template}"

    except Exception:
        pass

    return template


def generate_wiki(project: str, repo_dir: Path, db_path: Path = None):
    """
    Generate wiki pages from wiki.db data.
    If db_path is None, use the default location in ~/.ai-memory/wiki/{project}.db
    """
    if db_path is None:
        db_path = Path.home() / ".ai-memory" / "wiki" / f"{project}.db"
    
    # Create wiki directory in repo
    wiki_dir = repo_dir / ".ai-wiki" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize wiki DB if needed
    db = DBWiki(db_path)
    
    # Generate wiki index
    index_content = _read_template("index")
    (wiki_dir / "INDEX.md").write_text(index_content, encoding="utf-8")
    
    # Generate architecture page
    arch_content = _read_template("architecture")
    (wiki_dir / "ARCHITECTURE.md").write_text(arch_content, encoding="utf-8")
    
    # Create api/ subdirectory
    api_dir = wiki_dir / "api"
    api_dir.mkdir(exist_ok=True)
    endpoints_content = _read_template("endpoints")
    (api_dir / "endpoints.md").write_text(endpoints_content, encoding="utf-8")
    
    # Create models/ subdirectory
    models_dir = wiki_dir / "models"
    models_dir.mkdir(exist_ok=True)
    models_content = _read_template("models")
    (models_dir / "overview.md").write_text(models_content, encoding="utf-8")
    
    # Create services/ subdirectory
    services_dir = wiki_dir / "services"
    services_dir.mkdir(exist_ok=True)
    services_content = _read_template("services")
    (services_dir / "overview.md").write_text(services_content, encoding="utf-8")
    
    # Create database/ subdirectory
    database_dir = wiki_dir / "database"
    database_dir.mkdir(exist_ok=True)
    database_content = _read_template("database")
    (database_dir / "tables.md").write_text(database_content, encoding="utf-8")
    
    # Create components/ subdirectory
    components_dir = wiki_dir / "components"
    components_dir.mkdir(exist_ok=True)
    components_content = _read_template("components")
    (components_dir / "overview.md").write_text(components_content, encoding="utf-8")
    
    # Create tests/ subdirectory
    tests_dir = wiki_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    coverage_content = _read_template("coverage")
    (tests_dir / "coverage-map.md").write_text(coverage_content, encoding="utf-8")
    
    db.close()
    return True
