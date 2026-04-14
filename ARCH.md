# ai-memory — Definitive Implementation Plan
## The engine that creates and maintains .ai-memory/ and .ai-wiki/

---

## 1. What ai-memory is

ai-memory is a single tool that a developer installs once. It creates
and maintains two folders in every working repository:

**.ai-memory/** — the temporal layer: what happened, what was decided,
what the team is working on, how the project should be built.

**.ai-wiki/** — the structural layer: what exists in the codebase right
now — every endpoint, model, service, component, their dependencies,
blast radii, and test coverage.

Both folders are committed to git (except binary databases which stay
local). Both are readable by any AI IDE via pointer files. Both update
automatically on every commit via git hooks.

ai-memory does NOT provide a UI. It produces data. The UI is provided
by ai-architect (a separate tool that consumes ai-memory's output).

---

## 2. File structure of the ai-memory tool itself

This is what lives in the `github.com/Az3RoS/ai-memory` repository.

```
ai-memory/
│
├── setup.py
│   The single entry point. Developer runs `python setup.py` in any
│   repo. It detects the project, scans the codebase, imports git
│   history, generates all files, installs all hooks. One command.
│
├── scripts/
│   │
│   ├── cli.py
│   │   CLI router. Parses arguments and dispatches to the correct
│   │   script. Commands: init, scan, ingest, sync, query, status,
│   │   feature, fix, lint, review, sprint, onboard, rebuild.
│   │   Each command is a thin wrapper that calls the appropriate
│   │   module function.
│   │
│   ├── db_memory.py
│   │   Database module for memory.db (the temporal database).
│   │   Contains: schema definition, connection helper, all CRUD
│   │   functions for memories, file_pairs, knowledge_graph,
│   │   patterns, stacks, developers, sprints tables.
│   │   Location of memory.db: ~/.ai-memory/memory.db (local, never committed).
│   │   This file is imported by: ingest, sync, review, lint, feature,
│   │   aggregate, backfill.
│   │
│   ├── db_wiki.py
│   │   Database module for wiki.db (the structural database).
│   │   Contains: schema definition, connection helper, all CRUD
│   │   functions for entities, relationships, entities_fts,
│   │   scan_state tables.
│   │   Location of wiki.db: ~/.ai-memory/wiki/{project}.db (local, never committed).
│   │   This file is imported by: all scan_* modules, wiki_gen, blast_radius.
│   │
│   ├── ingest.py
│   │   Parses the latest git commit and stores structured data in
│   │   memory.db. Extracts: commit message, author, branch, diff stat,
│   │   changed files, modules touched, imports from diff. Detects
│   │   commit type (decision, blocker, commit) from signals. Updates
│   │   file co-occurrence pairs. Updates temporal knowledge graph.
│   │   Called by: post-commit hook.
│   │
│   ├── sync.py
│   │   The compiler. Reads memory.db and generates .ai-memory/CONTEXT.md.
│   │   Applies token budget. Ranks entries: decisions > blockers >
│   │   patterns > recent. Never truncates mid-entry. Also generates
│   │   patterns.md from file_pairs data.
│   │   Called by: post-commit hook (after ingest), post-merge hook.
│   │
│   ├── scan.py
│   │   The scanner orchestrator. Coordinates language-specific scanners.
│   │   Handles full scan (first run) and incremental scan (per commit).
│   │   Uses SHA-256 hash comparison to skip unchanged files.
│   │   Writes to wiki.db and generates .ai-wiki/wiki/ pages.
│   │   Called by: setup.py (full scan), post-commit hook (incremental).
│   │
│   ├── scan_python.py
│   │   Python-specific scanner using stdlib `ast` module.
│   │   Extracts: classes, functions, async functions, decorators,
│   │   imports, type hints, docstrings, endpoint definitions
│   │   (FastAPI/Flask/Django decorators), model definitions
│   │   (SQLAlchemy/Django ORM), schema definitions (Pydantic),
│   │   service classes, constants.
│   │   No external dependencies — ast is stdlib.
│   │
│   ├── scan_javascript.py
│   │   JavaScript/TypeScript scanner using regex patterns.
│   │   Extracts: React components (function, arrow, const), custom
│   │   hooks (useXxx), TypeScript interfaces and type aliases,
│   │   prop definitions, API calls (fetch, axios, useSWR, useQuery),
│   │   imports (ES6 import, require), exports, Next.js page routes
│   │   (from file paths), state management (zustand, redux, context).
│   │   No external dependencies — re is stdlib.
│   │
│   ├── scan_sql.py
│   │   SQL and migration file scanner using regex.
│   │   Extracts: CREATE TABLE definitions (columns, types, constraints),
│   │   foreign keys, indexes, ALTER TABLE changes, Alembic migration
│   │   operations (op.create_table, op.add_column), Django migration
│   │   operations. Builds table entities with full column metadata.
│   │   No external dependencies.
│   │
│   ├── scan_generic.py
│   │   Language-agnostic scanner using file structure and config files.
│   │   Extracts: module hierarchy from directory structure, layer
│   │   detection (api, services, models, tests) from directory names,
│   │   test-to-source file mapping from naming conventions,
│   │   dependencies from package.json/requirements.txt, env vars
│   │   from .env.example, Docker services from docker-compose.yml.
│   │   No external dependencies.
│   │
│   ├── wiki_gen.py
│   │   Generates markdown wiki pages from wiki.db data.
│   │   Produces: INDEX.md (master TOC with stats), ARCHITECTURE.md
│   │   (system overview), api/endpoints.md (all endpoints with call
│   │   chains), models/overview.md (all models with columns),
│   │   models/relationships.md (FK diagram), services/overview.md
│   │   (services with dependencies), services/dependency-graph.md,
│   │   database/tables.md (full schema), components/overview.md
│   │   (for frontend projects), tests/coverage-map.md (source→test mapping).
│   │   Each page is generated by querying wiki.db and formatting with
│   │   a markdown template.
│   │   Called by: scan.py (after scanning), setup.py (initial generation).
│   │
│   ├── blast_radius.py
│   │   Impact analysis engine. Given a set of changed files, performs
│   │   BFS traversal through the relationships table in wiki.db to
│   │   find all directly and indirectly affected entities within N hops.
│   │   Also finds test files covering impacted entities.
│   │   Produces markdown reports (used by review.py and wiki pages).
│   │   Called by: review.py (pre-push), wiki_gen.py (impact pages).
│   │
│   ├── detect.py
│   │   Auto-detection module. Detects: programming language (from
│   │   dependency files), framework (from dependency contents), database
│   │   (from ORM/driver dependencies), test framework, build tool, IDE
│   │   presence (from directory markers), monorepo structure (from
│   │   multiple dependency files in subdirs).
│   │   Called by: setup.py (initial detection).
│   │
│   ├── pointers.py
│   │   Generates IDE-specific pointer files. Creates: CLAUDE.md,
│   │   .cursorrules, AGENTS.md, .windsurfrules, GEMINI.md,
│   │   .github/copilot-instructions.md, .junie/guidelines.md.
│   │   Each pointer contains: session directives, skill routing
│   │   table, reference to CONTEXT.md.
│   │   All pointers have identical content, different filenames.
│   │   Called by: setup.py (initial creation).
│   │
│   ├── backfill.py
│   │   Imports existing git history into memory.db. Walks git log,
│   │   extracts commit data, runs type detection, builds file_pairs
│   │   from co-occurrence. Smart limit: full parse for <500 commits,
│   │   recent+decision-scan for larger repos. Deduplicates by
│   │   commit_hash (safe to run multiple times).
│   │   Called by: setup.py (initial import).
│   │
│   ├── feature_init.py
│   │   Creates FEAT_xxx or FIX_xxx folders under .ai-memory/features/.
│   │   Generates 5 template files: feature.md (or fix.md), plan.md,
│   │   scratch.md, test.md, commit.md. Auto-increments counter from
│   │   index.json. Pre-fills plan.md prompt with CONTEXT.md content
│   │   and wiki structure (if .ai-wiki/ exists).
│   │   Called by: cli.py (memory feature/fix commands).
│   │
│   ├── feature_close.py
│   │   Detects and processes feature completion. Triggered when
│   │   commit.md is committed with Status: DONE/PARTIAL/ABANDONED.
│   │   Auto-fills completion date, duration, files changed.
│   │   Extracts decisions → appends to decisions.md.
│   │   Extracts anti-patterns from scratch.md → appends to antipatterns.md.
│   │   Creates memory.db entry (type: feature-complete).
│   │   Called by: post-commit hook.
│   │
│   ├── review.py
│   │   Pre-push code review generator. Combines structural analysis
│   │   (blast radius from wiki.db) with temporal analysis (decision
│   │   compliance, pattern compliance, guideline compliance from
│   │   memory.db). Generates .ai-memory/review.md (not committed)
│   │   and prints advisory summary to terminal.
│   │   Called by: pre-push hook.
│   │
│   ├── guidelines_check.py
│   │   Checks changed files against .ai-memory/project/guidelines.md.
│   │   Uses regex to detect: missing test files for new source files,
│   │   wrong-layer imports (model in route), hardcoded URLs/secrets,
│   │   print() instead of logger.
│   │   Called by: review.py.
│   │
│   ├── lint.py
│   │   Knowledge base health checker. Scans both memory.db and wiki.db
│   │   for: contradicting decisions, stale decisions, broken patterns,
│   │   orphan features, unresolved blockers, missing test coverage,
│   │   dead code (functions with no callers), circular dependencies.
│   │   Generates .ai-memory/lint-report.md (not committed).
│   │   Called by: cli.py (memory lint command).
│   │
│   ├── aggregate.py
│   │   Sprint and cross-project aggregation. Queries memory.db across
│   │   project boundaries. Generates sprint summaries with: decisions
│   │   made, blockers resolved, features completed, patterns detected.
│   │   Also detects cross-project patterns (same problem solved
│   │   differently in different repos).
│   │   Called by: cli.py (memory sprint command).
│   │
│   ├── migrate.py
│   │   Schema migration handler. Detects current schema version in
│   │   memory.db and wiki.db, applies incremental migrations to bring
│   │   them to the latest version. Handles v1→v2 migration for
│   │   existing ai-memory users.
│   │   Called by: setup.py (if existing DB detected).
│   │
│   ├── pr_context.py
│   │   PR description generator. Reads review.md and formats it as
│   │   a copy-pasteable PR description. Includes: summary, decisions,
│   │   blast radius, risk score, AC status (if feature-linked).
│   │   Called by: pre-push hook (after review.py).
│   │
│   └── utils.py
│       Shared utilities. Functions: timestamp_scratch_notes (adds
│       timestamps to un-timestamped lines in scratch.md), slugify
│       (converts names to filesystem-safe slugs), estimate_tokens
│       (rough token count for a markdown string), read_json/write_json,
│       get_project_slug (reads from .ai-memory/index.json).
│       Called by: multiple scripts.
│
├── hooks/
│   │
│   ├── post-commit
│   │   Shell script. Fires after every git commit. Calls in order:
│   │   1. ingest.py (memory.db update)
│   │   2. sync.py (CONTEXT.md regeneration)
│   │   3. scan.py --incremental (wiki.db + wiki pages update)
│   │   4. feature_close.py (check for commit.md Status)
│   │   All calls are silent (2>/dev/null || true). Never blocks.
│   │   Has recursion guard: checks AI_MEMORY_RUNNING env var.
│   │
│   ├── pre-commit
│   │   Shell script. Fires before every commit. Calls:
│   │   1. utils.py timestamp-scratch (timestamps scratch.md lines)
│   │   Never blocks the commit.
│   │
│   ├── pre-push
│   │   Shell script. Fires before git push. Calls:
│   │   1. review.py (generates review.md + terminal output)
│   │   2. pr_context.py (generates pr-description.md)
│   │   Advisory only. Never blocks the push.
│   │
│   └── post-merge
│       Shell script. Fires after git pull/merge. Calls:
│       1. sync.py (regenerate CONTEXT.md from merged state)
│       2. scan.py --incremental (re-scan changed files in merge)
│
├── templates/
│   │
│   ├── context.md.template          Structure template for CONTEXT.md
│   ├── pointer.md.template          Universal pointer content (for all IDEs)
│   ├── guidelines-python.md         Starter Python coding standards
│   ├── guidelines-typescript.md     Starter TypeScript coding standards
│   ├── guidelines-general.md        Generic coding standards
│   ├── feature.md.template          Feature requirement template
│   ├── fix.md.template              Bug/defect report template
│   ├── plan.md.template             Implementation plan prompt template
│   ├── scratch.md.template          Working notes template (header only)
│   ├── test.md.template             Test plan prompt template
│   ├── commit.md.template           Outcome/close template
│   ├── gitattributes.template       merge=ours rules for auto-generated files
│   ├── wiki-index.md.template       Wiki INDEX.md template
│   ├── wiki-architecture.md.template  Wiki ARCHITECTURE.md template
│   ├── wiki-endpoints.md.template     Wiki endpoints page template
│   ├── wiki-models.md.template        Wiki models page template
│   ├── wiki-services.md.template      Wiki services page template
│   ├── wiki-database.md.template      Wiki database page template
│   ├── wiki-components.md.template    Wiki components page template
│   └── wiki-coverage.md.template      Wiki test coverage page template
│
├── skills/
│   │
│   ├── review.md          Code review: how to use CONTEXT.md + wiki for reviewing changes
│   ├── guidelines.md      Guidelines: how to check code against guidelines.md
│   ├── feature.md         Feature: how to create and work through a feature lifecycle
│   ├── help.md            Dev help: how to find answers using context + wiki
│   ├── debug.md           Debug: how to use blast radius + recent changes for debugging
│   ├── onboard.md         Onboard: how to understand a new codebase using wiki + context
│   ├── sprint.md          Sprint: how to generate sprint summaries
│   ├── lint.md            Lint: how to run and interpret knowledge health checks
│   ├── impact.md          Impact: how to analyze blast radius of changes
│   └── architect.md       Architect: how to query codebase structure from wiki
│
├── tests/
│   │
│   ├── conftest.py                  Shared test fixtures
│   ├── fixtures/                    Sample source files for scanner tests
│   │   ├── python_sample/           5-6 Python files forming a mini FastAPI project
│   │   ├── javascript_sample/       5-6 JS/TS files forming a mini React project
│   │   └── sql_sample/              2-3 SQL and migration files
│   ├── test_db_memory.py            memory.db schema, CRUD, FTS5, relevance
│   ├── test_db_wiki.py              wiki.db schema, entities, relationships, BFS
│   ├── test_ingest.py               Commit parsing, type detection, imports
│   ├── test_sync.py                 CONTEXT.md generation, token budget, ranking
│   ├── test_scan_python.py          AST extraction: classes, functions, endpoints
│   ├── test_scan_javascript.py      Regex extraction: components, hooks, imports
│   ├── test_scan_sql.py             SQL parsing: tables, columns, FKs
│   ├── test_scan_generic.py         Structure detection, config parsing
│   ├── test_wiki_gen.py             Wiki page generation, template rendering
│   ├── test_blast_radius.py         BFS traversal, impact sets, test coverage
│   ├── test_detect.py               Stack, IDE, monorepo detection
│   ├── test_backfill.py             History import, deduplication
│   ├── test_feature.py              Feature/fix creation, close, decisions
│   ├── test_review.py               Compliance checks, risk scoring
│   ├── test_lint.py                 Each lint check as separate test
│   └── test_guidelines.py           Regex guideline checks
│
├── README.md                        Adoption-focused (the one we already wrote)
└── AI-MEMORY-README.md              Developer setup guide (step-by-step)
```

---

## 3. What gets created in a working repo (after setup.py)

This is what appears in the developer's actual project after running
`python setup.py`.

```
your-project/
│
├── .ai-memory/                              ← COMMITTED TO GIT
│   │
│   ├── CONTEXT.md
│   │   The single source of truth for all AI IDEs. Auto-generated
│   │   by sync.py. Contains: project identity (stack, branch, team),
│   │   guidelines summary, active features + AC progress, decisions
│   │   (never truncated), blockers, patterns, anti-patterns, recent
│   │   activity (all contributors), module map summary, cross-project
│   │   insights. Token budget: ~2000 tokens. Regenerated on every
│   │   commit. Never edited manually.
│   │
│   ├── index.json
│   │   Project metadata. Contains: slug, next_feat counter, next_fix
│   │   counter, token_budget, created_at, last_sync. Written by
│   │   setup.py, updated by feature_init.py (counters) and sync.py
│   │   (last_sync).
│   │
│   ├── project/
│   │   │
│   │   ├── overview.md
│   │   │   High-level project description. Initially generated by
│   │   │   setup.py from detected stack + directory structure.
│   │   │   Developer can edit this manually to add business context,
│   │   │   team info, deployment details. Referenced by CONTEXT.md
│   │   │   identity section.
│   │   │
│   │   ├── architecture.md
│   │   │   Architecture conventions. Initially populated from detected
│   │   │   patterns (layer structure, naming conventions). Developer
│   │   │   can edit. Defines intended architecture: which layer calls
│   │   │   which, what goes where, what's forbidden. Used by lint.py
│   │   │   to detect architecture drift.
│   │   │
│   │   ├── guidelines.md
│   │   │   Coding standards. Starter template generated based on
│   │   │   detected stack (Python, TypeScript, or general). Developer
│   │   │   edits to match team conventions. Sections: naming, patterns,
│   │   │   architecture rules, testing rules, anti-patterns. Used by
│   │   │   guidelines_check.py in pre-push hook. Referenced in
│   │   │   CONTEXT.md as compressed summary.
│   │   │
│   │   ├── decisions.md
│   │   │   Architecture Decision Log. Append-only. Each entry:
│   │   │   date, author, decision description, rationale, affected
│   │   │   files. Auto-populated from: commit type detection (ingest.py)
│   │   │   and feature close (feature_close.py). Developer can also
│   │   │   add manually. Entries are permanent — never deleted, only
│   │   │   superseded. Referenced in CONTEXT.md decisions section.
│   │   │
│   │   ├── patterns.md
│   │   │   Auto-detected file co-occurrence patterns. Generated by
│   │   │   sync.py from file_pairs table. Shows which files always
│   │   │   change together and the confidence percentage. Used by
│   │   │   review.py to detect pattern violations. Developer should
│   │   │   not edit — auto-generated.
│   │   │
│   │   └── antipatterns.md
│   │       Known pitfalls. Auto-populated from: feature scratch.md
│   │       entries marked as "tried and rejected" during feature
│   │       close. Developer can also add manually. Referenced in
│   │       CONTEXT.md anti-patterns section and by skills/debug.md.
│   │
│   ├── features/
│   │   │
│   │   ├── FEAT_001_news-pipeline/
│   │   │   ├── feature.md        Requirement + acceptance criteria
│   │   │   ├── plan.md           Implementation plan (prompt + response)
│   │   │   ├── scratch.md        Working notes (auto-timestamped)
│   │   │   ├── test.md           Test plan (prompt + response)
│   │   │   └── commit.md         Outcome summary (Status: DONE)
│   │   │
│   │   ├── FEAT_002_dark-mode/
│   │   │   └── ... (same 5 files, Status: DONE)
│   │   │
│   │   ├── FEAT_003_gemini-provider/
│   │   │   └── ... (same 5 files, Status: empty = ACTIVE)
│   │   │
│   │   └── FIX_001_async-timeout/
│   │       ├── fix.md            Bug description + expected behaviour
│   │       ├── plan.md           Investigation plan
│   │       ├── scratch.md        Debug notes
│   │       ├── test.md           Regression test plan
│   │       └── commit.md         Root cause + fix summary
│   │
│   ├── skills/
│   │   │   Copied from ai-memory tool's skills/ directory during
│   │   │   setup.py. These are IDE-agnostic markdown instructions
│   │   │   that the AI reads on demand when the developer asks
│   │   │   about a specific topic. Referenced from pointer files.
│   │   │
│   │   ├── review.md
│   │   ├── guidelines.md
│   │   ├── feature.md
│   │   ├── help.md
│   │   ├── debug.md
│   │   ├── onboard.md
│   │   ├── sprint.md
│   │   ├── lint.md
│   │   ├── impact.md
│   │   └── architect.md
│   │
│   └── .gitattributes
│       Merge strategy for auto-generated files:
│       CONTEXT.md merge=ours
│       patterns.md merge=ours
│       This means: on merge conflict, keep local version, then
│       post-merge hook regenerates from merged database state.
│
├── .ai-wiki/                                ← COMMITTED TO GIT
│   │
│   ├── wiki/
│   │   │   All pages are auto-generated by wiki_gen.py. Developer
│   │   │   should not edit these. Regenerated on every commit
│   │   │   (incremental — only pages for affected modules).
│   │   │
│   │   ├── INDEX.md
│   │   │   Master table of contents. Quick stats (entity counts,
│   │   │   relationship counts, test coverage %). Links to all
│   │   │   section pages. Architecture flow summary.
│   │   │
│   │   ├── ARCHITECTURE.md
│   │   │   System-level overview. Layer analysis (API → Service →
│   │   │   Model → DB). Maximum dependency depth. Circular dependency
│   │   │   check result. Module grouping.
│   │   │
│   │   ├── api/
│   │   │   ├── endpoints.md
│   │   │   │   Every API endpoint. For each: HTTP method, path, file
│   │   │   │   location, line number, auth requirements (from decorators),
│   │   │   │   input schema (with fields), output schema (with fields),
│   │   │   │   call chain (which service, which model), middleware.
│   │   │   │
│   │   │   └── middleware.md
│   │   │       Auth middleware, rate limiting, CORS, error handlers.
│   │   │       For each: file location, what it does, which endpoints
│   │   │       use it.
│   │   │
│   │   ├── models/
│   │   │   ├── overview.md
│   │   │   │   All ORM models. For each: class name, file, table name,
│   │   │   │   columns (name, type, constraints), relationships.
│   │   │   │
│   │   │   └── relationships.md
│   │   │       Foreign key map. Which model references which. Cascade
│   │   │       rules. Join patterns detected from query usage.
│   │   │
│   │   ├── services/
│   │   │   ├── overview.md
│   │   │   │   All service classes. For each: file, public methods
│   │   │   │   (with signatures), dependencies (what it imports),
│   │   │   │   dependents (what imports it).
│   │   │   │
│   │   │   └── dependency-graph.md
│   │   │       Service-to-service dependency chains. Maximum depth.
│   │   │       Circular dependency check. Config dependencies.
│   │   │
│   │   ├── schemas/
│   │   │   └── overview.md
│   │   │       All Pydantic/validation schemas. For each: fields with
│   │   │       types, required/optional, defaults, which endpoint uses it.
│   │   │
│   │   ├── database/
│   │   │   ├── tables.md
│   │   │   │   All database tables. For each: columns with types, PKs,
│   │   │   │   FKs, indexes, constraints. Derived from model metadata
│   │   │   │   and migration files.
│   │   │   │
│   │   │   └── migrations.md
│   │   │       Migration history. Chronological list of schema changes.
│   │   │       What changed, when, which table affected.
│   │   │
│   │   ├── components/
│   │   │   │   (Only generated for frontend projects that have React,
│   │   │   │   Vue, Svelte, or Angular components detected)
│   │   │   │
│   │   │   ├── overview.md
│   │   │   │   Component tree. Parent→child rendering relationships.
│   │   │   │   Props passed between components.
│   │   │   │
│   │   │   ├── hooks.md
│   │   │   │   Custom hooks. For each: name, parameters, return type,
│   │   │   │   which components use it.
│   │   │   │
│   │   │   └── pages.md
│   │   │       Page routes. For each: path, component, layout, guards.
│   │   │       Derived from file-based routing or router config.
│   │   │
│   │   ├── config/
│   │   │   └── overview.md
│   │   │       Settings, env vars, feature flags. Which parts of the
│   │   │       code use which config values.
│   │   │
│   │   └── tests/
│   │       └── coverage-map.md
│   │           Source file → test file mapping. Files with tests vs
│   │           files without. Coverage gaps highlighted.
│   │
│   └── .gitattributes
│       merge=ours for all wiki/ pages (auto-generated, regenerate
│       on conflict via post-merge hook).
│
├── CLAUDE.md                    Pointer file for Claude Code
├── .cursorrules                 Pointer file for Cursor
├── AGENTS.md                    Pointer file for Codex CLI / OpenClaw
├── .windsurfrules               Pointer file for Windsurf
├── GEMINI.md                    Pointer file for Gemini CLI
├── .github/
│   └── copilot-instructions.md  Pointer file for VS Code + Copilot
├── .junie/
│   └── guidelines.md            Pointer file for JetBrains
└── .vscode/
    └── tasks.json               VS Code task shortcuts (optional)
```

---

## 4. What stays local per developer (never committed)

```
~/.ai-memory/
│
├── memory.db
│   SQLite database. Contains all temporal data for ALL projects.
│   Tables: memories, memories_fts, file_pairs, knowledge_graph,
│   patterns, stacks, developers, sprints, schema_version.
│   Rebuilt from git history via `setup.py --rebuild` if lost.
│
├── wiki/
│   ├── signal.db              wiki.db for project "signal"
│   ├── trading-app.db         wiki.db for project "trading-app"
│   └── health-api.db          wiki.db for project "health-api"
│   Each project has its own structural database.
│   Rebuilt from source scan via `memory scan --full` if lost.
│
├── config.json
│   Developer preferences: name, email, default token budget,
│   default guidelines template.
│
├── projects.json
│   Project registry. For each project: slug, local path, stack,
│   last_sync timestamp. Used by aggregate.py for cross-project
│   queries and by ai-architect for project discovery.
│
└── logs/
    ├── signal-2026-04-14.md           Daily log for signal
    ├── signal-2026-04-13.md
    ├── trading-app-2026-04-14.md       Daily log for trading-app
    └── ...
```

---

## 5. Script-by-script specification

### 5.1 db_memory.py

**Purpose:** All database operations for memory.db.

**Constants to define:**
- SCHEMA_VERSION (integer, current version)
- DEFAULT_TOKEN_BUDGET (integer, 2000)
- DEFAULT_DB_PATH (Path: ~/.ai-memory/memory.db)
- VALID_MEMORY_TYPES (list: commit, decision, note, pattern, blocker, feature-complete)
- VALID_DECISION_TYPES (list: dependency, architecture, database, config, deprecation)

**Functions to implement (11 total):**

1. `get_db_path()` → Path. Check env var AI_MEMORY_DB_PATH, default to ~/.ai-memory/memory.db, create parent dirs.
2. `get_connection(db_path)` → Connection. WAL mode, foreign keys, busy timeout 5000ms.
3. `init_schema(conn)` → None. Create all tables with IF NOT EXISTS. Check schema_version, run migrations if needed.
4. `insert_memory(conn, project, timestamp, type, message, **kwargs)` → int or None. INSERT OR IGNORE unique on project+commit_hash. JSON-encode list fields. Return rowid or None for duplicate.
5. `query_memories(conn, project, terms, type, limit)` → list of dict. FTS5 search if terms provided, filter by type if specified, else most recent. Apply limit.
6. `update_file_pairs(conn, project, files_list)` → None. Generate all pairs (itertools.combinations), INSERT OR UPDATE co_count+1, update last_seen.
7. `get_ranked_context(conn, project, token_budget)` → dict with sections. Query by priority: decisions (always included), blockers, patterns (from file_pairs), recent. Estimate ~20 tokens per entry. Fill until budget reached. Never truncate mid-entry.
8. `insert_knowledge_graph(conn, project, subject, predicate, object, source, confidence)` → int. INSERT OR REPLACE, update last_seen on conflict.
9. `calculate_relevance(entry_type, age_days, surfaced_count)` → float. Exponential decay (exp(-0.03*age)), type multiplier (decision=3, blocker=2, pattern=2.5, note=1.5, commit=1), access boost (1 + 0.1*surfaced_count).
10. `get_cross_project_patterns(conn, project, stack_tags)` → list of dict. Query patterns table for matching stack_tags from OTHER projects, limit 5, order by times_surfaced.
11. `get_file_pair_patterns(conn, project, min_count)` → list of dict. Query file_pairs where co_count >= min_count, return (file_a, file_b, co_count, percentage).

**Tests (15):** Schema creation, each CRUD function, FTS5 search accuracy, relevance calculation edge cases (90-day decision vs 7-day commit), file_pairs co-occurrence, empty database handling.

---

### 5.2 db_wiki.py

**Purpose:** All database operations for wiki.db (per-project structural database).

**Constants to define:**
- WIKI_SCHEMA_VERSION (integer)
- VALID_ENTITY_TYPES (list: class, function, async_function, endpoint, model, schema, service, table, component, hook, page, config, test, module, decorator, middleware, constant, type_alias, enum, external)
- VALID_RELATIONSHIP_TYPES (list: imports, calls, inherits, implements, depends_on, validates, returns, maps_to_table, has_column, has_field, uses_middleware, tested_by, renders, provides_prop, consumes_api, configured_by, migrated_by, decorates, instantiates)

**Functions to implement (12 total):**

1. `get_wiki_db_path(project_slug)` → Path. Returns ~/.ai-memory/wiki/{project_slug}.db, create parent dirs.
2. `get_connection(project_slug)` → Connection. WAL mode, foreign keys, cascade deletes enabled.
3. `init_schema(conn)` → None. Create entities, relationships, entities_fts (with triggers), scan_state, schema_version.
4. `insert_entity(conn, project, entity_type, name, file_path, **kwargs)` → int. INSERT OR REPLACE. Auto-generate qualified_name from file_path + name. kwargs: line_start, line_end, signature, docstring, decorators (JSON), metadata (JSON).
5. `insert_relationship(conn, source_id, rel_type, target_id, **kwargs)` → int. INSERT, kwargs: metadata (JSON).
6. `delete_entities_for_file(conn, project, file_path)` → int (count deleted). DELETE FROM entities WHERE file_path=?. Cascade deletes relationships. Also delete from scan_state.
7. `get_entity_by_name(conn, project, name)` → dict or None. Exact match first, then LIKE match.
8. `get_entity_by_qualified_name(conn, project, qualified_name)` → dict or None.
9. `get_relationships_for_entity(conn, entity_id, direction)` → list of dict. Direction: "outgoing" (source_id=?), "incoming" (target_id=?), "both". Join with entities table to include entity details.
10. `search_entities(conn, project, terms, entity_type, limit)` → list of dict. FTS5 search.
11. `file_needs_rescan(conn, project, file_path, current_hash)` → bool. Compare SHA256 hash with scan_state.
12. `update_scan_state(conn, project, file_path, file_hash, entity_count, parse_time_ms)` → None.
13. `get_stats(conn, project)` → dict. Entity count by type, total relationships, file count, last scan timestamp.

**Tests (12):** Schema creation, entity CRUD, relationship cascade deletes, FTS5 search, scan_state hash comparison, stats calculation, empty database.

---

### 5.3 ingest.py

**Purpose:** Parse git commit → memory.db.

**Functions to implement (6):**

1. `get_commit_info()` → dict or None. git log -1 with null separator (%H%x00%s%x00%ae%x00%aI). git branch --show-current. Return {hash, message, author, branch, timestamp} or None on failure.
2. `get_diff_stat()` → dict. git diff --name-only HEAD~1 → files list. git diff --stat HEAD~1 → summary string. Handle first commit (use --root). Handle merge commits.
3. `extract_modules(files_list)` → list of strings. Take first 2 directory components of each path, deduplicate, filter hidden dirs.
4. `detect_type(message, branch, files_list)` → tuple (type, decision_type_or_none). Priority: file signals (config files, new dirs, migrations, deletions) → branch signals (feat/, fix/, refactor/) → message keywords (decided, chose, blocker, blocked) → default "commit". Return tuple.
5. `extract_imports_from_diff()` → list of (source_file, imported_module). git diff HEAD~1 -U0, filter added lines (start with +), regex match Python and JS import patterns.
6. `run_ingest(project)` → dict summary. Orchestrates all above. Opens memory.db, inserts memory, updates file_pairs, inserts knowledge_graph edges (imports + module membership), returns {entries_added, type_detected}. Wrapped in try/except — never crashes.

**Tests (12):** Each function individually + full integration test (create test repo, commit, verify DB state). Error cases: non-git directory, empty diff, corrupted index.json.

---

### 5.4 sync.py

**Purpose:** memory.db → .ai-memory/CONTEXT.md.

**Functions to implement (7):**

1. `get_project_identity(conn, project)` → string. Query stacks table, git branch, author count (30 days). Format ~80 tokens.
2. `get_active_features(project_dir)` → list of dict. Scan features/ for active features (no Status in commit.md). Count AC checkboxes.
3. `get_guidelines_summary(project_dir)` → string. Read guidelines.md, extract first 3 rules per section, compress to 2-3 lines (~50 tokens).
4. `get_module_relationships(conn, project)` → string. Query temporal knowledge_graph for imports/changes-with predicates, group by module, format ~100 tokens.
5. `get_cross_project_insights(conn, project)` → list of dict. Query patterns table for matching stack_tags from other projects, top 3.
6. `get_wiki_summary(project_dir)` → string. Read .ai-wiki/wiki/INDEX.md if it exists, extract stats line (entity counts, test coverage). ~60 tokens.
7. `compile_context(project, project_dir)` → None. Orchestrates all above. Opens memory.db, calls get_ranked_context, assembles CONTEXT.md from template, applies token budget (trim bottom: cross-project → wiki summary → oldest recent → module map). Writes file. Updates surfaced_count. Also regenerates patterns.md.

**Tests (10):** Valid CONTEXT.md generation, token budget respected, decisions never truncated, empty database, missing index.json, feature reflection, wiki summary inclusion.

---

### 5.5 scan.py

**Purpose:** Source code → wiki.db + .ai-wiki/wiki/ pages.

**Functions to implement (4):**

1. `full_scan(project_dir, project)` → dict stats. Walk project tree, skip ignored paths (.git, node_modules, __pycache__, .venv, dist, build). Group files by extension. Dispatch to scan_python/scan_javascript/scan_sql/scan_generic. Insert all entities + relationships into wiki.db. Resolve name references to entity IDs (create "external" stubs for unresolvable imports). Update scan_state for every file. Call wiki_gen.generate_all(). Return stats.
2. `incremental_scan(project_dir, project, changed_files)` → dict stats. For each file: compute SHA256, check scan_state, skip if unchanged. For changed files: delete old entities, re-scan, insert new. For deleted files: delete entities + scan_state. Regenerate only affected wiki pages. Return stats.
3. `resolve_references(conn, project, entities, relationships)` → resolved relationships. Build name→id lookup from inserted entities. For unresolvable targets: create stub entity (type="external"). Return relationships with source_id and target_id populated.
4. `get_ignored_patterns()` → list of glob patterns. Default ignores + .ai-wiki-ignore file if it exists.

**Tests (8):** Full scan of test fixture project, incremental scan after file change, deleted file handling, external dependency stubs, ignore patterns, mixed-language project.

---

### 5.6 scan_python.py

**Purpose:** Python AST extraction using stdlib `ast` module.

**Functions to implement (5):**

1. `scan_file(file_path, project)` → tuple (entities, relationships). Parse with ast, walk tree, extract classes/functions/imports/constants. Handle SyntaxError gracefully (return empty).
2. `extract_class(node, file_path)` → entity dict. Name, bases, methods, decorators, docstring (first line), line range. Detect subtype: model (inherits Base/Model), schema (inherits BaseModel), service (in services/ dir), test (inherits TestCase), default class. For models: extract Column() definitions into metadata. For schemas: extract field annotations.
3. `extract_function(node, file_path)` → entity dict. Name, args with type hints (skip self/cls), return type, decorators, docstring, async flag. Build signature string. Detect endpoints from decorator patterns (@app.get, @router.post, etc.).
4. `extract_imports(node, file_path)` → list of relationship dicts. Handle ast.Import and ast.ImportFrom. Resolve relative imports against file path.
5. `build_qualified_name(file_path, entity_name)` → string. Convert file path to module path, append entity name.

**Tests (15):** Classes with inheritance detection (model vs schema vs class), FastAPI endpoint decorator parsing, SQLAlchemy Column extraction, Pydantic field extraction, async function signatures, type hints, relative imports, syntax errors, empty files, files with only comments.

---

### 5.7 scan_javascript.py

**Purpose:** JS/TS extraction using regex.

**Functions to implement (3):**

1. `scan_file(file_path, project)` → tuple (entities, relationships). Apply regex patterns to file content. Extract components, hooks, types, imports, API calls, page routes.
2. `extract_entity_from_match(match, pattern_name, file_path)` → entity dict. Map regex match to entity with correct entity_type and metadata.
3. `detect_page_route(file_path)` → string or None. For Next.js: pages/about.tsx → "/about". For app router: app/dashboard/page.tsx → "/dashboard".

**Tests (12):** React function components, arrow components, custom hooks, TypeScript interfaces with fields, API calls (fetch, axios, useSWR), ES6 imports, require imports, Next.js page detection, JSX child detection, Vue/Svelte files.

---

### 5.8 scan_sql.py

**Purpose:** SQL and migration extraction using regex.

**Functions to implement (2):**

1. `scan_file(file_path, project)` → tuple (entities, relationships). Detect file type (raw SQL, Alembic, Django migration). Parse accordingly.
2. `parse_create_table(sql_content, file_path)` → entity dict. Extract table name, columns with types/constraints, PKs, FKs, indexes.

**Tests (8):** CREATE TABLE, ALTER TABLE, foreign keys, indexes, Alembic op.create_table, multi-statement files, IF NOT EXISTS handling.

---

### 5.9 scan_generic.py

**Purpose:** Language-agnostic structure and config extraction.

**Functions to implement (3):**

1. `scan_project_structure(project_dir, project)` → tuple (entities, relationships). Walk tree, create module entities, detect layers, map tests to source.
2. `scan_config_files(project_dir, project)` → tuple (entities, relationships). Parse package.json/requirements.txt/env files/docker-compose.
3. `map_test_to_source(project_dir)` → list of (source_path, test_path). Match by naming convention (src/auth.py → tests/test_auth.py).

**Tests (8):** Directory structure, layer detection, test mapping, config parsing, missing files, monorepo structure.

---

### 5.10 wiki_gen.py

**Purpose:** wiki.db → .ai-wiki/wiki/ markdown pages.

**Functions to implement (10):**

1. `generate_all(conn, project, wiki_dir)` → list of paths. Create directory structure, call each page generator, generate INDEX.md last.
2. `generate_index(conn, project, wiki_dir, page_stats)` → path. Stats, section links, architecture flow summary.
3. `generate_architecture(conn, project, wiki_dir)` → path. Layer analysis, depth check, circular dependency check.
4. `generate_endpoints(conn, project, wiki_dir)` → path. All endpoints grouped by domain, with full call chain.
5. `generate_models(conn, project, wiki_dir)` → path. All models with columns, types, constraints.
6. `generate_model_relationships(conn, project, wiki_dir)` → path. FK map between models.
7. `generate_services(conn, project, wiki_dir)` → path. Services with methods, dependencies, dependents.
8. `generate_database(conn, project, wiki_dir)` → path. Full table schema from model metadata + migrations.
9. `generate_components(conn, project, wiki_dir)` → path. Component tree, hooks, pages. Skip if no components detected.
10. `generate_coverage_map(conn, project, wiki_dir)` → path. Source → test mapping, highlight gaps.

Each function follows the same pattern: query wiki.db → loop → format with template → write file.

**Tests (10):** Each generator with sample data + empty data handling + cross-page link validation.

---

### 5.11 blast_radius.py

**Purpose:** Impact analysis from changed files.

**Functions to implement (3):**

1. `get_blast_radius(conn, project, changed_files, max_depth)` → dict. Find entities in changed files, BFS through relationships (imports, calls, inherits, depends_on), collect impacted entities at each depth, find test files via tested_by edges. Handle cycles (visited set). Return {direct_impact, indirect_impact, test_impact, total_files}.
2. `format_blast_radius_md(blast_result, project)` → string. Markdown report grouped by depth, with file paths and entity names.
3. `get_risk_factors(blast_result, changed_files)` → list of strings. Check: auth/payment/security paths, test gaps in impacted files, config file changes.

**Tests (8):** Direct dependents, transitive dependents (2-hop), test coverage, circular dependency handling, isolated files, risk factor detection.

---

### 5.12 remaining scripts

**feature_init.py (2 functions):** create_feature, create_fix. Counter increment, template generation, plan.md context embedding.
**Tests (6).**

**feature_close.py (2 functions):** detect_feature_close (from diff file list), close_feature (decision extraction, anti-pattern extraction, memory.db entry, knowledge_graph update, auto-fill dates).
**Tests (6).**

**review.py (6 functions):** get_changes_since_main, check_pattern_compliance, check_decision_compliance, check_guideline_compliance, calculate_risk_score, generate_review.
**Tests (10).**

**lint.py (8 check functions + 1 runner):** contradicting decisions, stale decisions, broken patterns, orphan features, unresolved blockers, missing tests, dead code (no callers in wiki.db), circular dependencies (from wiki.db relationships). run_lint generates lint-report.md.
**Tests (9).**

**guidelines_check.py (4 functions):** check_missing_tests, check_wrong_layer_imports, check_hardcoded_values, check_logging_patterns.
**Tests (6).**

**detect.py (3 functions):** detect_stack, detect_ides, detect_monorepo.
**Tests (8).**

**backfill.py (2 functions):** backfill_history (walks git log, deduplicates, smart limits), build_initial_file_pairs (co-occurrence from history).
**Tests (6).**

**pointers.py (2 functions):** generate_all_pointers (creates all 7 IDE files), generate_pointer_content (builds the universal content block).
**Tests (4).**

**pr_context.py (1 function):** generate_pr_description (reads review.md, formats as PR-ready markdown).
**Tests (3).**

**aggregate.py (2 functions):** generate_sprint_summary (queries across projects within date range), export_sprint_md (formats as markdown).
**Tests (4).**

**migrate.py (2 functions):** migrate_memory_db (schema versioning for memory.db), migrate_wiki_db (schema versioning for wiki.db).
**Tests (4).**

**utils.py (5 functions):** timestamp_scratch_notes, slugify, estimate_tokens, read_json, write_json, get_project_slug.
**Tests (5).**

---

## 6. Hooks — exact behaviour

### post-commit (fires after every git commit)

```
1. Check AI_MEMORY_RUNNING env var → exit if "1" (recursion guard)
2. Set AI_MEMORY_RUNNING=1
3. Find PYTHON executable (python3 or python)
4. Find AI_MEMORY_HOME (~/.ai-memory-system or AI_MEMORY_HOME env var)
5. Call: ingest.py → silent, never blocks
6. Call: sync.py → silent, never blocks
7. Call: scan.py --incremental → silent, never blocks
8. Call: feature_close.py → silent, never blocks
9. Exit 0 (always)
```

### pre-commit (fires before every commit)

```
1. Check recursion guard
2. Call: utils.py timestamp-scratch → timestamps un-timestamped
   lines in active feature scratch.md files, stages the file
3. Exit 0 (always)
```

### pre-push (fires before git push)

```
1. Check recursion guard
2. Call: review.py → generates review.md + prints terminal summary
3. Call: pr_context.py → generates pr-description.md
4. Exit 0 (always — advisory only)
```

### post-merge (fires after git pull/merge)

```
1. Check recursion guard
2. Call: sync.py → regenerate CONTEXT.md from merged state
3. Call: scan.py --incremental → re-scan files changed in merge
4. Exit 0 (always)
```

---

## 7. Test summary

```
MODULE                    TESTS    WHAT THEY COVER
────────────────────────  ───────  ────────────────────────────────
test_db_memory.py          15     Schema, CRUD, FTS5, relevance, pairs
test_db_wiki.py            12     Schema, entities, relationships, BFS, FTS5
test_ingest.py             12     Commit parsing, type detection, imports
test_sync.py               10     CONTEXT.md generation, budget, ranking
test_scan_python.py        15     AST: classes, functions, endpoints, models
test_scan_javascript.py    12     Regex: components, hooks, props, API calls
test_scan_sql.py            8     SQL parsing: tables, columns, FKs
test_scan_generic.py        8     Structure, config, test mapping
test_wiki_gen.py           10     Each page generator + empty data
test_blast_radius.py        8     BFS, depth limits, cycles, test coverage
test_detect.py              8     Stack, IDE, monorepo detection
test_backfill.py            6     History import, dedup, smart limits
test_feature.py            12     Create/close features, decisions, AC tracking
test_review.py             10     Compliance checks, risk scoring, report
test_lint.py                9     Each lint check, report generation
test_guidelines.py          6     Regex checks for naming, imports, secrets
test_utils.py               5     Timestamp, slugify, tokens, JSON I/O

TOTAL                     ~166 tests
```

---

## 8. Implementation sequence (day by day)

```
DAY    WHAT                                    PASS CRITERIA
─────  ──────────────────────────────────────  ─────────────────────────────
  1    db_memory.py + test_db_memory.py         15 tests pass
       db_wiki.py + test_db_wiki.py             12 tests pass
       conftest.py + test fixtures

  2    ingest.py + test_ingest.py               12 tests pass
       utils.py + test_utils.py                  5 tests pass

  3    sync.py + test_sync.py                   10 tests pass
       Templates: context.md, pointer.md

  4    scan_python.py + test_scan_python.py     15 tests pass
       fixtures/python_sample/ (mini FastAPI project)

  5    scan_javascript.py + test_scan_js.py     12 tests pass
       fixtures/javascript_sample/ (mini React project)
       scan_sql.py + test_scan_sql.py            8 tests pass
       scan_generic.py + test_scan_generic.py    8 tests pass

  6    scan.py (orchestrator + incremental)     Integrated with Day 4-5
       wiki_gen.py + test_wiki_gen.py           10 tests pass
       Wiki templates (INDEX, architecture,
       endpoints, models, services, database,
       components, coverage)

  7    blast_radius.py + test_blast_radius.py    8 tests pass
       detect.py + test_detect.py                8 tests pass
       backfill.py + test_backfill.py            6 tests pass

  8    feature_init.py + feature_close.py       12 tests pass (test_feature)
       Feature templates (feature, fix, plan,
       scratch, test, commit)

  9    review.py + test_review.py               10 tests pass
       guidelines_check.py + test_guidelines.py  6 tests pass
       pr_context.py (3 tests)
       Guidelines templates (python, ts, general)

 10    lint.py + test_lint.py                    9 tests pass
       pointers.py (4 tests)
       Skill files (10 markdown files)
       Hooks (4 shell scripts)
       .gitattributes template

 11    setup.py (integrates everything)          Integration test passes:
       aggregate.py (4 tests)                    clone repo → setup →
       migrate.py (4 tests)                      commit → verify CONTEXT.md
                                                 + wiki pages + memory.db

 12    End-to-end integration test:              Full pipeline:
       Create new project → setup → feature →    project → feature → plan →
       commits → test → review → push → close    implement → test → review →
       → verify entire chain works.              push → close → verify
       README.md + AI-MEMORY-README.md           All ~166 tests pass.
       Windows compatibility check.
       Performance test: 500-file project
       scans in <15 seconds.
```

---

## 9. What ai-architect reads (for reference)

ai-architect (separate tool) does NOT modify any repo. It reads:

**From .ai-memory/ (committed):**
- CONTEXT.md — project identity, decisions, patterns, recent activity
- project/decisions.md — full decision log
- project/guidelines.md — coding standards
- project/architecture.md — intended architecture
- features/ — feature lifecycle data

**From .ai-wiki/ (committed):**
- wiki/INDEX.md — structural overview + stats
- wiki/api/endpoints.md — all endpoints with call chains
- wiki/services/dependency-graph.md — service dependencies
- wiki/models/overview.md — all models with columns
- wiki/database/tables.md — full database schema
- wiki/tests/coverage-map.md — test coverage gaps

**From ~/.ai-memory/ (local):**
- memory.db — for FTS5 search across all projects
- wiki/{project}.db — for graph traversal + blast radius queries
- projects.json — for project discovery

ai-architect provides: Streamlit UI, graph visualization, cross-repo
analysis, LLM-powered chat interface, architecture drift detection.
That is a separate implementation plan.
