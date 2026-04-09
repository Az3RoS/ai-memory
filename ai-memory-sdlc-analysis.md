# ai-memory → AI SDLC: Process Advancements Analysis
## What the industry is doing in 2026 and how to adopt it simply

---

## Part 1: The landscape — seven shifts happening right now

### Shift 1: Context engineering replaced prompt engineering

Martin Fowler coined "context engineering" as the discipline that determines
whether AI coding agents produce reliable code or expensive technical debt.
The core insight: the quality of AI output depends not on how you phrase
your question but on what information the AI has access to when it answers.

CLAUDE.md, .cursorrules, and CONTEXT.md are all forms of context engineering.
Your ai-memory system is already doing context engineering — it just needs
to extend from "what happened" (memory) to "what should happen" (specs,
guidelines, review criteria).

**What this means for ai-memory:**
CONTEXT.md is already the context layer. Extend it with coding standards,
architectural rules, and review criteria — not as separate documents the
developer has to remember, but as sections the AI reads automatically.

---

### Shift 2: Spec-driven development (SDD) is mainstream

GitHub released Spec Kit (open source). The arXiv paper "Spec-Driven
Development: From Code to Contract in the Age of AI" (Feb 2026) formalized
it. The core workflow:

```
Requirement → Spec → Validation gates → AI generates code → Tests verify
```

The VS Code team now creates prototypes (actual PRs) instead of spec
documents. Their PM loop changed from "write a spec → create issues →
hand off" to "create a working prototype → iterate → ship."

Key insight from the community: "If you're already using CLAUDE.md files
effectively, you're already doing lightweight spec-driven development."

**What this means for ai-memory:**
Add a `specs/` directory under `.ai-memory/`. When a developer creates
a feature spec (even a simple markdown file), ai-memory can:
- Validate implementation against spec acceptance criteria
- Track spec → implementation → test coverage chain
- Surface unmet requirements in CONTEXT.md

---

### Shift 3: Hooks are deterministic, CLAUDE.md is advisory

The Claude Code community consensus in 2026:
- CLAUDE.md is followed ~80% of the time (advisory)
- Hooks are followed 100% of the time (deterministic)

"If something must happen every time without exception — formatting,
linting, security checks — make it a hook. If it's guidance Claude
should consider, CLAUDE.md is fine."

Claude Code now supports 20+ hook lifecycle events:
- PreToolUse / PostToolUse (before/after any tool runs)
- SessionStart / SessionEnd
- PreCompact (before context window compresses)
- Notification (after events like compaction)

The VS Code team runs Copilot code review on EVERY PR before human
review. Engineers must resolve AI comments before requesting human review.

**What this means for ai-memory:**
Your git hooks are the right foundation. Extend them:
- post-commit → ingest + sync (already doing this)
- pre-push → auto-review + guideline check (NEW)
- post-merge → context refresh (NEW)
- pre-commit → pattern compliance warning (NEW, advisory)

---

### Shift 4: Multi-agent code review is production-ready

Claude Code Review (research preview) runs multiple specialized agents
in parallel on each PR:
- Each agent looks for a different class of issue
- A verification step filters false positives
- Results are deduplicated and ranked by severity
- Findings are posted as inline comments

CodeRabbit achieves 46% accuracy on real-world runtime bugs.
Qodo saved 450,000 developer hours at a Fortune 100 retailer.
The DORA 2025 Report shows 42-48% improvement in bug detection
with AI review.

VS Code team's evolution: "Six months ago, we didn't enforce AI
review because the feedback was too noisy. Model quality significantly
improved, often catching security, performance, and quality issues
on first pass."

**What this means for ai-memory:**
You don't need CodeRabbit or Qodo. You can build a lightweight
review layer using your existing memory + git diff:
- "This PR changes auth but has no test changes" (from file_pairs)
- "This contradicts decision from 2026-04-01" (from decisions.md)
- "Missing error handling pattern used elsewhere" (from patterns)
These are context-aware reviews that external tools CAN'T do because
they don't have your project's decision history.

---

### Shift 5: The review bottleneck is the real problem

Industry data from 2026:
- 41% of commits are AI-assisted
- Developer output grew 25-35% per engineer
- But review capacity stayed flat
- Estimated 40% quality deficit by 2026

The bottleneck shifted from writing code to validating what gets merged.
AI code review tools are growing from $550M to $4B market.

The VS Code team's solution: automated validation pipelines that verify
"golden scenarios" — specs of expected behavior for core user flows.
These run as automated post-merge validation.

**What this means for ai-memory:**
Your system already tracks what changed and why. Add a review context
generator that surfaces this for reviewers:
- "Here's what this PR does in 3 sentences"
- "These decisions were made during this work"
- "These patterns were followed/broken"
- "Risk assessment: auth changed, tests updated ✓"

---

### Shift 6: Skills are the new plugins

The Open Agent Skills standard (adopted by 30+ products including
OpenAI Codex, Gemini CLI, Copilot, Cursor, JetBrains) defines
skills as SKILL.md files with YAML frontmatter + markdown instructions.

Skills load on-demand (not every session like CLAUDE.md). This is
the mechanism for heavy context without permanent token cost.

Claude Code built-in skills in 2026:
- /batch — parallel changes across worktrees
- /simplify — spawns 3 review agents on changed files
- /loop — recurring tasks for up to 3 days

Community skills: frontend-design (277K+ installs), Remotion (video),
Google Workspace CLI, and hundreds more.

**What this means for ai-memory:**
Package ai-memory capabilities as skills:
- `/memory <query>` — search project memory
- `/review` — generate review context for current changes
- `/guidelines` — check current code against project standards
- `/spec <feature>` — create a feature specification
These work in any IDE that supports the Open Agent Skills standard.

---

### Shift 7: BMAD and RIPER — structured SDLC workflows

BMAD-METHOD assigns named agent personas across the SDLC:
- Mary (Business Analyst) → requirements
- Preston (Product Manager) → PRDs
- Winston (Architect) → system design
- Devon (Developer) → implementation
- James (QA) → testing

RIPER Workflow enforces phase separation:
- Research → Innovate → Plan → Execute → Review

Both are heavyweight (21+ agents, YAML workflows). The community
feedback: "coordination overhead slows iteration."

**What this means for ai-memory:**
Don't build 21 agents. Build 5 capabilities into one system:
1. Requirement capture (from specs and issues)
2. Guideline enforcement (from coding standards)
3. Implementation assistance (from memory + patterns)
4. Review automation (from diff analysis + decisions)
5. Retrospective generation (from sprint aggregation)

Each is a script or a section in CONTEXT.md, not a separate agent.

---

## Part 2: What to add to ai-memory — the capability matrix

### Current capabilities (what ai-memory v1 does)

```
SDLC PHASE        CAPABILITY                    STATUS
─────────────── ─────────────────────────────── ──────
Planning         (none)                         ❌
Design           (none)                         ❌
Development      Context injection (CONTEXT.md) ✅
                 Decision tracking              ✅
                 Memory search (/memory)        ✅
Testing          (none)                         ❌
Review           (none)                         ❌
Deployment       (none)                         ❌
Retrospective    (none)                         ❌
```

### Proposed capabilities (ai-memory as AI SDLC)

```
SDLC PHASE        CAPABILITY                    IMPL. METHOD
─────────────── ─────────────────────────────── ──────────────────────
Planning         Requirement capture            specs/ directory
                 Feature spec generation        spec.py template
                 Task breakdown                 From spec → checklist

Design           Architecture decision log      decisions.md (exists)
                 Pattern detection              file_pairs (exists)
                 Stack awareness                stack.json (exists)

Development      Context injection              CONTEXT.md ★
                 Cross-project patterns          patterns table
                 Dev-code-help                  /help skill
                 Coding guidelines              guidelines.md → hook

Testing          Test coverage tracking          From git diff
                 Missing test detection          file_pairs co-occurrence
                 Test pattern surfacing          "auth changes need tests"

Review           Pre-push guideline check        pre-push hook
                 PR context generation           review.py → review.md
                 Decision compliance check       Against decisions.md
                 Risk scoring                    Based on modules touched

Deployment       (out of scope for v2)          Future: CI integration

Retrospective    Sprint summary                 aggregate.py
                 Pattern evolution report        From patterns table
                 Decision audit trail           From decisions.md
```

---

## Part 3: Detailed design for each new capability

### 3.1 Coding guidelines enforcement

**The problem:** Every project has coding standards but they live in a
wiki nobody reads, or in a senior dev's head.

**The solution:** `.ai-memory/guidelines.md` — committed, version-controlled,
machine-readable coding standards that ai-memory enforces.

```markdown
# Coding Guidelines

## Naming
- Python: snake_case for functions, PascalCase for classes
- Files: lowercase with underscores
- Test files: test_<module>.py

## Patterns
- All API routes must have error handling
- Database operations must use context managers
- Environment variables accessed only through settings module
- No hardcoded secrets, URLs, or credentials

## Architecture rules
- Models in src/models/, never in routes
- Business logic in src/services/, not in routes
- Routes are thin: validate → service → response
- All external API calls go through src/clients/

## Testing
- Every new module needs a test file
- Async functions need async test fixtures
- Mock external services, never call them in tests

## Anti-patterns (NEVER do these)
- No global mutable state
- No circular imports
- No print() for logging — use logger
- No try/except without specific exception type
```

**How it integrates:**

1. `guidelines.md` is committed to `.ai-memory/` (team-shared)
2. CONTEXT.md includes a compressed summary (2-3 lines)
3. Pointer files (CLAUDE.md, .cursorrules) reference it:
   `"Follow guidelines in .ai-memory/guidelines.md"`
4. Pre-push hook (advisory) checks if changed files follow patterns:
   - New Python file without corresponding test file? → warning
   - Route file with business logic? → warning
   - Import from wrong layer? → warning
5. These checks use regex/AST on the diff — no LLM needed for basics

```python
# guidelines_check.py — runs in pre-push hook
import re, sys

def check_guidelines(diff_files, guidelines):
    warnings = []

    for f in diff_files:
        # Check: new source file without test
        if f.startswith("src/") and f.endswith(".py"):
            test_file = f.replace("src/", "tests/test_")
            if test_file not in diff_files and not file_exists(test_file):
                warnings.append(f"⚠ {f} has no test file ({test_file})")

        # Check: route file with database import
        if "/routes/" in f:
            content = read_file(f)
            if re.search(r"from.*models.*import", content):
                warnings.append(f"⚠ {f}: direct model import in route (use service layer)")

        # Check: hardcoded URLs or secrets
        content = read_file(f)
        if re.search(r'https?://[^\s"\']+\.(com|io|org)', content):
            if ".env" not in f and "test" not in f:
                warnings.append(f"⚠ {f}: possible hardcoded URL (use settings)")

    return warnings
```

---

### 3.2 Automatic code review (pre-push)

**The problem:** Human reviewers are bottlenecked. Context is lost between
commit and review. Reviewers spend time understanding "what" before
evaluating "how."

**The solution:** `review.py` generates a review context file that
combines memory intelligence with diff analysis.

**What it checks (no LLM needed):**

```
CHECK                              SIGNAL SOURCE           SEVERITY
────────────────────────────────── ──────────────────────── ────────
Files changed without usual pair   file_pairs table         Medium
Decision contradicted              decisions.md + diff      High
Guideline violated                 guidelines.md + regex    Medium
Auth/payment code without tests    file path patterns       High
Config file changed                .env, settings, etc.     Info
New dependency added               requirements.txt diff    Medium
Migration without model change     file pattern mismatch    Warning
Large diff (>500 lines)            diff stat                Info
```

**Output: `.ai-memory/review.md`** (auto-generated, never committed)

```markdown
## Pre-push review: feat/multi-provider

### Summary
8 files changed, +142 -37, across 3 modules (providers, config, tests)

### Risk assessment: MEDIUM
- ⚠ Provider code changed without updating error handling docs
- ✓ Tests updated for all changed modules
- ✓ No auth/payment code modified
- ℹ New dependency: google-generativeai added to requirements.txt

### Decision compliance
- ✓ Consistent with [2026-04-01] PWA-first strategy
- ✓ Consistent with [2026-04-05] async SQLAlchemy choice
- ⚠ New provider added — consider updating decisions.md

### Pattern compliance
- ✓ Provider changes paired with config changes (as expected)
- ✓ Test files updated for changed modules
- ⚠ src/providers/gemini.py created without src/providers/gemini_test.py
    (historical pattern: provider + test always paired)

### For reviewers
This PR adds Gemini as an LLM provider alongside existing Groq support.
The provider abstraction in src/providers/base.py is extended with a new
concrete implementation. Config changes support provider switching via
environment variable.
```

**This is the killer feature.** No external tool can generate this
because no external tool has your decision history, file co-occurrence
data, and coding guidelines in one place.

---

### 3.3 PR review context (for GitHub/GitLab)

**The problem:** PR descriptions are often empty or say "fixed stuff."
Reviewers lack context.

**The solution:** When developer pushes, the pre-push hook generates
a PR description from memory.

```python
# pr_context.py
def generate_pr_description(project, branch, diff_files):
    # What changed
    modules = extract_modules(diff_files)
    stats = git_diff_stat()

    # Why (from memory — decisions made on this branch)
    decisions = query_decisions(project, branch=branch)

    # Risk (from guidelines + patterns)
    risks = check_guidelines(diff_files)
    pattern_breaks = check_patterns(diff_files)

    # Cross-references
    related = find_related_memories(project, modules)

    return format_pr_template(
        summary=auto_summary(diff_files, stats),
        decisions=decisions,
        risks=risks,
        patterns=pattern_breaks,
        related=related,
        testing=detect_test_changes(diff_files)
    )
```

Output is copied to clipboard or written to `.ai-memory/pr-description.md`
for the developer to paste into the PR. Zero effort.

---

### 3.4 Requirement validation

**The problem:** Features get built without clear acceptance criteria.
AI generates code that "works" but doesn't match the requirement.

**The solution:** Lightweight spec files in `.ai-memory/specs/`

```markdown
<!-- .ai-memory/specs/2026-04-09-gemini-provider.md -->
# Spec: Add Gemini LLM provider

## Requirement
Support Google Gemini as an alternative LLM provider alongside Groq.
Users switch via PROVIDER environment variable.

## Acceptance criteria
- [ ] Gemini provider implements BaseProvider interface
- [ ] Supports text generation and streaming
- [ ] Handles rate limiting (429) with exponential backoff
- [ ] Timeout configurable via settings (default: 30s)
- [ ] Falls back to Groq if Gemini is unavailable
- [ ] Unit tests cover: success, timeout, rate limit, fallback

## Constraints
- No new dependencies beyond google-generativeai
- Must work with existing async session lifecycle
- API key from environment, never hardcoded

## Related decisions
- [2026-04-01] PWA-first (not affected)
- [2026-04-05] async SQLAlchemy (provider must be async)
```

**How ai-memory uses this:**

1. CONTEXT.md surfaces active specs:
   `"Active spec: Gemini provider (4/6 criteria met)"`
2. Post-commit hook checks if changed files relate to an active spec
3. Acceptance criteria are tracked against test results
4. When all criteria met → spec moves to `specs/completed/`
5. Spec becomes a decision record automatically

**No LLM needed for tracking.** Criteria are checkboxes. File changes
map to criteria via keyword matching. Test passes map via test names.

---

### 3.5 Dev-code-help (contextual assistance)

**The problem:** Developer asks AI "how do I add a new provider?"
AI doesn't know the project's patterns, conventions, or past decisions.

**The solution:** CONTEXT.md already provides this. Enhance it with:

1. **Pattern examples** in `.ai-memory/patterns.md`:
   ```
   ## Adding a new provider
   Based on 3 previous providers (groq, openai, gemini):
   1. Create src/providers/<name>.py implementing BaseProvider
   2. Add config in src/config/providers.py
   3. Create tests/test_<name>_provider.py
   4. Update .env.example with <NAME>_API_KEY
   5. Add to provider factory in src/providers/__init__.py
   Files always changed together: provider + config + test + factory
   ```

2. **Anti-pattern log** in `.ai-memory/antipatterns.md`:
   ```
   ## Known pitfalls
   - Don't import models directly in routes (use services)
   - Don't create sync functions in async codebase (everything awaits)
   - Don't hardcode timeouts (use settings.PROVIDER_TIMEOUT)
   - SQLAlchemy sessions: always use async with session_maker()
   ```

3. These are auto-populated from commit history:
   - Patterns from file_pairs co-occurrence
   - Anti-patterns from fix commits that follow error commits

---

### 3.6 Dev productivity metrics (passive)

**The problem:** Sprint retros lack data. "What did we do?" requires
manual recall.

**The solution:** ai-memory already tracks everything. Add summaries:

```python
# metrics.py
def developer_metrics(project, period_days=14):
    return {
        "commits": count_commits(project, period_days),
        "decisions": count_type(project, "decision", period_days),
        "blockers_opened": count_type(project, "blocker", period_days),
        "blockers_resolved": count_resolved_blockers(project, period_days),
        "modules_touched": unique_modules(project, period_days),
        "patterns_followed": pattern_compliance_rate(project, period_days),
        "guideline_warnings": guideline_violation_count(project, period_days),
        "avg_files_per_commit": avg_files_per_commit(project, period_days),
        "contributors": unique_authors(project, period_days),
    }
```

This feeds into sprint summaries — no manual input from any developer.

---

## Part 4: File structure — final (with all capabilities)

```
ai-memory/
├── setup.py                         # One command to install everything
├── scripts/
│   ├── memory_cli.py                # CLI: init, ingest, query, sync, status,
│   │                                #       review, spec, sprint, guidelines, help
│   ├── ingest.py                    # Parse git diff + branch + file patterns
│   ├── sync.py                      # Generate CONTEXT.md (token-budgeted)
│   ├── detect.py                    # Stack, IDE, monorepo detection
│   ├── pointers.py                  # Generate IDE pointer files
│   ├── backfill.py                  # Import existing git history
│   ├── migrate.py                   # Schema migrations
│   ├── aggregate.py                 # Sprint summaries, cross-project
│   ├── review.py                    # Pre-push code review generation
│   ├── guidelines_check.py          # Coding standards compliance
│   ├── spec_track.py                # Spec → implementation tracking
│   └── pr_context.py                # PR description generator
├── hooks/
│   ├── post-commit                  # ingest + sync
│   ├── pre-push                     # review + guidelines check (advisory)
│   ├── post-merge                   # context refresh
│   └── pre-commit                   # pattern compliance warning (advisory)
├── templates/
│   ├── CONTEXT.md.template
│   ├── guidelines.md.template       # Starter coding standards
│   ├── spec.md.template             # Feature spec template
│   ├── CLAUDE.md.template
│   ├── cursorrules.template
│   ├── AGENTS.md.template
│   └── copilot-instructions.template
├── skills/                           # Open Agent Skills standard
│   ├── memory/SKILL.md              # /memory search
│   ├── review/SKILL.md              # /review current changes
│   ├── spec/SKILL.md                # /spec create feature spec
│   ├── guidelines/SKILL.md          # /guidelines check compliance
│   └── help/SKILL.md                # /help contextual dev assistance
├── README.md
└── AI-MEMORY-README.md
```

### Per-repo generated structure

```
your-project/
├── .ai-memory/                       # Committed (team-shared)
│   ├── CONTEXT.md                    # ★ Universal truth — all IDEs
│   ├── index.json                    # Project config
│   ├── stack.json                    # Auto-detected tech stack
│   ├── decisions.md                  # Architecture Decision Log
│   ├── patterns.md                   # Auto-detected file patterns
│   ├── guidelines.md                 # Coding standards (editable)
│   ├── antipatterns.md               # Known pitfalls (auto + manual)
│   ├── specs/                        # Feature specifications
│   │   ├── active/                   # In-progress specs
│   │   └── completed/               # Done specs (become decisions)
│   └── .gitattributes                # merge=ours for auto-generated files
├── CLAUDE.md                         # Pointer → CONTEXT.md + directives
├── .cursorrules                      # Pointer → CONTEXT.md + directives
├── AGENTS.md                         # Pointer → CONTEXT.md + directives
├── .github/
│   └── copilot-instructions.md       # Pointer → CONTEXT.md
└── .vscode/
    └── tasks.json                    # VS Code shortcuts
```

---

## Part 5: CONTEXT.md — enhanced structure with all capabilities

```markdown
<!-- AUTO-GENERATED by ai-memory v2. Do not edit. -->
<!-- Project: signal | Budget: 2000 tokens | Updated: 2026-04-09T14:30Z -->

## Identity
Stack: Python 3.11 / FastAPI / async SQLAlchemy / SQLite / pytest
Branch: feat/multi-provider-llm | Contributors: 3 this month

## Guidelines (summary — full: .ai-memory/guidelines.md)
snake_case functions, PascalCase classes. Routes are thin: validate→service→respond.
No global state. No print() — use logger. Mock externals in tests.

## Active specs
- Gemini provider (4/6 criteria met) → .ai-memory/specs/active/gemini-provider.md

## Decisions (never truncated)
- [04-08] Switched LLM: Groq → Gemini (cost)
- [04-05] Chose async SQLAlchemy over raw sqlite3
- [04-01] PWA over native — browser-first

## Blockers
- Async session lifecycle → test flakes (since 04-07)
- Gemini rate limiting not implemented (since 04-08)

## Patterns
- auth changes → always pair with tests/test_auth.py
- provider changes → always pair with config/settings.py
- model changes → always pair with alembic migration

## Anti-patterns (project-specific)
- Don't import models in routes (use services layer)
- Don't create sync functions (everything async)
- SQLAlchemy sessions: always use `async with`

## Recent (7 days)
- [04-09] fix(providers): Gemini timeout handling (arnab)
- [04-08] feat(dashboard): theme switcher (dev-c)
- [04-07] refactor(db): async SQLAlchemy migration (dev-b)

## Cross-project
- [trading-app] FastAPI async sessions need explicit close()
```

---

## Part 6: Implementation priority (phased rollout)

```
PHASE  WHAT                               EFFORT    IMPACT
────── ────────────────────────────────── ────────── ──────
  1    Enhanced ingest.py (diff parsing)   1 day     HIGH
       sync.py (universal CONTEXT.md)      1 day     HIGH
       setup.py (one-command install)      1 day     HIGH
       backfill.py                         0.5 day   HIGH
       Pointer file templates              0.5 day   MEDIUM
       ─── TOTAL PHASE 1: 4 days ──────────────────────────

  2    guidelines.md template + check      1 day     HIGH
       review.py (pre-push review)         1 day     HIGH
       pr_context.py (PR description)      0.5 day   MEDIUM
       ─── TOTAL PHASE 2: 2.5 days ────────────────────────

  3    spec.md template + tracking         1 day     MEDIUM
       antipatterns.md auto-population     0.5 day   MEDIUM
       Cross-project pattern surfacing     0.5 day   MEDIUM
       ─── TOTAL PHASE 3: 2 days ──────────────────────────

  4    Sprint aggregation (aggregate.py)   1 day     MEDIUM
       Skills packaging (/memory, /review) 1 day     HIGH
       Metrics generation                  0.5 day   LOW
       ─── TOTAL PHASE 4: 2.5 days ────────────────────────

  5    CI/CD integration (GitHub Actions)  1 day     MEDIUM
       Monorepo support                    1 day     MEDIUM
       Onboarding generator                0.5 day   LOW
       ─── TOTAL PHASE 5: 2.5 days ────────────────────────

  TOTAL: ~13.5 days for solo developer
  Recommended: Ship Phase 1-2 first (6.5 days), iterate on rest
```

---

## Part 7: What NOT to build (deliberate omissions)

```
FEATURE                    WHY NOT
───────────────────────── ──────────────────────────────────────────
Vector search / embeddings  FTS5 is sufficient at project scale.
                            Adds dependencies. Build path: swap later.

LLM at write-time           Token cost per commit. Breaks air-gapped
                            requirement. All inference is read-time only.

Multi-agent orchestration   BMAD has 21 agents. Community says "too much
                            coordination overhead." One script per capability.

Deployment automation       Out of scope. CI/CD tools exist.

Real-time collaboration     Memory is async by design (git is async).
                            Real-time collab is a different problem.

Dashboard / web UI          Adds complexity. CONTEXT.md IS the dashboard.
                            Review with: cat .ai-memory/CONTEXT.md

Cloud storage               Local-first. Git is the sync mechanism.
                            No SaaS dependency. No data sovereignty issues.
```

---

## Part 8: How this compares to commercial tools

```
CAPABILITY              QODO ($19/seat)   CODERABBIT     AI-MEMORY (free)
─────────────────────── ───────────────── ────────────── ─────────────────
Codebase indexing        Full repo         Full repo      SQLite FTS5
PR review                Auto on PR        Auto on PR     Pre-push hook
Security scanning        Built-in          Built-in       Regex patterns
Decision tracking        ❌                 ❌              ✅ (core feature)
Cross-project patterns   ❌                 ❌              ✅ (core feature)
Sprint summaries         ❌                 ❌              ✅
Coding guidelines        Custom rules      .coderabbit    guidelines.md
Spec tracking            ❌                 ❌              ✅ specs/
Context for AI IDEs      ❌                 ❌              ✅ CONTEXT.md
Air-gapped support       ❌                 ❌              ✅
Zero dependencies        ❌                 ❌              ✅
Free                     ❌                 Free tier      ✅ Always free

The key differentiator: ai-memory provides CONTEXT (decisions, patterns,
history) while commercial tools provide ANALYSIS (bugs, vulnerabilities).
They are complementary, not competitive. ai-memory makes commercial
tools better by giving them context they don't have.
```

---

## Part 9: The "dumb user" test

Every capability passes this test:
"A developer who knows only `git commit` can use this."

```
CAPABILITY              USER ACTION REQUIRED         AUTOMATIC?
─────────────────────── ─────────────────────────── ──────────
Memory building          Just commit normally         ✅ Yes
Context injection        Nothing — IDE reads files    ✅ Yes
Guidelines enforcement   Nothing — pre-push warns     ✅ Yes
Code review              Nothing — pre-push generates  ✅ Yes
PR description           Copy .ai-memory/pr-desc.md   ⚡ 1 step
Spec creation            Write a markdown file         ✏️ Manual
Sprint summary           Run: memory sprint            ⚡ 1 command
Onboarding              Run: memory onboard            ⚡ 1 command
Initial setup            Run: python setup.py           ⚡ 1 command
```

Only spec creation requires active thought — and it should.
Everything else is invisible to the developer.
```
