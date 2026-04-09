# ai-memory

A lightweight, local AI memory system for developer productivity.
Works across every AI-powered IDE. No cloud. No plugins. No marketplace.
Zero token cost on commit. Stdlib Python only.

Adapted from [Karpathy's LLM Knowledge Base](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) architecture and shaped by the convergent evolution of memory systems across Claude Code, Cursor, Copilot, and the broader AI SDLC landscape of 2026.

---

## Why this exists

Every AI coding assistant forgets everything between sessions. Your decisions, your architecture, your debugging history, your coding standards — gone. You spend the first ten minutes of every session re-explaining your project. Multiply that across a team of five, across three projects, across a six-month sprint cycle. That is thousands of hours of repeated context-setting that a machine should be handling.

ai-memory solves this by building a persistent, queryable memory from your git activity and feeding it to your AI assistant automatically. You commit normally. The system captures what changed, why, and how it relates to previous work. Your AI assistant reads this context on every session without you doing anything.

The result: your AI assistant starts every session already knowing your stack, your decisions, your patterns, your blockers, and your team's recent activity.

---

## The seven shifts that make this necessary

The AI-assisted development landscape changed fundamentally between late 2025 and mid 2026. Seven shifts converged to make structured memory not just useful but essential for any team shipping production code.

### 1. Context engineering replaced prompt engineering

The quality of AI output depends not on how you phrase your question but on what information the AI has access to when it answers. Martin Fowler coined "context engineering" as the discipline of curating the entire information environment an AI agent operates within — the files it reads, the rules it follows, the history it carries, the tools it can reach, and the structure of the project it navigates. A well-crafted prompt with poor context produces worse results than a vague prompt with excellent context. ai-memory is a context engineering tool: it ensures your AI assistant has the right project knowledge before you ask your first question.

### 2. Spec-driven development went mainstream

GitHub released Spec Kit. An arXiv paper formalised spec-driven development (SDD). The VS Code team stopped writing spec documents and started creating working prototypes directly. The core insight: specifications are no longer documents humans read after the fact — they are executable contracts that AI agents validate against during implementation. When your AI assistant knows your feature spec, your acceptance criteria, and your architectural constraints, it generates code that meets requirements on the first pass instead of the third.

### 3. Hooks became the enforcement layer

The Claude Code community reached a clear consensus: CLAUDE.md is advisory (followed roughly 80% of the time), but hooks are deterministic (followed 100% of the time). If something must happen on every commit without exception — memory capture, context refresh, guideline checks — it belongs in a git hook, not in a markdown file the AI might skip. ai-memory uses git hooks as its automation backbone because they fire on every git operation regardless of which IDE, terminal, or operating system the developer uses.

### 4. Multi-agent code review hit production

Claude Code Review runs multiple specialised agents in parallel on each pull request, each looking for a different class of issue, with a verification step filtering false positives. The VS Code team now requires engineers to resolve AI review comments before requesting human review. CodeRabbit achieves 46% accuracy on real-world runtime bugs. The DORA 2025 Report shows 42-48% improvement in bug detection with AI review. The bottleneck in software delivery shifted from writing code to validating what gets merged, and structured memory makes review dramatically more effective because reviewers get context — what changed, why, which decisions were made, which patterns were followed or broken — without reading through thirty commits.

### 5. The review bottleneck became the real crisis

Developer output grew 25-35% per engineer thanks to AI-assisted coding. 41% of commits are now AI-assisted. But human review capacity stayed flat. The estimated quality deficit reached 40% by 2026 — more code enters the pipeline than reviewers can validate with confidence. ai-memory addresses this directly: by auto-generating review context that summarises decisions, flags pattern deviations, and scores risk, it gives reviewers the information they need in seconds instead of hours.

### 6. Skills became the universal extension mechanism

The Open Agent Skills standard was adopted by over 30 products including OpenAI Codex, Google Gemini CLI, Microsoft Copilot, Cursor, and JetBrains. A skill is a markdown file with instructions that an AI agent reads when a relevant task comes up. Skills load on demand (not every session), keeping the context window lean. ai-memory packages its capabilities — code review, guideline checking, spec creation, contextual help — as plain markdown skill files that work in any IDE without marketplace access, plugin installation, or internet connectivity.

### 7. Structured SDLC workflows emerged but heavyweight ones failed

Frameworks like BMAD-METHOD (21 specialised agents) and RIPER (5-phase workflow) attempted to bring structure to AI-assisted development. The community verdict: too much coordination overhead. ai-memory takes the opposite approach — one memory system, one context file, five lightweight capabilities, zero orchestration. Structure should be invisible to the developer. If they have to think about the workflow, the workflow is wrong.

---

## Key concepts every developer should understand

These terms appear throughout AI-assisted development tooling in 2026. Understanding them is not optional — they directly affect how productive you are with any AI coding assistant.

### Context window

The context window is the total amount of text an AI model can process in a single interaction. Think of it as the model's working memory. For Claude, this is currently up to 200,000 tokens. Everything the AI knows about your conversation, your code, your project files, and your instructions must fit inside this window. When it fills up, older information gets compressed or dropped. Every token matters because every token of project context displaces a token the AI could use for reasoning about your actual question.

### Tokens

A token is roughly three-quarters of a word, or about four characters of English text. "function" is two tokens. A 100-line Python file is roughly 500-800 tokens. Your entire CONTEXT.md should stay under 2,000 tokens — that is about 1,500 words, or three pages of text. This is enough to communicate your stack, your decisions, your patterns, your blockers, and two weeks of activity. Going beyond this wastes context window space that the AI needs for reasoning.

### Ambient context vs on-demand context

Ambient context is information loaded into every session automatically — your CONTEXT.md, your coding guidelines, your pointer files. This costs tokens on every interaction but saves the developer from re-explaining the project. On-demand context is information loaded only when needed — a specific memory search result, a skill file read for a particular task, a spec document referenced during implementation. Good memory systems minimise ambient cost and maximise on-demand precision.

### Token budget

A fixed cap on how many tokens the context file is allowed to consume. ai-memory defaults to 2,000 tokens for CONTEXT.md. Within that budget, entries are ranked by value: decisions first (they never truncate), then blockers, then patterns, then recent activity. If the budget is exceeded, the lowest-value entries at the bottom are dropped — never mid-entry, never decisions. The budget is configurable per project.

### Context engineering

The practice of curating what information your AI assistant has access to. This is not prompt engineering (how you phrase a question) — it is the broader discipline of ensuring the AI has the right files, rules, history, and structure to produce useful output. A developer who invests thirty minutes setting up good context saves hours of correcting an AI that made wrong assumptions. ai-memory automates context engineering: it decides what goes into CONTEXT.md, how it is ranked, and when it is refreshed, so the developer does not have to think about it.

### Skills (in the AI coding context)

A skill is a set of instructions that tells an AI assistant how to perform a specific task. Unlike plugins (which require marketplace installation and API integration), skills are plain markdown files that the AI reads when a relevant topic comes up. A code review skill tells the AI: read the diff, check against guidelines, look for pattern deviations, score risk, and output a structured summary. The AI follows these instructions because they are in its context window, not because a plugin API was called. This is why skills work in restricted environments — they are just text files.

### Hooks (in the git context)

Git hooks are shell scripts that run automatically at specific points in the git workflow — after a commit, before a push, after a merge. They are not IDE-specific. They fire regardless of whether you committed from VS Code, a terminal, a CI runner, or a Docker container. ai-memory uses hooks as its automation layer because they are the one mechanism that works universally across every development environment. Critically, ai-memory's hooks never block git operations — they run silently and fail gracefully.

### File co-occurrence (patterns)

When two files consistently change together across many commits — for example, `src/auth/jwt.py` and `tests/test_auth.py` — that is a pattern. ai-memory detects these patterns automatically from git history and uses them for two purposes: helping the AI understand your project's structure (the patterns section of CONTEXT.md), and flagging when a commit breaks an established pattern (the pre-push review warns: "you changed auth but didn't update the test file you always pair with it").

### Relevance decay

Not all memories are equally useful. A decision made yesterday is more relevant than a routine commit from six weeks ago. ai-memory applies a decay function: entries lose relevance over time unless they keep being surfaced in CONTEXT.md (which bumps their score). Decisions decay slowly (half-life of roughly 70 days). Regular commits decay faster (half-life of roughly 23 days). Patterns that keep appearing never decay. This ensures the token budget is spent on what matters most right now.

### Pointer files

Every AI-powered IDE reads at least one convention file from the filesystem. Claude Code reads CLAUDE.md. Cursor reads .cursorrules. Copilot reads .github/copilot-instructions.md. ai-memory generates all of these, but each contains the same thing: a small set of session directives and a reference to read .ai-memory/CONTEXT.md. The pointer files are the bridge between ide-specific conventions and a single source of truth. They cost roughly 120 tokens each, loaded once per session.

### Single source of truth (CONTEXT.md)

CONTEXT.md is the one file that all AI assistants read, regardless of IDE. It is auto-generated by ai-memory from the SQLite database and is never edited manually. It contains: project identity (stack, branch, team), active decisions, current blockers, detected patterns, anti-patterns, recent activity across all contributors, module structure, and cross-project insights. Every pointer file redirects to it. Every skill references it. It is the canonical representation of your project's memory.

---

## What ai-memory does across the development lifecycle

```
SDLC PHASE        WHAT AI-MEMORY PROVIDES                          EFFORT REQUIRED
───────────────── ──────────────────────────────────────────────── ──────────────────
Planning           Feature spec templates, requirement tracking     Write a markdown file
Design             Architecture decision log, pattern detection     Automatic from commits
Development        Universal context injection, cross-project       Automatic (just commit)
                   patterns, contextual dev assistance
Testing            Missing test detection, test pattern surfacing   Automatic from patterns
Code review        Pre-push review context, guideline compliance,   Automatic on push
                   risk scoring, pattern deviation warnings
PR review          Auto-generated PR descriptions with context,     Copy one file
                   decision references, and risk assessment
Retrospective      Sprint summaries, pattern evolution reports      One command
Onboarding         Full project context on first setup, decision    Run setup once
                   history, anti-patterns, coding guidelines
```

---

## How it works (no code, just the flow)

A developer commits normally. A git hook fires silently and captures the commit message, the diff stat, the changed file paths, and the branch name. This information is parsed — without any LLM — to extract what changed, which modules were touched, whether the commit represents a decision, a bugfix, a feature, or routine maintenance, and which files changed together. All of this is stored in a local SQLite database.

After ingestion, a sync process generates CONTEXT.md by querying the database, ranking entries by type and relevance, applying the token budget, and writing a structured markdown file. This file is committed to the repository and shared with the team through normal git operations.

When a developer opens any AI-powered IDE, the IDE reads its native convention file (CLAUDE.md, .cursorrules, etc.), which points to CONTEXT.md. The AI assistant starts the session with full project context — stack, decisions, patterns, blockers, recent activity — without the developer saying a word.

When a developer pushes, a pre-push hook generates a review context: what changed, which decisions are relevant, which patterns were followed or broken, and a risk score. This is advisory — it never blocks the push — but it gives the developer (and their reviewers) instant insight into the quality and completeness of the changes.

Everything is local. Everything is file-based. Everything uses Python stdlib. Everything works offline. Everything works in restricted environments.

---

## What makes this different from other memory systems

| Dimension | ai-memory | Claude Memory Compiler | MemPalace | Mem0 / Zep |
|-----------|-----------|----------------------|-----------|------------|
| Dependencies | Python stdlib only | Python + uv + Agent SDK | ChromaDB + pip | Cloud API + paid tier |
| LLM at write-time | No (zero cost per commit) | Yes (~$0.02/session) | No | Yes |
| Works air-gapped | Yes | No (needs API) | Partially (needs Llama) | No |
| IDE support | All (via pointer files) | Claude Code only | Via MCP | Chrome extension |
| Team sharing | Via git (committed files) | Via git | Local only | Cloud sync |
| Plugin required | No | No | MCP server | API key |
| Review capability | Yes (pre-push hook) | No | No | No |
| Guideline enforcement | Yes (regex + patterns) | No | No | No |
| Sprint aggregation | Yes (cross-project SQL) | No | No | No |
| Decision tracking | Yes (core feature) | Yes | No | No |
| Cross-project patterns | Yes (shared SQLite) | No | No | No |
| Cost | Free forever | Subscription + API | Free | $19-249/month |

The key differentiator: commercial tools like CodeRabbit and Qodo provide analysis (finding bugs and vulnerabilities). ai-memory provides context (decisions, patterns, history, guidelines). They are complementary. ai-memory makes every other tool better by giving it context that no external service has access to — your team's decision history, your file co-occurrence patterns, and your project-specific coding standards.

---

## Who this is for

**Solo developers** who work across multiple projects and waste time re-explaining their stack, their decisions, and their patterns to AI assistants at the start of every session.

**Small teams (2-10 developers)** where knowledge walks out the door when someone leaves, where sprint retros rely on memory instead of data, and where code review lacks the context needed to catch architectural regressions.

**Developers in restricted environments** — banks, government contractors, defence, healthcare — where you cannot install marketplace plugins, cannot use cloud APIs, cannot send code to external services, and need everything to run on an air-gapped laptop with nothing beyond Python and Git.

**Teams adopting AI-assisted development** who recognise that the bottleneck has shifted from writing code to validating it, and that structured context is the difference between an AI assistant that helps and one that generates plausible-looking code that contradicts last week's architecture decision.

---

## Design principles

**One file is the truth.** CONTEXT.md is the single source of context for all IDEs. Every other file is a pointer to it.

**One command is the setup.** `python setup.py` is the only command a developer ever runs. After that, everything is automatic.

**Git is the sync mechanism.** No shared database. No cloud service. Committed files are the team layer. Local SQLite is the performance layer. Git history is the immutable source of truth.

**Hooks are the automation layer.** Not IDE plugins. Not marketplace extensions. Git hooks fire on every git operation regardless of IDE, terminal, or operating system.

**Skills are just files.** Not plugins. Not API integrations. Markdown files that the AI reads when a relevant task comes up. They work in every IDE that can read a file.

**Nothing blocks the developer.** Every hook fails silently. Every check is advisory. The system never prevents a commit or a push. It provides information and lets the developer decide.

**Everything is rebuildable.** If the SQLite database is lost, `setup.py --rebuild` reconstructs it from git history. Zero data loss by design.

**Stdlib only.** No pip install. No npm. No external dependencies. Python's built-in `sqlite3`, `subprocess`, `pathlib`, and `json` modules are all that is needed. This is a deliberate constraint that ensures the system runs everywhere Python and Git exist.

---

## Architecture overview

```
┌──────────────────────────────────────────────────────────────┐
│  LAYER 3: TEAM SHARED (committed to git)                     │
│  .ai-memory/ — CONTEXT.md, decisions.md, guidelines.md,      │
│  patterns.md, skills/, specs/                                │
│  Every developer sees this. Survives team changes.            │
├──────────────────────────────────────────────────────────────┤
│  LAYER 2: DEVELOPER LOCAL (per machine)                      │
│  ~/.ai-memory/memory.db — SQLite + FTS5, all projects        │
│  Fast search, relevance scoring, cross-project queries.       │
│  Never pushed. Each developer builds independently.           │
├──────────────────────────────────────────────────────────────┤
│  LAYER 1: GIT HISTORY (immutable source of truth)            │
│  Commits, diffs, branches, file changes.                     │
│  If memory.db is lost, rebuild from here. Zero data loss.     │
└──────────────────────────────────────────────────────────────┘
```

---

## Roadmap

| Phase | What | Status |
|-------|------|--------|
| 1 — Memory | Auto-ingest from git, token-budgeted CONTEXT.md, universal IDE support, brownfield backfill, multi-project | Building |
| 2 — Review | Pre-push code review, guideline enforcement, PR description generation | Planned |
| 3 — Specs | Feature specification tracking, requirement validation, acceptance criteria | Planned |
| 4 — Sprints | Cross-project sprint summaries, team aggregation, pattern evolution | Planned |
| 5 — Guardian | Architecture rule enforcement, pattern compliance warnings, decision conflict detection | Future |
| 6 — Onboarding | Auto-generated onboarding documents, full project knowledge transfer | Future |

---

## Requirements

- Python 3.8+
- No external packages — stdlib only (`sqlite3`, `subprocess`, `pathlib`, `json`)
- Git
- Any AI-powered IDE (Claude Code, Cursor, VS Code + Copilot, Codex CLI, Windsurf, JetBrains, Gemini CLI) — or none at all (the memory system works independently)

---

## License

MIT

---

## Credits

Built by [Az3RoS](https://github.com/Az3RoS). Adapted from Karpathy's LLM Knowledge Base architecture. Informed by research into Claude Memory Compiler, MemPalace, Cline Memory Bank, and the broader AI memory systems landscape of 2026. Shaped by the real-world constraints of building software in restricted environments where simplicity is not a preference but a requirement.