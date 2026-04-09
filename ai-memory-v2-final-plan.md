# ai-memory v2 — Final Plan of Action
## IDE-agnostic. Plugin-free. Restricted-environment ready.

---

## 1. The core constraint and how we solve it

### The constraint
No marketplace. No plugins. No npm/pip beyond stdlib. No external APIs.
Must work in: Claude Code, VS Code + Copilot, Cursor, Codex CLI,
Windsurf, JetBrains + AI Assistant, Vim + Copilot, even Notepad
with a terminal. Also: air-gapped corporate laptops, bank dev
environments, government contractor machines.

### The insight
Every AI-powered IDE has ONE thing in common: it reads files from
the file system. Not plugins. Not APIs. Files.

```
IDE                 NATIVE FILE IT READS              HOW IT READS IT
──────────────────  ────────────────────────────────  ─────────────────
Claude Code         CLAUDE.md (walks up dir tree)     Auto on every session
Cursor              .cursorrules, .cursor/rules/*.mdc  Auto on every session
VS Code + Copilot   .github/copilot-instructions.md   Auto on code gen
Codex CLI           AGENTS.md                          Auto on every session
Windsurf            .windsurfrules                     Auto on every session
JetBrains + AI      .junie/guidelines.md               Auto on every session
Gemini CLI          GEMINI.md                          Auto on every session
Any IDE             README.md, any .md file            When opened/referenced
```

**The strategy:** We don't integrate with IDEs. We place files where
IDEs already look. The IDE does the integration for us.

### The two universal mechanisms

**Mechanism 1: Native file placement**
Every AI IDE reads at least one convention file. We generate all of them.
Each is a thin pointer (2-5 lines) that tells the AI to read CONTEXT.md.
Cost: ~50 tokens per pointer. Total across all IDEs: ~350 tokens.

**Mechanism 2: Git hooks**
Git hooks are shell scripts in `.git/hooks/`. They run on every git
operation regardless of which IDE, terminal, or OS is being used.
They need no installation beyond `chmod +x`. They call Python scripts
that use only stdlib modules. They work on Windows, macOS, Linux.
They work in Docker containers, CI runners, and air-gapped machines.

These two mechanisms — files the IDE reads + hooks that git triggers —
give us full SDLC coverage without touching any IDE's plugin system.

---

## 2. How "skills" work without a marketplace

### The problem with marketplace skills
Claude Code skills live in `~/.claude/skills/`. Cursor rules live in
`.cursor/rules/`. Each IDE has a different path, format, and loading
mechanism. In restricted environments, you can't install marketplace
plugins, you can't write to `~/.claude/` (it may not exist), and
you may not have the IDE's CLI tool to register skills.

### The solution: skills as referenced markdown files

A "skill" in ai-memory is a markdown file in `.ai-memory/skills/`
that the pointer file tells the AI to read on demand.

**How it works:**

```markdown
# CLAUDE.md (the pointer file)

## Session directives
- Short sentences. 8-10 words max.
- No filler. No preamble. Tool-first.
- Read .ai-memory/CONTEXT.md before every task.
- Respect decisions. Reference by [date].

## Available skills (read on demand)
When asked to review code → read .ai-memory/skills/review.md
When asked about guidelines → read .ai-memory/skills/guidelines.md
When asked to create a spec → read .ai-memory/skills/spec.md
When asked for help with code → read .ai-memory/skills/help.md
When starting a new feature → read .ai-memory/skills/feature.md
```

**Why this works everywhere:**
- The AI reads CLAUDE.md at session start
- It sees "when asked about X, read file Y"
- When the developer asks about X, the AI reads Y
- No plugin system needed — just file reading
- Works identically in Cursor (via .cursorrules), Codex (via AGENTS.md), etc.

**The skill files themselves are IDE-agnostic markdown:**

```markdown
<!-- .ai-memory/skills/review.md -->
# Code review skill

## When to activate
Developer says: review, check, pre-push, PR, pull request, code quality

## What to do
1. Read .ai-memory/CONTEXT.md for project context
2. Read .ai-memory/guidelines.md for coding standards
3. Run: git diff --cached --stat (or git diff main...HEAD)
4. For each changed file:
   a. Check if paired file exists (from patterns in CONTEXT.md)
   b. Check naming conventions match guidelines
   c. Check for anti-patterns listed in CONTEXT.md
5. Generate review summary with:
   - Files changed and modules touched
   - Decisions relevant to these changes
   - Pattern compliance (paired files present?)
   - Guideline violations found
   - Risk assessment (auth/payment/config = high risk)

## Output format
Use this template:
### Review: [branch name]
**Risk:** LOW | MEDIUM | HIGH
**Changes:** N files across M modules
**Decisions referenced:** [list]
**Issues:** [list or "none found"]
**Recommendation:** [ship / address issues first]
```

**This markdown skill works in Claude Code, Cursor, Codex, Windsurf,
JetBrains, Gemini CLI — any tool that can read a file when instructed.**

### Skills inventory

```
SKILL FILE                          TRIGGER PHRASES              PURPOSE
──────────────────────────────────  ───────────────────────────  ──────────────────────
.ai-memory/skills/review.md        review, check, PR, quality   Pre-push code review
.ai-memory/skills/guidelines.md    guidelines, standards, rules  Show/check coding rules
.ai-memory/skills/spec.md          spec, requirement, feature    Create feature spec
.ai-memory/skills/help.md          help, how do I, show me       Contextual dev assistance
.ai-memory/skills/feature.md       new feature, implement, add   Feature implementation guide
.ai-memory/skills/debug.md         bug, fix, error, failing      Debug with project context
.ai-memory/skills/onboard.md       onboard, new, getting started New developer guide
.ai-memory/skills/sprint.md        sprint, summary, retro        Sprint summary generation
```

Each skill is a standalone markdown file that references CONTEXT.md
and other .ai-memory/ files. No imports. No dependencies. No registry.

---

## 3. How hooks work without IDE integration

### Git hooks are the universal automation layer

```
HOOK              WHEN IT FIRES              WHAT IT DOES
────────────────  ─────────────────────────  ────────────────────────────────
post-commit       After every git commit      1. Ingest commit into memory.db
                                              2. Update CONTEXT.md
                                              3. Update daily log

pre-push          Before git push             1. Generate review.md
                                              2. Run guidelines check
                                              3. Generate pr-description.md
                                              4. Print advisory warnings

post-merge        After git pull/merge        1. Refresh CONTEXT.md from DB
                                              2. Rebuild patterns if needed

pre-commit        Before git commit           1. Pattern compliance warning
                  (advisory — never blocks)    2. Missing test file warning
                                              3. Guideline quick-check
```

### Hook architecture (cross-platform)

Each hook is a thin shell script that calls a Python script.
The Python script uses only stdlib modules.

```bash
#!/bin/sh
# .git/hooks/post-commit
# Works on: Linux, macOS, Windows (Git Bash), Docker, CI runners

MEMORY_HOME="${HOME}/.ai-memory-system"
PYTHON=$(command -v python3 || command -v python)

# Silent execution — never blocks the commit
"$PYTHON" "$MEMORY_HOME/scripts/ingest.py" 2>/dev/null || true
"$PYTHON" "$MEMORY_HOME/scripts/sync.py" 2>/dev/null || true
```

**Critical design decisions:**
- `|| true` ensures hooks NEVER block git operations
- `2>/dev/null` suppresses errors — developer sees nothing
- Hooks auto-detect Python path (works on any system)
- If Python is missing, hook silently does nothing
- If memory_home doesn't exist, hook silently does nothing
- ZERO chance of breaking the developer's workflow

### Windows compatibility

Git on Windows runs hooks through Git Bash (MINGW). The sh
shebang works. Python path detection works. `$HOME` maps to
`%USERPROFILE%`. No PowerShell needed for hooks.

For the `setup.py` command itself, the developer runs it from
any terminal (cmd, PowerShell, Git Bash) — Python stdlib handles
path differences via `pathlib.Path`.

---

## 4. Pointer file generation — complete coverage

### The universal generator

`pointers.py` generates ALL IDE-specific files from a single template.
Each file is 5-15 lines. Each points to CONTEXT.md. Each includes
the skill routing table. Each includes session directives.

The generator runs once during `setup.py` and is idempotent — safe
to run again without data loss.

### Complete pointer file map

```
FILE                              IDE                    LOADED
────────────────────────────────  ─────────────────────  ────────────────
CLAUDE.md                         Claude Code             Every session
.cursorrules                      Cursor                  Every session
AGENTS.md                         Codex CLI, OpenClaw     Every session
.windsurfrules                    Windsurf (Codeium)      Every session
GEMINI.md                         Gemini CLI              Every session
.github/copilot-instructions.md   VS Code + Copilot       Every code gen
.junie/guidelines.md              JetBrains + Junie        Every session
.ai-memory/CONTEXT.md             ALL (via pointer refs)   On demand
```

### Pointer file template (same content, different filename)

```markdown
# Session directives
- Short sentences. 8-10 words max.
- No filler. No preamble. Tool-first.
- Read .ai-memory/CONTEXT.md before every task.
- Respect existing decisions. Reference by [date].
- Check blockers before suggesting workarounds.
- Follow .ai-memory/guidelines.md for coding standards.

# Skills (read the file when the topic comes up)
- Code review → .ai-memory/skills/review.md
- Coding guidelines → .ai-memory/skills/guidelines.md
- Feature spec → .ai-memory/skills/spec.md
- Dev help → .ai-memory/skills/help.md
- Debugging → .ai-memory/skills/debug.md
- New developer → .ai-memory/skills/onboard.md

# Project context
Read .ai-memory/CONTEXT.md for decisions, patterns, blockers, and history.
```

Token cost per pointer: ~120 tokens. Loaded once per session.
CONTEXT.md: ~1,500 tokens. Total ambient cost: ~1,620 tokens.

### IDE detection during setup (informational only)

```python
# detect.py — tells the developer what was generated
def detect_ides():
    found = []
    if path_exists(".vscode/"):
        found.append("VS Code")
    if path_exists(".cursor/"):
        found.append("Cursor")
    if path_exists(".claude/"):
        found.append("Claude Code")
    if path_exists(".idea/"):
        found.append("JetBrains")
    # Always generate ALL pointer files regardless
    return found

# Output during setup:
# "Detected: VS Code, Claude Code
#  Generated pointer files for: ALL IDEs (7 files)
#  Your IDE will pick up the relevant file automatically."
```

**Key principle:** Generate ALL pointer files always. The ones that
aren't relevant are ignored by the IDE (it only reads its own file).
The overhead is 7 small files totaling ~2KB. Negligible.

---

## 5. The restricted environment checklist

### What ai-memory needs to run

```
REQUIREMENT          AVAILABLE IN RESTRICTED ENV?    FALLBACK
───────────────────  ─────────────────────────────  ─────────────
Python 3.8+          Yes (most corp environments)    Script as .py files
sqlite3 module       Yes (Python stdlib)             None needed
subprocess module    Yes (Python stdlib)             None needed
pathlib module       Yes (Python stdlib)             None needed
json module          Yes (Python stdlib)             None needed
Git                  Yes (if they're coding)         Required
File system write    Yes (to project directory)      Required
~/.ai-memory/ write  Yes (home directory)            Configurable path
```

### What ai-memory does NOT need

```
NOT REQUIRED                   WHY
────────────────────────────  ────────────────────────────────────
Internet access                Everything is local
pip install                    No external packages
npm / node                     Not used
Docker                         Not used
API keys                       No external services
IDE plugins                    File-based integration only
Admin/root access              Writes to home + project dirs only
Specific IDE                   Works with any editor + terminal
Specific OS                    Python + Git = cross-platform
MCP servers                    Not used
LLM at write-time              Zero inference cost on commit
```

### Air-gapped deployment

```bash
# On a machine with internet:
git clone https://github.com/Az3RoS/ai-memory
zip -r ai-memory.zip ai-memory/

# Transfer ai-memory.zip to the restricted machine via approved channel

# On the restricted machine:
unzip ai-memory.zip -d ~/.ai-memory-system
cd ~/your-project
python ~/.ai-memory-system/setup.py

# Done. No internet needed from this point forward.
```

### Corporate proxy / firewall scenarios

ai-memory never makes network calls. It reads files and runs git
commands. If git works on the machine, ai-memory works.

---

## 6. Multi-project, multi-team — complete scenarios

### Scenario A: Single developer, multiple projects

```
Developer machine:
~/.ai-memory/
├── memory.db              # Contains: signal (247), trading (189), health (94)
├── config.json            # Developer preferences
└── projects.json          # Registry with paths

~/signal/.ai-memory/CONTEXT.md          # Signal's context
~/trading/.ai-memory/CONTEXT.md         # Trading app's context
~/health-api/.ai-memory/CONTEXT.md      # Health API's context
```

Cross-project patterns surface automatically:
- Developer hits async SQLAlchemy bug in health-api
- memory.db shows signal had the same pattern + resolution
- CONTEXT.md for health-api includes: "[from signal] async sessions need explicit close()"

### Scenario B: Team of 5 on same repo

```
How memory flows between developers:

Dev A commits → post-commit hook:
  1. Ingest to Dev A's local memory.db
  2. Update .ai-memory/CONTEXT.md
  3. Update .ai-memory/decisions.md (if decision detected)
  4. git add .ai-memory/ is manual or via hook

Dev A pushes → pre-push hook:
  1. Generate review.md (not committed)
  2. Advisory warnings printed to terminal

Dev B pulls:
  1. Gets updated CONTEXT.md, decisions.md
  2. post-merge hook triggers sync.py
  3. Dev B's local memory.db updates from git log
  4. Dev B's CONTEXT.md regenerates (merges local + pulled data)

Dev C who never installed ai-memory:
  1. Pulls → gets .ai-memory/ files
  2. Their IDE reads CLAUDE.md or .cursorrules (pointer file)
  3. Pointer says "read .ai-memory/CONTEXT.md"
  4. Dev C gets full project context without any setup
  5. ONLY thing missing: their commits don't auto-ingest
     (no hooks installed until they run setup.py)
```

### Scenario C: Existing project with 1000+ commits

```
Day 1: Developer runs python setup.py

setup.py detects:
  - Git repo: yes
  - Existing commits: 1,247
  - Existing .ai-memory/: no
  - Stack: Python 3.11, FastAPI, SQLAlchemy, pytest

setup.py executes:
  1. Creates .ai-memory/ structure
  2. Generates pointer files (ALL IDEs)
  3. Installs git hooks
  4. Runs backfill:
     - Scans last 200 commits fully (diff, files, branches)
     - Scans ALL commit messages for decision keywords
     - Builds file_pairs from co-occurrence data
     - Detects patterns from repeated pairings
  5. Generates CONTEXT.md with:
     - Detected stack
     - Decisions found in history
     - File patterns detected
     - Recent activity (last 2 weeks)
  6. Generates guidelines.md (starter template based on stack)
  7. Prints: "Imported 200 commits, found 14 decisions, detected 8 patterns"

Time elapsed: 15-30 seconds
Developer effort: one command
```

### Scenario D: Sprint spanning multiple teams

```
Team Alpha: signal, dashboard-ui (3 devs)
Team Beta: trading-app, market-data (4 devs)

Sprint 2026-W15 summary (generated by any team lead):

  memory sprint --projects signal,dashboard-ui,trading-app,market-data \
                --start 2026-04-01 --end 2026-04-14

This queries the local memory.db which has data for all projects
the developer's machine has set up. If a project is missing:

  "⚠ market-data not found in local memory. Run setup.py in that repo,
   or ask a team member to share their sprint data."

Sharing sprint data between developers who have different projects:

  # Dev A generates signal + dashboard-ui summary
  memory sprint export --projects signal,dashboard-ui > alpha-sprint.md

  # Dev B generates trading-app + market-data summary
  memory sprint export --projects trading-app,market-data > beta-sprint.md

  # Team lead combines (or anyone merges the markdown files)
  cat alpha-sprint.md beta-sprint.md > sprint-2026-W15.md

No shared database needed. Export is markdown. Merge is concatenation.
```

### Scenario E: New developer joins mid-project

```
Day 1:
  git clone <repo>
  cd <repo>
  python ~/.ai-memory-system/setup.py

What happens:
  1. .ai-memory/CONTEXT.md already exists (committed by team)
  2. setup.py sees existing .ai-memory/ → "Existing project detected"
  3. Installs hooks for this developer's future commits
  4. Backfills history into personal memory.db
  5. CONTEXT.md already has: decisions, patterns, blockers, stack

What the new dev sees immediately (from CONTEXT.md):
  - "Stack: Python 3.11 / FastAPI / async SQLAlchemy / SQLite"
  - "Decision [04-05]: Chose async SQLAlchemy over raw sqlite3"
  - "Pattern: auth changes always paired with test_auth.py"
  - "Blocker: async session lifecycle causes test flakes"
  - "Anti-pattern: don't import models in routes, use services"

Time to productivity: minutes instead of days.
No onboarding meeting needed for technical context.
```

### Scenario F: Developer leaves the team

```
What stays behind (committed to git):
  .ai-memory/CONTEXT.md        — full project context
  .ai-memory/decisions.md      — all architecture decisions with author
  .ai-memory/patterns.md       — detected file patterns
  .ai-memory/guidelines.md     — coding standards
  .ai-memory/specs/completed/  — all completed feature specs

What leaves with the developer:
  ~/.ai-memory/memory.db        — their personal search index

Impact: ZERO knowledge loss.
The decision log survives. The patterns survive. The context survives.
The only thing lost is the developer's personal FTS5 search speed —
and any new developer rebuilds that with setup.py --rebuild.
```

### Scenario G: Monorepo with multiple services

```
company-monorepo/
├── services/
│   ├── auth/
│   │   └── .ai-memory/          # Auth service context
│   │       ├── CONTEXT.md
│   │       └── index.json       # scope: services/auth/**
│   ├── billing/
│   │   └── .ai-memory/          # Billing service context
│   │       ├── CONTEXT.md
│   │       └── index.json       # scope: services/billing/**
│   └── gateway/
│       └── .ai-memory/          # Gateway context
│           ├── CONTEXT.md
│           └── index.json       # scope: services/gateway/**
├── libs/
│   └── shared/
│       └── .ai-memory/          # Shared libs context
├── .ai-memory/                   # Root-level: cross-service decisions
│   ├── CONTEXT.md               # Overall architecture context
│   ├── decisions.md             # Cross-service decisions
│   └── index.json               # mode: monorepo
├── CLAUDE.md                     # Root pointer (reads root CONTEXT.md)
└── .cursorrules                  # Root pointer

When developer edits services/auth/handler.py:
  - post-commit detects scope from file path
  - Ingests into memory.db with project = "monorepo/auth"
  - Updates services/auth/.ai-memory/CONTEXT.md
  - Also updates root .ai-memory/CONTEXT.md if cross-service decision

When IDE opens services/auth/:
  - Claude Code walks up, finds services/auth/.ai-memory/ first
  - Then finds root .ai-memory/ — both contexts loaded
  - Cursor reads root .cursorrules → pointed to root CONTEXT.md
  - Developer gets both service-specific and cross-service context
```

### Scenario H: CI/CD — no local dev machine

```
GitHub Actions workflow:

on:
  push:
    branches: [main]

jobs:
  memory:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 50

      - run: |
          python scripts/ingest.py --ci
          python scripts/sync.py
          python scripts/review.py --ci > .ai-memory/review.md

      - run: |
          git add .ai-memory/
          git diff --staged --quiet || \
            git commit -m "chore(memory): sync [skip ci]" && \
            git push

The --ci flag:
  - Creates temporary memory.db (not persisted)
  - Skips hook installation
  - Skips cross-project patterns (CI sees one repo)
  - Generates CONTEXT.md from recent commits only
  - Review.md becomes part of the committed .ai-memory/

Result: even repos where NO developer has installed ai-memory
locally can have auto-generated CONTEXT.md from CI.
```

---

## 7. CONTEXT.md — the final structure

```markdown
<!-- AUTO-GENERATED by ai-memory v2. Do not edit manually. -->
<!-- Project: signal | Budget: 2000 tokens | Sync: 2026-04-09T14:30Z -->
<!-- Contributors: arnab@tcs.com, dev-b@tcs.com, dev-c@tcs.com -->

## Identity
Stack: Python 3.11 / FastAPI / async SQLAlchemy / SQLite / pytest
Repo: signal-news-agent | Branch: feat/multi-provider-llm
Team: 3 contributors (30 days) | Commits: 247 total, 34 this sprint

## Guidelines (→ .ai-memory/guidelines.md for full rules)
snake_case fns, PascalCase classes. Routes thin: validate→service→respond.
No global state. No print()→use logger. Mock externals in tests.
Services in src/services/, models in src/models/. No cross-layer imports.

## Active specs (→ .ai-memory/specs/active/)
- Gemini provider: 4/6 criteria met (timeout, fallback remaining)

## Decisions (permanent — never truncated)
- [04-08] arnab: LLM provider Groq → Gemini (cost reduction)
- [04-05] dev-b: async SQLAlchemy over raw sqlite3 (pooling)
- [04-01] arnab: PWA over native — browser-first strategy
- [03-28] arnab: 7-category news pipeline (not 3 as originally planned)

## Blockers (active)
- Async session lifecycle → test flakes (since 04-07, affects: tests/)
- Gemini rate limiting not implemented (since 04-08, affects: providers/)

## Patterns (auto-detected from history)
- auth changes → always pair: src/auth/*.py + tests/test_auth.py
- provider changes → always pair: src/providers/*.py + config/settings.py
- model changes → always pair: src/models/*.py + alembic/versions/*.py
- dashboard changes → always pair: src/ui/*.py + static/css/*.css

## Anti-patterns (learned from past mistakes)
- Don't import models in routes → use services layer
- Don't create sync functions → everything async
- SQLAlchemy: always `async with session_maker()`, never raw session
- Don't hardcode timeouts → use settings.PROVIDER_TIMEOUT

## Recent activity (14 days, all contributors)
- [04-09] arnab: fix(providers) Gemini timeout handling
- [04-09] dev-c: feat(dashboard) theme switcher, 3 themes
- [04-08] dev-b: refactor(db) async SQLAlchemy migration
- [04-07] arnab: test(auth) JWT expiry edge cases
- [04-06] dev-c: fix(ui) dark mode contrast issues
- [04-05] dev-b: feat(models) add async session factory

## Module map
src/api/        → FastAPI routes (thin controllers)
src/agents/     → News analysis pipeline (7 agents)
src/providers/  → LLM abstraction (Groq, Gemini)
src/models/     → SQLAlchemy models (User, Article, Source)
src/services/   → Business logic layer
tests/          → pytest, async fixtures, mocked externals

## Cross-project insights
- [trading-app] FastAPI async sessions need explicit close()
- [health-api] SQLite WAL mode prevents write locks in tests
```

---

## 8. Complete file inventory

### What ships in the ai-memory repo (the tool)

```
ai-memory/                               PURPOSE
├── setup.py                              One-command installer
├── scripts/
│   ├── memory_cli.py                     CLI router (init|ingest|query|sync|status|sprint)
│   ├── ingest.py                         Parse git diff + branch + files → memory.db
│   ├── sync.py                           Generate CONTEXT.md from memory.db
│   ├── detect.py                         Auto-detect stack, IDE, monorepo
│   ├── pointers.py                       Generate ALL IDE pointer files
│   ├── backfill.py                       Import existing git history
│   ├── migrate.py                        Schema migration (v1 → v2)
│   ├── aggregate.py                      Sprint summaries, cross-project
│   ├── review.py                         Pre-push review context
│   ├── guidelines_check.py               Coding standards compliance
│   ├── spec_track.py                     Spec → implementation tracking
│   └── pr_context.py                     PR description generator
├── hooks/
│   ├── post-commit                       ingest + sync (silent)
│   ├── pre-push                          review + guidelines (advisory)
│   ├── post-merge                        context refresh
│   └── pre-commit                        pattern warning (advisory)
├── templates/
│   ├── CONTEXT.md.template               Structure for generated context
│   ├── guidelines.md.template            Starter coding standards (per stack)
│   ├── guidelines-python.md.template     Python-specific standards
│   ├── guidelines-typescript.md.template  TypeScript-specific standards
│   ├── spec.md.template                  Feature specification template
│   ├── pointer.md.template               Universal pointer content
│   └── gitattributes.template            Merge strategy for auto-gen files
├── skills/
│   ├── review.md                         Code review instructions
│   ├── guidelines.md                     Guidelines check instructions
│   ├── spec.md                           Spec creation instructions
│   ├── help.md                           Contextual dev assistance
│   ├── feature.md                        Feature implementation guide
│   ├── debug.md                          Debug with project context
│   ├── onboard.md                        New developer orientation
│   └── sprint.md                         Sprint summary generation
├── README.md                             Project overview
└── AI-MEMORY-README.md                   Developer guide (step-by-step)

Total: 31 files. All Python stdlib. All markdown.
```

### What gets created per repo

```
your-project/                             PURPOSE
├── .ai-memory/                            COMMITTED (team-shared)
│   ├── CONTEXT.md                         ★ Universal context (all IDEs)
│   ├── index.json                         Project config + metadata
│   ├── stack.json                         Auto-detected tech stack
│   ├── decisions.md                       Architecture Decision Log
│   ├── patterns.md                        Auto-detected file patterns
│   ├── guidelines.md                      Coding standards (editable)
│   ├── antipatterns.md                    Known pitfalls (auto + manual)
│   ├── skills/                            Skill files (copied from tool)
│   │   ├── review.md
│   │   ├── guidelines.md
│   │   ├── spec.md
│   │   ├── help.md
│   │   ├── feature.md
│   │   ├── debug.md
│   │   ├── onboard.md
│   │   └── sprint.md
│   ├── specs/                             Feature specifications
│   │   ├── active/                        In-progress specs
│   │   └── completed/                     Done (become decision records)
│   └── .gitattributes                     merge=ours for auto-gen files
│
├── CLAUDE.md                              Pointer (Claude Code)
├── .cursorrules                           Pointer (Cursor)
├── AGENTS.md                              Pointer (Codex CLI, OpenClaw)
├── .windsurfrules                         Pointer (Windsurf)
├── GEMINI.md                              Pointer (Gemini CLI)
├── .github/
│   └── copilot-instructions.md            Pointer (VS Code + Copilot)
├── .junie/
│   └── guidelines.md                      Pointer (JetBrains)
└── .vscode/
    └── tasks.json                         VS Code shortcuts (optional)

Total per-repo: ~25 files. All committed. All markdown/json.
```

### Global store (per developer, never committed)

```
~/.ai-memory/                              PURPOSE
├── memory.db                              SQLite + FTS5 (all projects)
├── config.json                            Developer preferences
├── projects.json                          Project registry + paths
└── logs/
    └── <project>-YYYY-MM-DD.md            Daily logs

Total: 3 files + daily logs. All local. Rebuilable from git.
```

---

## 9. The automation flow (what happens when)

### On every commit (invisible to developer)

```
Developer: git commit -m "fix auth timeout"
                │
                ▼
        .git/hooks/post-commit fires
                │
                ▼
        ingest.py runs (silent, <1 second):
        ├── Reads: git log -1 (message, author, hash, branch)
        ├── Reads: git diff --stat HEAD~1 (files, lines)
        ├── Reads: git diff --name-only HEAD~1 (file list)
        ├── Detects: type (commit/decision/blocker/pattern)
        ├── Detects: modules touched (top-level dirs)
        ├── Updates: file_pairs co-occurrence table
        ├── Writes: memory.db (one INSERT)
        └── Writes: daily log entry
                │
                ▼
        sync.py runs (silent, <1 second):
        ├── Reads: memory.db (ranked query)
        ├── Applies: token budget (2000 default)
        ├── Applies: relevance decay
        ├── Generates: CONTEXT.md
        └── Generates: patterns.md (if co-occurrence changed)
                │
                ▼
        Developer sees nothing. CONTEXT.md is updated.
        Next IDE session reads the fresh context.
```

### On git push (advisory warnings)

```
Developer: git push
                │
                ▼
        .git/hooks/pre-push fires
                │
                ▼
        review.py runs (<2 seconds):
        ├── Reads: git diff main...HEAD (all changes in branch)
        ├── Reads: memory.db (decisions, patterns)
        ├── Reads: guidelines.md (coding standards)
        ├── Checks: file pair compliance
        ├── Checks: guideline violations (regex)
        ├── Checks: decision compliance
        ├── Scores: risk level (LOW/MEDIUM/HIGH)
        ├── Writes: .ai-memory/review.md (not committed)
        └── Prints: summary to terminal
                │
                ▼
        pr_context.py runs (<1 second):
        ├── Reads: review.md
        ├── Reads: decisions from this branch
        ├── Generates: .ai-memory/pr-description.md
        └── Prints: "PR description ready: .ai-memory/pr-description.md"
                │
                ▼
        Terminal output (example):
        ┌─────────────────────────────────────────────┐
        │ ai-memory pre-push review                   │
        │                                             │
        │ Risk: MEDIUM                                │
        │ ✓ 8 files changed across 3 modules          │
        │ ✓ Tests updated for all changed modules     │
        │ ⚠ New provider without error handling docs  │
        │ ⚠ Consider updating decisions.md            │
        │                                             │
        │ PR description: .ai-memory/pr-description.md│
        └─────────────────────────────────────────────┘
        Push continues regardless (advisory only).
```

### On git pull/merge (context refresh)

```
Developer: git pull
                │
                ▼
        .git/hooks/post-merge fires
                │
                ▼
        sync.py runs (regenerates CONTEXT.md):
        ├── Reads: pulled changes from .ai-memory/decisions.md
        ├── Imports: any new decisions into local memory.db
        ├── Regenerates: CONTEXT.md from merged state
        └── Result: context reflects both local + pulled data
```

---

## 10. Implementation sequence

```
STEP  WHAT TO BUILD                     DEPENDS ON    EFFORT
────  ──────────────────────────────── ────────────── ──────
  1   SQLite schema (v2)                Nothing        2 hrs
  2   ingest.py (enhanced diff parser)  Schema         1 day
  3   sync.py (CONTEXT.md generator)    Schema         1 day
  4   detect.py (stack, IDE, monorepo)  Nothing        4 hrs
  5   pointers.py (all IDE files)       detect.py      4 hrs
  6   backfill.py (history import)      ingest.py      4 hrs
  7   setup.py (one-command install)    All above      1 day
  8   Hooks (post-commit, pre-push,     ingest, sync   4 hrs
      post-merge, pre-commit)
  9   templates/ (all .template files)  Nothing        4 hrs
 10   skills/ (all .md skill files)     Nothing        4 hrs
      ─── PHASE 1 COMPLETE: Core system working ───
      Effort: ~6 days

 11   guidelines.md template + check    Schema         1 day
 12   review.py (pre-push review)       Memory data    1 day
 13   pr_context.py (PR description)    review.py      4 hrs
      ─── PHASE 2 COMPLETE: Review + guidelines ───
      Effort: ~2.5 days

 14   spec.md template + tracking       Schema         1 day
 15   aggregate.py (sprint summary)     Schema         1 day
 16   migrate.py (v1 → v2 migration)    Schema         4 hrs
      ─── PHASE 3 COMPLETE: Specs + sprints ───
      Effort: ~2.5 days

 17   CI/CD workflow template           sync.py        4 hrs
 18   Monorepo scope detection          detect.py      4 hrs
 19   Cross-project pattern surfacing   Schema         4 hrs
      ─── PHASE 4 COMPLETE: Advanced scenarios ───
      Effort: ~1.5 days

TOTAL: ~12.5 days for solo developer
RECOMMENDED: Ship Phase 1 first (6 days). Validate. Iterate.
```

---

## 11. What "done" looks like

```
TEST                                                  PASS?
────────────────────────────────────────────────────  ─────
Developer clones repo, runs setup.py, sees context     [ ]
Developer commits — CONTEXT.md updates silently         [ ]
Developer pushes — sees advisory review in terminal     [ ]
Developer opens Claude Code — reads CONTEXT.md          [ ]
Developer opens Cursor — reads .cursorrules → context   [ ]
Developer opens VS Code — Copilot reads context         [ ]
Developer opens Codex CLI — reads AGENTS.md → context   [ ]
Developer with NO setup sees CONTEXT.md in repo         [ ]
New developer runs setup.py — productive in minutes     [ ]
Laptop dies — setup.py --rebuild restores everything    [ ]
5 devs push to same repo — no merge conflicts           [ ]
Sprint summary generated with one command               [ ]
Air-gapped machine — everything works offline            [ ]
No pip install needed — stdlib only                     [ ]
Total ambient token cost per session — under 2000       [ ]
Total commands developer memorises — 1 (setup.py)       [ ]
Works on Windows, macOS, Linux equally                  [ ]
CI/CD can generate context without local install        [ ]
Monorepo services get scoped context                    [ ]
Cross-project patterns surface automatically            [ ]
```
