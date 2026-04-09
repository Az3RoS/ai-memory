# ai-memory v2 — Complete Architecture Plan
## Multi-project, multi-team, brownfield-first

---

## 1. Real-world scenarios this must handle

Before any architecture, these are the actual situations developers face.
Every design decision below is tested against these scenarios.

```
SCENARIO                                    WHAT MUST HAPPEN
─────────────────────────────────────────── ──────────────────────────────────────────
S1. Existing project, 500+ commits          Backfill history into memory.db silently
    Dev installs ai-memory mid-sprint       CONTEXT.md populated on first run

S2. 5 devs on same repo                    Each has local memory.db
    All commit to same .ai-memory/          CONTEXT.md merges without conflict
    Dev A's decisions visible to Dev B      Committed files are the shared layer

S3. One dev works across 3 projects         Single global memory.db, 3 project slugs
    Pattern from Project A helps Project C  Cross-project patterns surface automatically

S4. Sprint spans 2 teams, 4 projects       Sprint summary aggregates across projects
    PM wants "what happened this sprint"    No manual input from any developer

S5. New dev joins mid-project              Runs setup.py → gets full context instantly
    Has never seen the codebase            CONTEXT.md + onboarding.md = day-1 ready

S6. Developer leaves the team              Their decisions persist in committed files
    Knowledge must not walk out            memory.db is local but .ai-memory/ is shared

S7. Org adopts this across 20 repos        Consistent setup, no per-repo config
    Some repos are Python, some TypeScript  Stack detection handles heterogeneity

S8. CI/CD pipeline integration             GitHub Actions runs ingest on merge to main
    Automated memory without local hooks    Server-side memory building

S9. Monorepo with multiple services        Sub-project scoping within one git repo
    services/auth, services/billing, etc.   Each service gets its own context scope

S10. Merge conflicts in .ai-memory/        CONTEXT.md is auto-generated
     Two devs push simultaneously          Regenerate on conflict, never manual merge
```

---

## 2. Data architecture — three layers

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: TEAM SHARED (committed to git)                       │
│  .ai-memory/ directory in each repo                            │
│  Every dev sees this. Survives team changes.                   │
│  Contains: CONTEXT.md, decisions.md, stack.json, patterns.md   │
│  Merge strategy: auto-regenerate, never manual merge           │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: DEVELOPER LOCAL (per machine)                        │
│  ~/.ai-memory/memory.db — personal, all projects               │
│  Fast FTS5 search, relevance scores, full history              │
│  Never pushed. Each dev builds independently.                  │
│  Rebuilable from git log at any time.                          │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: GIT HISTORY (the immutable source)                   │
│  Commits, diffs, branches, file changes                        │
│  This is the raw signal. Everything above derives from it.     │
│  If memory.db is lost, rebuild from git log. Zero data loss.   │
└─────────────────────────────────────────────────────────────────┘
```

### Why three layers matter

- **Layer 1 (git)** is the ground truth. Memory can always be rebuilt.
- **Layer 2 (local DB)** is the performance layer. FTS5 search, relevance
  scoring, cross-project queries — all fast, all local.
- **Layer 3 (committed files)** is the team layer. A developer who never
  installed ai-memory still gets CONTEXT.md because someone else committed it.

This means: if a developer's laptop dies, they run `setup.py` on a new
machine and `--rebuild` reconstructs memory.db from git history.

---

## 3. File structure (v2 final)

### What ships in the ai-memory repo (the tool itself)

```
ai-memory/
├── setup.py                        # One command to rule them all
├── scripts/
│   ├── memory_cli.py               # CLI: init, ingest, query, sync, status,
│   │                               #       plan, review, sprint, onboard, rebuild
│   ├── ingest.py                   # Parses git diff + branch + file patterns
│   ├── sync.py                     # Generates CONTEXT.md (token-budgeted)
│   ├── detect.py                   # Stack detection, IDE detection
│   ├── pointers.py                 # Generates IDE pointer files
│   ├── backfill.py                 # Imports existing git history
│   ├── migrate.py                  # Schema migrations for existing memory.db
│   └── aggregate.py                # Cross-project and sprint aggregation
├── hooks/
│   ├── post-commit                 # Calls ingest + sync (silent, never blocks)
│   ├── pre-push                    # Refreshes CONTEXT.md before push
│   └── post-merge                  # Re-syncs after pulling others' changes
├── templates/
│   ├── CONTEXT.md.template
│   ├── CLAUDE.md.template
│   ├── cursorrules.template
│   ├── AGENTS.md.template
│   ├── copilot-instructions.template
│   └── gitignore-additions.template
├── README.md
└── AI-MEMORY-README.md
```

### What gets created per repo

```
your-project/
├── .ai-memory/                      # ✓ Committed to git (team-shared)
│   ├── CONTEXT.md                   # ★ Single source of truth for all IDEs
│   ├── index.json                   # Project config: slug, token budget, scope
│   ├── stack.json                   # Auto-detected tech stack
│   ├── patterns.md                  # Auto-detected file co-occurrence patterns
│   ├── decisions.md                 # Architecture Decision Log (append-only)
│   └── .gitattributes               # merge=ours for CONTEXT.md (auto-resolve)
├── CLAUDE.md                        # → Points to .ai-memory/CONTEXT.md
├── .cursorrules                     # → Points to .ai-memory/CONTEXT.md
├── AGENTS.md                        # → Points to .ai-memory/CONTEXT.md
├── .github/
│   └── copilot-instructions.md      # → Points to .ai-memory/CONTEXT.md
└── .vscode/
    └── tasks.json                   # VS Code shortcuts (optional)
```

### Global store (per developer machine)

```
~/.ai-memory/
├── memory.db                        # SQLite + FTS5 (ALL projects)
├── config.json                      # Global settings: developer name, org,
│                                    #   default token budget, preferred IDE
├── projects.json                    # Project registry with paths
└── logs/
    └── <project>-YYYY-MM-DD.md      # Daily logs per project
```

---

## 4. SQLite schema (multi-project, multi-developer aware)

```sql
------------------------------------------------------------
-- Core memories table
------------------------------------------------------------
CREATE TABLE memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,               -- project slug
    timestamp   TEXT NOT NULL,               -- ISO 8601
    type        TEXT NOT NULL,               -- commit|decision|note|pattern|blocker|review
    message     TEXT NOT NULL,               -- human-readable summary
    branch      TEXT,                        -- git branch at time of commit
    author      TEXT,                        -- git author email (for multi-dev)
    commit_hash TEXT,                        -- for dedup on backfill/rebuild
    files_changed   TEXT,                    -- JSON array: ["src/auth/jwt.py", "tests/test_auth.py"]
    modules_touched TEXT,                    -- JSON array: ["src/auth", "tests"]
    diff_stat       TEXT,                    -- "3 files, +45 -12"
    decision_type   TEXT,                    -- dependency|architecture|database|config|deprecation
    relevance       REAL DEFAULT 1.0,        -- decays over time
    surfaced_count  INTEGER DEFAULT 0,       -- times included in CONTEXT.md
    tags            TEXT,                    -- JSON array: ["auth", "jwt", "security"]
    UNIQUE(project, commit_hash)             -- prevents duplicate ingestion
);

CREATE INDEX idx_memories_project ON memories(project, timestamp DESC);
CREATE INDEX idx_memories_type ON memories(project, type);
CREATE INDEX idx_memories_author ON memories(project, author);

------------------------------------------------------------
-- Full-text search
------------------------------------------------------------
CREATE VIRTUAL TABLE memories_fts USING fts5(
    message, files_changed, modules_touched, branch, tags,
    content=memories, content_rowid=id
);

------------------------------------------------------------
-- File co-occurrence (replaces knowledge graph)
-- "files that change together are related"
------------------------------------------------------------
CREATE TABLE file_pairs (
    project     TEXT NOT NULL,
    file_a      TEXT NOT NULL,
    file_b      TEXT NOT NULL,
    co_count    INTEGER DEFAULT 1,
    last_seen   TEXT,
    PRIMARY KEY (project, file_a, file_b)
);

------------------------------------------------------------
-- Cross-project patterns
-- "lessons that transfer between projects"
------------------------------------------------------------
CREATE TABLE patterns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_project  TEXT NOT NULL,
    pattern_type    TEXT NOT NULL,            -- fix|architecture|performance|testing|deployment
    description     TEXT NOT NULL,
    stack_tags      TEXT,                     -- JSON: ["fastapi", "sqlalchemy", "async"]
    trigger_files   TEXT,                     -- JSON: files that activate this pattern
    resolution      TEXT,                     -- what was done to fix/implement
    created         TEXT NOT NULL,
    times_surfaced  INTEGER DEFAULT 0
);

CREATE INDEX idx_patterns_stack ON patterns(stack_tags);

------------------------------------------------------------
-- Stack detection cache
------------------------------------------------------------
CREATE TABLE stacks (
    project         TEXT PRIMARY KEY,
    lang            TEXT,                     -- python|typescript|go|rust|java
    framework       TEXT,                     -- fastapi|django|express|react|spring
    database        TEXT,                     -- sqlite|postgres|mysql|mongo
    test_framework  TEXT,                     -- pytest|jest|vitest|go-test
    build_tool      TEXT,                     -- pip|npm|cargo|gradle
    detected_at     TEXT,
    config_files    TEXT                      -- JSON: files used for detection
);

------------------------------------------------------------
-- Developer registry (for multi-dev scenarios)
------------------------------------------------------------
CREATE TABLE developers (
    email       TEXT PRIMARY KEY,
    name        TEXT,
    projects    TEXT,                         -- JSON array of project slugs
    first_seen  TEXT,
    last_active TEXT
);

------------------------------------------------------------
-- Sprint tracking (cross-project aggregation)
------------------------------------------------------------
CREATE TABLE sprints (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,                -- "2026-W15" or custom name
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    projects    TEXT NOT NULL,                -- JSON array of project slugs
    summary     TEXT,                         -- auto-generated sprint summary
    generated   TEXT                          -- when summary was last built
);

------------------------------------------------------------
-- Schema version (for migrations)
------------------------------------------------------------
CREATE TABLE schema_version (
    version     INTEGER PRIMARY KEY,
    applied     TEXT NOT NULL
);
INSERT INTO schema_version VALUES (2, datetime('now'));
```

---

## 5. Brownfield adoption — importing existing projects

### The problem
A project with 500+ commits already exists. Developer installs ai-memory.
CONTEXT.md must be useful on the first run, not after 50 new commits.

### backfill.py — smart history import

```
python setup.py                        # Triggers backfill automatically
  └── backfill.py runs with defaults:
      ├── Scans git log (all commits, or --limit N)
      ├── Deduplicates by commit_hash (safe to run multiple times)
      ├── For each commit:
      │   ├── Extracts message, author, branch, timestamp
      │   ├── Runs git diff --stat for that commit
      │   ├── Runs git diff --name-only for file list
      │   ├── Detects type (decision/commit/etc.) from signals
      │   └── Inserts into memory.db
      ├── Builds file_pairs from co-occurrence across all commits
      ├── Detects stack from current repo state
      └── Runs sync.py to generate CONTEXT.md
```

### Backfill strategies by project size

```
COMMITS    STRATEGY                          TIME
────────── ─────────────────────────────── ──────────
< 50       Full backfill (all commits)       < 5 sec
50-500     Full backfill                     < 30 sec
500-2000   Last 200 commits + all decisions  < 15 sec
                (scan all messages for decision keywords,
                 but only full-parse recent ones)
2000+      Last 100 commits + decision scan  < 10 sec
                + file structure snapshot
```

### Handling already-active projects with team members

```
SCENARIO: 5 devs on ProjectX. Dev C installs ai-memory.

1. Dev C runs: python setup.py
2. setup.py detects existing .ai-memory/ in repo
   → Does NOT overwrite committed CONTEXT.md
   → Creates local memory.db from git history
   → Registers project in ~/.ai-memory/projects.json
   → Installs hooks for future commits
3. Dev C's next commit triggers ingest + sync
   → CONTEXT.md updates with new data
   → Dev C pushes → other devs get updated CONTEXT.md
4. Devs A, B who haven't installed ai-memory:
   → Still see CONTEXT.md in repo (it's committed)
   → Their IDE reads it via pointer files
   → They just don't get automatic updates from their commits
5. When Dev A eventually runs setup.py:
   → backfill imports their commits too
   → No data loss, no conflicts
```

---

## 6. Multi-developer scenarios

### How local DB + committed files interact

```
           Dev A (London)              Dev B (Mumbai)
           ┌──────────────┐            ┌──────────────┐
           │ memory.db    │            │ memory.db    │
           │ (local, A's  │            │ (local, B's  │
           │  perspective) │            │  perspective) │
           └──────┬───────┘            └──────┬───────┘
                  │ sync.py                    │ sync.py
                  ▼                            ▼
           CONTEXT.md (A)              CONTEXT.md (B)
                  │ git push                   │ git push
                  └──────────┬─────────────────┘
                             ▼
                    git repo (shared)
                    .ai-memory/CONTEXT.md
                    (last pusher's version wins)
```

### Merge conflict resolution for CONTEXT.md

CONTEXT.md is auto-generated. Manual merge is never correct.
Solution: `.ai-memory/.gitattributes` contains:

```
CONTEXT.md merge=ours
patterns.md merge=ours
```

This means: on merge conflict, keep your version. Then post-merge
hook runs sync.py which regenerates from the merged memory.db state.
Result: CONTEXT.md always reflects the current state after merge.

### decisions.md is append-only (never conflicts)

```
# Architecture Decision Log

## [2026-04-08] Switched LLM provider from Groq to Gemini
Author: arnab@tcs.com
Files: src/providers/gemini.py, config/settings.py
Reason: Cost reduction, better rate limits

## [2026-04-07] Chose async SQLAlchemy over raw sqlite3
Author: dev-b@tcs.com
Files: src/models/base.py, requirements.txt
Reason: Connection pooling, migration support
```

Each entry is a new block appended at the top. Two devs adding
decisions simultaneously creates a trivial merge (both additions kept).

### Author tracking in memory.db

```python
# ingest.py extracts author from git
author = subprocess.run(
    ["git", "log", "-1", "--format=%ae"],
    capture_output=True, text=True
).stdout.strip()
```

This enables: "show me all decisions made by Dev B",
"what did the team work on this week", and sprint aggregation.

---

## 7. Multi-project scenarios

### One developer, multiple projects

```
~/.ai-memory/
├── memory.db          # Contains data for ALL projects
│   ├── project=signal     (247 entries)
│   ├── project=trading-app (189 entries)
│   └── project=health-api  (94 entries)
├── projects.json
│   [
│     {"slug": "signal", "path": "/home/arnab/signal", "stack": "python/fastapi"},
│     {"slug": "trading-app", "path": "/home/arnab/trading", "stack": "python/fastapi"},
│     {"slug": "health-api", "path": "/home/arnab/health", "stack": "python/flask"}
│   ]
└── logs/
    ├── signal-2026-04-09.md
    ├── trading-app-2026-04-09.md
    └── health-api-2026-04-08.md
```

### Cross-project pattern surfacing

When sync.py generates CONTEXT.md for project "health-api":

1. Read health-api's stack from stacks table → python, flask, sqlite
2. Query patterns table for matching stack_tags:
   ```sql
   SELECT * FROM patterns
   WHERE json_each.value IN ('python', 'sqlite', 'async')
   AND source_project != 'health-api'
   ORDER BY times_surfaced DESC
   LIMIT 5
   ```
3. If health-api uses SQLite and signal had a blocker about
   async SQLite connections → that pattern surfaces automatically.

### Monorepo support (multiple services, one git repo)

```json
// .ai-memory/index.json for a monorepo
{
  "mode": "monorepo",
  "scopes": {
    "auth-service": {
      "paths": ["services/auth/"],
      "token_budget": 1500
    },
    "billing-service": {
      "paths": ["services/billing/"],
      "token_budget": 1500
    },
    "shared-libs": {
      "paths": ["libs/"],
      "token_budget": 500
    }
  }
}
```

When a commit touches `services/auth/handler.py`:
- ingest.py detects scope = "auth-service"
- Inserts with project = "monorepo/auth-service"
- sync.py generates scoped CONTEXT.md for auth-service
- Shared libs changes surface in ALL scopes

setup.py detects monorepo structure automatically:
- Multiple `package.json` or `requirements.txt` in subdirs
- `services/`, `packages/`, `apps/` directory patterns
- Prompts once: "Detected monorepo. Use scoped memory? [Y/n]"

---

## 8. Sprint and team aggregation

### Sprint tracking

```bash
# Define a sprint (one-time per sprint)
memory sprint start --name "2026-W15" --projects signal,trading-app --days 14

# Auto-generates at sprint end (or on demand)
memory sprint summary
```

Sprint summary pulls from ALL projects in the sprint:

```sql
SELECT m.project, m.type, m.message, m.author, m.timestamp
FROM memories m
WHERE m.project IN ('signal', 'trading-app')
  AND m.timestamp BETWEEN '2026-04-01' AND '2026-04-14'
ORDER BY m.type, m.timestamp DESC
```

Output: `.ai-memory/sprint-2026-W15.md`

```markdown
# Sprint 2026-W15 Summary
Period: 2026-04-01 → 2026-04-14
Projects: signal, trading-app
Developers: arnab@tcs.com, dev-b@tcs.com, dev-c@tcs.com

## Decisions made (5)
- [signal] Switched LLM provider to Gemini (arnab)
- [signal] Adopted async SQLAlchemy (dev-b)
- [trading-app] Moved to WebSocket for live prices (dev-c)
- [trading-app] Chose Redis for session cache (arnab)
- [signal] PWA over native app (arnab)

## Blockers encountered (2)
- [signal] Async session lifecycle in tests (RESOLVED)
- [trading-app] WebSocket reconnection on mobile (OPEN)

## Volume
- signal: 34 commits, 12 files avg per commit
- trading-app: 28 commits, 8 files avg per commit
- Total: 62 commits across 2 projects by 3 developers

## Patterns detected
- Auth module changed 8 times this sprint (signal)
- Provider switching pattern emerging (signal)
- WebSocket + Redis always change together (trading-app)
```

### Team-level aggregation without shared DB

The key insight: **no shared database needed**. Each developer has
their own memory.db. Team visibility comes from committed files:

```
WHAT'S LOCAL (per developer)        WHAT'S SHARED (via git)
─────────────────────────────────── ────────────────────────────────
memory.db (full history + scores)   .ai-memory/CONTEXT.md
relevance scores                    .ai-memory/decisions.md
cross-project patterns              .ai-memory/patterns.md
personal query history              .ai-memory/stack.json
sprint definitions                  CLAUDE.md, .cursorrules, etc.
```

A developer who pushes updates CONTEXT.md and decisions.md.
Other developers pull and get updated context without running anything.
Their local memory.db builds independently from their own commits.

Sprint summaries are generated locally by whoever runs the command,
then committed to git for team visibility.

---

## 9. CI/CD integration (serverless memory)

For teams that want memory built on the server, not locally:

### GitHub Actions workflow

```yaml
# .github/workflows/memory-sync.yml
name: Update AI Memory
on:
  push:
    branches: [main, develop]

jobs:
  memory:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 20  # Last 20 commits for context

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Build memory
        run: |
          python scripts/memory_cli.py init --project ${{ github.event.repository.name }} --repo . --ci
          python scripts/backfill.py --limit 20
          python scripts/sync.py

      - name: Commit updated context
        run: |
          git config user.name "ai-memory[bot]"
          git config user.email "ai-memory@noreply"
          git add .ai-memory/
          git diff --staged --quiet || git commit -m "chore(memory): update context [skip ci]"
          git push
```

The `--ci` flag:
- Skips hook installation (no local git hooks in CI)
- Uses a temporary memory.db (not persisted between runs)
- Generates CONTEXT.md from the last N commits only
- Skips cross-project patterns (CI only sees one repo)

### When CI-built memory meets local memory

Developer pulls CI-updated CONTEXT.md → their local sync.py
respects the committed version until their next commit triggers
a local regeneration. No conflict — local always rebuilds fresh.

---

## 10. CONTEXT.md structure (v2 — multi-dev aware)

```markdown
<!-- AUTO-GENERATED by ai-memory v2. Do not edit manually. -->
<!-- Project: signal | Entries: 247 | Budget: 2000 tokens -->
<!-- Contributors: arnab@tcs.com, dev-b@tcs.com, dev-c@tcs.com -->
<!-- Last sync: 2026-04-09T14:30:00Z | Branch: feat/multi-provider -->

## Identity
Stack: Python 3.11 / FastAPI / async SQLAlchemy / SQLite / pytest
Repo: signal-news-agent
Active branch: feat/multi-provider-llm
Team: 3 contributors this month

## Decisions (persistent — never truncated)
- [2026-04-08] arnab: Switched LLM from Groq → Gemini (cost)
- [2026-04-05] dev-b: Chose async SQLAlchemy over raw sqlite3
- [2026-04-01] arnab: PWA over native — browser-first strategy

## Blockers (active — cleared when resolved)
- Async session lifecycle causes test flakes (since 04-07)
- Gemini rate limiting not implemented (since 04-08)

## Patterns (auto-detected from file co-occurrence)
- auth changes → always paired with tests/test_auth.py
- provider changes → always paired with config/settings.py
- model changes → always paired with alembic migration

## Recent (last 7 days, all contributors)
- [04-09] arnab: fix(providers): Gemini timeout handling
- [04-09] dev-c: feat(dashboard): theme switcher, 3 themes
- [04-08] dev-b: refactor(db): async SQLAlchemy migration
- [04-07] arnab: test(auth): JWT expiry edge cases
- [04-06] dev-c: fix(ui): dark mode contrast issues

## Structure
src/api/       → FastAPI routes
src/agents/    → News analysis pipeline (7 agents)
src/providers/ → LLM abstraction (Groq, Gemini, OpenAI)
src/models/    → SQLAlchemy models (User, Article, Source)
tests/         → pytest with async fixtures

## Cross-project (from other projects with matching stack)
- [trading-app] FastAPI async sessions need explicit close()
- [health-api] SQLite WAL mode prevents write locks in tests
```

---

## 11. setup.py — complete flow

```python
"""
The only command a developer ever runs.
Handles: greenfield, brownfield, monorepo, team join, rebuild.
"""

def main():
    # 1. Validate git repo
    if not is_git_repo():
        exit("Not a git repo. Run this from your project root.")

    # 2. Detect situation
    has_existing_memory = path_exists(".ai-memory/")
    has_existing_db = path_exists(GLOBAL_DB_PATH)
    commit_count = git_commit_count()
    is_monorepo = detect_monorepo()

    # 3. Determine project slug
    if has_existing_memory:
        slug = read_index_json()["slug"]
        print(f"Found existing ai-memory for '{slug}'")
    else:
        slug = derive_slug_from_dirname()

    # 4. Check if project already in global DB
    if has_existing_db and project_exists_in_db(slug):
        print(f"Project '{slug}' already registered. Updating hooks.")
        mode = "update"
    else:
        mode = "fresh"

    # 5. Detect stack
    stack = detect_stack()  # Scans package.json, requirements.txt, etc.
    print(f"Detected: {stack['lang']}/{stack['framework']}")

    # 6. Install/update hooks
    install_hooks()  # post-commit, pre-push, post-merge

    # 7. Create .ai-memory/ structure
    if not has_existing_memory:
        create_ai_memory_dir()
        create_index_json(slug, stack)
        create_gitattributes()  # merge=ours for CONTEXT.md

    # 8. Create pointer files (always, idempotent)
    create_pointer_files()  # CLAUDE.md, .cursorrules, AGENTS.md, etc.

    # 9. Ensure global DB exists with current schema
    init_or_migrate_db()

    # 10. Register project
    register_project(slug, os.getcwd(), stack)

    # 11. Backfill history
    if commit_count > 0:
        backfilled = backfill(slug, limit=smart_limit(commit_count))
        print(f"Imported {backfilled} commits from history")

    # 12. Build co-occurrence data
    build_file_pairs(slug)

    # 13. Detect cross-project patterns
    if has_existing_db:
        surface_patterns(slug, stack)

    # 14. Generate CONTEXT.md
    sync(slug)

    # 15. Suggest .gitignore additions
    suggest_gitignore()

    print(f"\nDone. Memory active for '{slug}'.")
    print("Just commit normally. Everything else is automatic.")
    if mode == "fresh":
        print("\nSuggested next step:")
        print("  git add .ai-memory/ CLAUDE.md .cursorrules AGENTS.md .github/")
        print('  git commit -m "chore: add ai-memory"')
```

---

## 12. Rebuild from scratch (disaster recovery)

```bash
# Developer's laptop dies. New machine. Clone repo.
python setup.py --rebuild
```

What `--rebuild` does:
1. Creates fresh memory.db
2. Scans entire git log (all commits)
3. Rebuilds memories table from commit history
4. Rebuilds file_pairs from co-occurrence
5. Re-detects stack
6. Regenerates CONTEXT.md

Time: ~60 seconds for 2000 commits.
Data loss: zero (git history is the source of truth).

The `--rebuild` flag also handles:
- Schema migrations (old memory.db → new schema)
- Corrupted DB recovery
- Moving to a new machine

---

## 13. Merge conflict strategy

### Files that never conflict (by design)

```
FILE                    STRATEGY              WHY
────────────────────── ───────────────────── ─────────────────────────
CONTEXT.md             merge=ours + regen    Auto-generated, rebuilt on merge
patterns.md            merge=ours + regen    Auto-generated
stack.json             merge=ours + regen    Auto-detected
CLAUDE.md              Never changes         Static 2-line pointer
.cursorrules           Never changes         Static 2-line pointer
AGENTS.md              Never changes         Static 2-line pointer
copilot-instructions   Never changes         Static pointer
```

### Files that merge cleanly (append-only)

```
FILE                    STRATEGY              WHY
────────────────────── ───────────────────── ─────────────────────────
decisions.md           Standard git merge     Append-only, timestamped blocks
                                              Two devs add different blocks →
                                              git auto-merges (no conflict)
index.json             merge=ours             Config, regenerated on sync
```

### post-merge hook ensures freshness

```bash
#!/bin/bash
# .git/hooks/post-merge
python ~/.ai-memory-system/scripts/sync.py 2>/dev/null || true
```

After any pull/merge, CONTEXT.md is regenerated from local memory.db.
This means: even if the pulled CONTEXT.md had conflicts, the local
regeneration produces a correct version immediately.

---

## 14. Growth roadmap — AI SDLC phases

### Phase 1: Memory (this plan)
**Status: Implementing**
- Auto-ingest from git hooks
- Brownfield backfill
- Multi-project, multi-developer support
- Universal IDE context via CONTEXT.md
- Cross-project pattern surfacing
- Sprint aggregation

### Phase 2: Planning assistant
**Trigger: >100 entries per project**
```bash
memory plan "add Stripe payment integration"
```
Outputs: structured plan referencing past decisions, suggesting file
locations from co-occurrence data, warning about known blockers.
Template-based, no LLM. Committed as `.ai-memory/plans/<date>-<slug>.md`.

### Phase 3: Review context
**Trigger: pre-push hook**
```bash
memory review
```
Auto-generates a PR context block: what changed, why (from decisions),
which patterns were followed/broken. Outputs to `.ai-memory/review.md`.
Reviewers read this instead of parsing 30 commits.

### Phase 4: Architecture guardian
**Trigger: >50 patterns in file_pairs**
Pre-commit hook (advisory, never blocks) warns when:
- You changed file A but not file B (they always change together)
- Your commit breaks a detected pattern
- A new dependency contradicts a previous decision
Output: warning message in terminal. Developer decides to proceed or fix.

### Phase 5: Onboarding generator
**Trigger: new contributor detected**
```bash
memory onboard
```
Generates `.ai-memory/onboarding.md` covering: stack, structure,
conventions, all decisions with rationale, common patterns,
active blockers. Committed to git. New developer reads this + CONTEXT.md
and is productive on day 1.

### Phase 6: Org-level intelligence
**Trigger: >10 projects using ai-memory in an org**
Optional shared patterns database (SQLite file on shared drive,
or simple JSON API). Patterns that emerge across multiple teams
surface in all projects with matching stacks.
No cloud. No SaaS. Just a shared file.

---

## 15. Session directives (embedded in pointer files)

### CLAUDE.md
```markdown
# Session directives
- Short sentences. 8-10 words max.
- No filler. No preamble. Tool-first.
- Check .ai-memory/CONTEXT.md before every task.
- Reference decisions by [date]. Respect existing choices.
- If blocked, check blockers section before suggesting workarounds.
- Use memory index. Minimise token usage.

# Project context
@.ai-memory/CONTEXT.md
```

### .cursorrules
```markdown
Always read .ai-memory/CONTEXT.md before starting any task.
It contains project decisions, detected patterns, active blockers,
and recent activity across all contributors.
Reference decisions by date. Do not suggest alternatives to
settled decisions unless explicitly asked.
Short responses. Code first. No preamble.
```

### AGENTS.md
```markdown
# Context source
Read .ai-memory/CONTEXT.md for project memory.
Decisions are final unless user says otherwise.
Patterns section shows which files change together — follow them.
Blockers section shows known issues — check before suggesting.
```

Directive tokens: ~100 per pointer file. Loaded once per session.
CONTEXT.md: ~1,500 tokens. Total ambient cost: ~1,600 tokens.

---

## 16. What was borrowed, what is original

```
CONCEPT                    SOURCE                      OUR VERSION
─────────────────────────  ──────────────────────────  ──────────────────────────
Compiler pipeline          Claude Memory Compiler      git → SQLite → CONTEXT.md
170-token wake-up          MemPalace                   Identity block (5 lines, ~80 tokens)
Typed entries              claude-mem                  commit|decision|pattern|blocker
Zero dependencies          LuciferForge                stdlib Python only
Read-order hierarchy       Cline Memory Bank           Pointers → CONTEXT.md
Diff-based signal          GitHub Copilot Memory       git diff parsing in ingest.py
Token budget ranking       Claude Code docs            decisions > blockers > recent
Co-occurrence graph        ORIGINAL                    file_pairs table in SQLite
Brownfield backfill        ORIGINAL                    Smart git log import on setup
Multi-IDE pointers         ORIGINAL                    One truth, N pointer files
Sprint aggregation         ORIGINAL                    Cross-project SQL queries
Merge conflict avoidance   ORIGINAL                    merge=ours + post-merge regen
Rebuild from git           ORIGINAL                    memory.db is a cache, git is truth
Monorepo scoping           ORIGINAL                    Path-based scope in index.json
```

---

## 17. Implementation priority

```
PHASE   WHAT                           FILES TO WRITE          EFFORT
──────  ─────────────────────────────  ──────────────────────  ──────
  1     Enhanced ingest.py             scripts/ingest.py       1 day
        (diff parsing, branch intent,
         file pattern detection)

  2     sync.py rewrite                scripts/sync.py         1 day
        (token-budgeted CONTEXT.md,
         multi-contributor aware)

  3     setup.py (one-command install)  setup.py                1 day
        (auto-detect everything,
         backfill, pointer files)

  4     backfill.py                    scripts/backfill.py     0.5 day
        (smart history import,
         dedup by commit hash)

  5     Schema migration               scripts/migrate.py      0.5 day
        (v1 → v2 memory.db)

  6     Pointer file templates         templates/*             0.5 day
        (CLAUDE.md, .cursorrules, etc.)

  7     aggregate.py                   scripts/aggregate.py    1 day
        (sprint summaries,
         cross-project patterns)

  8     detect.py                      scripts/detect.py       0.5 day
        (stack, IDE, monorepo detection)

Total: ~6 days for a solo developer
```

---

## 18. Definition of done

```
✓ Developer clones a project with 500 commits
✓ Runs `python setup.py` once
✓ CONTEXT.md is populated with decisions, patterns, recent history
✓ Opens in any IDE (Claude Code, Cursor, VS Code, Codex)
✓ AI assistant reads context without manual prompting
✓ Commits normally — memory updates silently
✓ Team member pushes — others get updated context on pull
✓ New developer joins — runs setup.py, productive in minutes
✓ Sprint summary generated with one command
✓ Developer's laptop dies — rebuild from git, zero data loss
✓ Total ambient token cost per session: <2,000 tokens
✓ Total commands developer ever memorises: 1 (python setup.py)
```
