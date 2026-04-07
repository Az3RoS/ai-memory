# ai-memory

A lightweight, local AI memory system for GitHub Copilot + VS Code.
No cloud. No LLM at write-time. Zero token cost on every commit.

---

## What it does

Builds a persistent, queryable "second brain" from your git history and
manual notes. Copilot reads it automatically via `CONTEXT.md`, and you can
deep-search it on demand with `/memory <terms>`.

```
commit → git hook → memory_cli.py ingest
                  → SQLite + FTS5 (global)
                  → CONTEXT.md   (per repo, auto-injected to Copilot)
                  → daily log    (markdown, human-readable)
                  → knowledge graph (entities + relations)
```

---

## Quickstart

### 1. Clone this repo (or copy `scripts/` anywhere)

```bash
git clone https://github.com/you/ai-memory ~/.ai-memory-system
```

### 2. Initialise a project

Run this once per repo. It sets up hooks, creates `.ai-memory/`, and
registers the project in your global `~/.ai-memory/projects.json`.

```bash
cd ~/your-project
python3 ~/.ai-memory-system/scripts/memory_cli.py init \
  --project my-project \
  --repo .
```

### 3. Start committing

After each commit the system automatically:
- Ingests the commit into SQLite
- Updates `CONTEXT.md` in your repo
- Writes today's daily log

### 4. Use in Copilot Chat

Copilot reads `.ai-memory/CONTEXT.md` automatically via
`.github/copilot-instructions.md`. For deeper search:

```
/memory fastapi async session
/memory last week decisions
/memory blocker
```

---

## Directory structure

```
~/.ai-memory/               ← global store
  memory.db                 ← SQLite + FTS5 (all projects)
  projects.json             ← project registry
  logs/
    <project>-YYYY-MM-DD.md ← daily logs
  entities/
    <project>.md            ← knowledge graph

<your-repo>/
  .ai-memory/               ← per-repo (committed to git)
    CONTEXT.md              ← ambient Copilot context (auto-generated)
    decisions.md            ← architecture decisions ledger
    index.json              ← slug pointer + stats
  .github/
    copilot-instructions.md ← tells Copilot to read CONTEXT.md
  .vscode/
    tasks.json              ← VS Code task shortcuts
```

---

## CLI reference

```bash
# All commands auto-detect project from .ai-memory/index.json
python3 scripts/memory_cli.py <command> [options]

ingest   [--project] [--message]    Ingest current commit into memory
query    <terms> [--limit] [--format context|json]  Full-text search
log      [--message]                Write/update today's daily log
sync     [--project]                Regenerate CONTEXT.md + decisions.md
context  [--tokens <budget>]        Print context block for current project
graph    [--project]                Rebuild knowledge graph
init     --project <slug> --repo <path>  Initialise a new project
status                              Show all registered projects
```

---

## Token budget strategy

| Layer | What | Tokens |
|-------|------|--------|
| Ambient (CONTEXT.md) | Recent + decisions always present | ~1,500 |
| On-demand (/memory) | FTS5 ranked results | ~1,500 |
| Total max per session | Both combined | ~3,000 |

Budget is configurable per project in `projects.json`:

```json
{ "slug": "signal", "token_budget": 2000 }
```

Entries are ranked: **decisions first → blockers → recent → rest**.
Truncation is clean — never mid-entry.

---

## Multi-project / multi-developer

- **Global DB** (`~/.ai-memory/memory.db`) — personal, stays local.
- **Repo `.ai-memory/`** — committed to git, shared with the team.
- Each developer runs `init` once; their local DB builds independently.
- Shared `CONTEXT.md` + `decisions.md` mean Copilot has team context
  even for developers who haven't set up the full system.

---

## Scaling to a new project

```bash
cd ~/new-repo
python3 ~/.ai-memory-system/scripts/memory_cli.py init \
  --project new-repo \
  --repo .
```

That's it. No config files to copy. Hooks auto-install.

---

## Future upgrade paths

| Path | What to change |
|------|----------------|
| Vector search | Swap SQLite FTS5 for pgvector / sqlite-vss |
| LLM summarisation | Add `memory_summarise.py` as a nightly cron |
| Team shared DB | Point `global_db_path()` to a shared Postgres instance |
| CI integration | Run `memory_cli.py ingest` in your GitHub Actions workflow |

---

## Requirements

- Python 3.10+
- No external packages — stdlib only (`sqlite3`, `subprocess`, `pathlib`, `json`)
- Git (for hook integration)
- VS Code + GitHub Copilot Chat (for slash command integration)
