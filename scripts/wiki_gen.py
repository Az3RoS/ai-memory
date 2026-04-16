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
