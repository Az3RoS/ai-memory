"""
feature_init.py — Creates feature/fix folders and templates under .ai-memory/docs/02-feature/.
"""
from pathlib import Path
import json
import shutil

def _slugify(name: str) -> str:
    """Convert name to slug (simple version)."""
    return name.lower().replace(" ", "-").replace("_", "-")

def _read_template(template_name: str) -> str:
    """Read a template file from the tool repo."""
    template_path = Path(__file__).parent.parent / "templates" / f"{template_name}.template"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return ""

def create_feature(mem_dir: Path, feature_name: str, context_block: str = "") -> str:
    """Create a new feature folder with templates and return feature folder path."""
    index_file = mem_dir / "index.json"
    index = json.loads(index_file.read_text(encoding="utf-8"))
    
    feat_num = index.get("next_feat", 1)
    slug = _slugify(feature_name)
    folder_name = f"FEAT_{feat_num:03d}_{slug}"
    feat_dir = mem_dir / "docs" / "02-feature" / folder_name
    feat_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy templates from _templates/
    templates_dir = mem_dir / "docs" / "02-feature" / "_templates"
    template_files = {
        "feature.md": "feature.md",
        "plan.md": "plan.md",
        "scratch.md": "scratch.md",
        "test.md": "test.md",
        "dod.md": "docs-02-dod.md",
    }
    
    for src_name, template_name in template_files.items():
        src_file = templates_dir / src_name if src_name != "dod.md" else None
        if src_file and src_file.exists():
            content = src_file.read_text(encoding="utf-8")
        else:
            content = _read_template(template_name)
        
        # Pre-fill feature.md with name
        if src_name == "feature.md":
            content = content.replace("# Feature", f"# Feature: {feature_name}")
        
        # Pre-fill plan.md with context if provided
        if src_name == "plan.md" and context_block:
            content = content.replace("## Notes", f"## Context\n\n{context_block}\n\n## Notes")
        
        (feat_dir / src_name).write_text(content, encoding="utf-8")
    
    # Increment counter
    index["next_feat"] = feat_num + 1
    index_file.write_text(json.dumps(index, indent=2), encoding="utf-8")
    
    return str(feat_dir)

def create_fix(mem_dir: Path, fix_name: str, context_block: str = "") -> str:
    """Create a new fix folder with templates and return fix folder path."""
    index_file = mem_dir / "index.json"
    index = json.loads(index_file.read_text(encoding="utf-8"))
    
    fix_num = index.get("next_fix", 1)
    slug = _slugify(fix_name)
    folder_name = f"FIX_{fix_num:03d}_{slug}"
    fix_dir = mem_dir / "docs" / "02-feature" / folder_name
    fix_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy templates from _templates/
    templates_dir = mem_dir / "docs" / "02-feature" / "_templates"
    template_files = {
        "feature.md": "feature.md",
        "plan.md": "plan.md",
        "scratch.md": "scratch.md",
        "test.md": "test.md",
        "dod.md": "docs-02-dod.md",
    }
    
    for src_name, template_name in template_files.items():
        src_file = templates_dir / src_name if src_name != "dod.md" else None
        if src_file and src_file.exists():
            content = src_file.read_text(encoding="utf-8")
        else:
            content = _read_template(template_name)
        
        # Pre-fill feature.md with name
        if src_name == "feature.md":
            content = content.replace("# Feature", f"# Fix: {fix_name}")
        
        # Pre-fill plan.md with context if provided
        if src_name == "plan.md" and context_block:
            content = content.replace("## Notes", f"## Context\n\n{context_block}\n\n## Notes")
        
        (fix_dir / src_name).write_text(content, encoding="utf-8")
    
    # Increment counter
    index["next_fix"] = fix_num + 1
    index_file.write_text(json.dumps(index, indent=2), encoding="utf-8")
    
    return str(fix_dir)
