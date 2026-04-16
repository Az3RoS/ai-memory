# ai-memory — Self-Guide

> One file. Everything you need to know. Read your section, skip the rest.

---

## Who should read what

| You are | Read |
|---------|------|
| New developer joining the team | [New Developer](#new-developer) → [Daily Use](#daily-use) → [FAQ](#faq) |
| Developer setting up a new repo | [First-Time Setup](#first-time-setup) → [What Gets Created](#what-gets-created) |
| Team lead onboarding the team | [Team Lead](#team-lead) |
| Product owner wanting context | [Product Owner](#product-owner) |
| Anyone hitting an error | [Troubleshooting](#troubleshooting) |

---

## What is ai-memory?

A local system that turns your git history into AI context. Every commit you make is automatically stored in a local database and written to `.ai-memory/CONTEXT.md`. Your AI assistant (Copilot, Claude, Cursor, etc.) reads that file and knows your project — decisions made, blockers hit, patterns to follow, what was built last week.

**No cloud. No LLM on write. No API keys. Just Python + git.**

```
you commit → hook fires → commit parsed → CONTEXT.md updated → AI reads it
```

---

## New Developer

You joined a project that already has ai-memory. Here's what you do.

### Step 1 — Find Python on your machine

**Windows:**
```cmd
where python
```
Expected output: `C:\Python311\python.exe` or similar. If you get "not found", install Python from python.org (3.10 or later).

**Mac/Linux:**
```bash
which python3
```
Expected output: `/usr/bin/python3` or `/usr/local/bin/python3`.

> **Keep this path.** You will use it in the commands below.

### Step 2 — Get the tool

```bash
# From the team's shared location, or clone directly:
git clone https://github.com/Az3RoS/ai-memory ~/.ai-memory-system
```

> **Air-gapped / no internet?** Ask your team lead for the zip. Unzip to `~/.ai-memory-system` (Windows: `C:\Users\YourName\.ai-memory-system`).

### Step 3 — Run setup in your repo

**Run this command from inside your project directory** — not from the ai-memory folder, not from home. From your actual project root where you see `.git/`.

```bash
cd /path/to/your-project          # your project, not ai-memory

python ~/.ai-memory-system/setup.py
```

**Windows:**
```cmd
cd C:\Projects\your-project

C:\Python311\python.exe C:\Users\YourName\.ai-memory-system\setup.py
```

This takes 10–30 seconds. You will see output like:
```
  [1/6] Detecting environment...
    Stack:    python
    IDEs:     vscode, claude
    Commits:  247

  [2/6] Initialising .ai-memory/...
  [3/6] Generating IDE pointer files...
  [4/6] Installing skill files...
  [5/6] Importing git history...
    Imported 200 commits, found 14 decisions
  [6/6] Generating CONTEXT.md...

  Setup complete. Project 'your-project' is ready.
```

### Step 4 — Commit the generated files

```bash
git add .ai-memory/ CLAUDE.md .cursorrules AGENTS.md GEMINI.md
git add .github/copilot-instructions.md .junie/
git commit -m "chore: add ai-memory context"
git push
```

> **Already committed by someone else?** Skip this. If `.ai-memory/CONTEXT.md` already exists in the repo, just run setup (Step 3) — it will detect the existing project and only install hooks for you.

### Step 5 — You're done

Make a commit. CONTEXT.md updates. Your AI assistant reads it automatically.

---

## First-Time Setup

Setting up ai-memory in a **brand new repo** that has never had it.

### Where to run the setup command

Always run from **inside the target repo** — the project you want to add memory to.

```
WRONG:  cd ~/.ai-memory-system && python setup.py
WRONG:  python setup.py (from home directory)
RIGHT:  cd ~/your-project && python ~/.ai-memory-system/setup.py
```

The setup script detects the current directory as the project root. If you run it from the wrong place, it will set up memory for the wrong folder.

### What the command does

```
python ~/.ai-memory-system/setup.py
```

1. Detects your stack (Python, TypeScript, Go, etc.) and any IDEs present
2. Creates `.ai-memory/` in your project with CONTEXT.md, decisions.md, index.json
3. Generates pointer files for every AI IDE (CLAUDE.md, .cursorrules, AGENTS.md, etc.)
4. Copies skill files to `.ai-memory/skills/`
5. Installs git hooks (pre-commit, post-commit, pre-push, post-merge)
6. Imports your last 200 commits into the local database
7. Generates the first CONTEXT.md

### Optional flags

```bash
# Override the project name (default: repo folder name)
python ~/.ai-memory-system/setup.py --project my-api

# Create a feature template immediately after setup
python ~/.ai-memory-system/setup.py --feature "User authentication redesign"

# Create a fix template immediately after setup
python ~/.ai-memory-system/setup.py --fix "Login timeout bug"

# Wipe and reimport all history from scratch
python ~/.ai-memory-system/setup.py --rebuild

# Point to a specific repo path
python ~/.ai-memory-system/setup.py --repo /path/to/repo
```

### What gets created

**In your repo (commit these):**
```
.ai-memory/
  CONTEXT.md          ← auto-generated, AI reads this
  decisions.md        ← architecture decisions ledger
  index.json          ← project metadata
  skills/             ← AI skill files (8 files)
    review.md
    guidelines.md
    spec.md
    help.md
    feature.md
    debug.md
    onboard.md
    sprint.md
.ai-wiki/            ← optional generated project wiki
  wiki/
    INDEX.md
    ARCHITECTURE.md
    api/endpoints.md
    models/overview.md
    services/overview.md
    database/tables.md
    components/overview.md
    tests/coverage-map.md
CLAUDE.md             ← pointer for Claude Code
.cursorrules          ← pointer for Cursor
AGENTS.md             ← pointer for Codex CLI
GEMINI.md             ← pointer for Gemini CLI
.windsurfrules        ← pointer for Windsurf
.github/
  copilot-instructions.md   ← pointer for VS Code Copilot
.junie/
  guidelines.md       ← pointer for JetBrains
```

### What is `.ai-wiki`?

`.ai-wiki/` is the generated project wiki folder. It is created automatically during setup and seeded with documentation templates for architecture, API, models, services, database, components, and test coverage.

- `.ai-wiki/wiki/INDEX.md` is the entry point for the generated wiki
- The rest of the files are stubs you can fill in as the project evolves
- Commit `.ai-wiki/` if your team wants the generated docs in source control
- If you want to regenerate the wiki structure later, re-run:
  ```bash
  python ~/.ai-memory-system/setup.py
  ```
- If you only need a new feature or fix template, use:
  ```bash
  python ~/.ai-memory-system/setup.py --feature "My feature name"
  python ~/.ai-memory-system/setup.py --fix "My bug fix"
  ```

The generated files are intended as a starting point. Edit them in place and keep them synced with your project architecture.

**On your machine only (never committed):**
```
~/.ai-memory/
  memory.db           ← your personal SQLite database
  projects.json       ← registry of all your projects
  logs/               ← daily markdown logs
  entities/           ← knowledge graph files
```

### Files you may need to create manually

Most files are auto-generated. Two are meant to be edited by hand:

| File | What to do |
|------|-----------|
| `.ai-memory/guidelines.md` | Copy from `templates/guidelines.md.template` and edit for your team's standards. This is **not** auto-generated — you own it. |
| `.ai-memory/specs/active/<name>.md` | Copy from `templates/spec.md.template` when starting a new feature. |

Everything else (`CONTEXT.md`, `decisions.md`, `index.json`, all pointer files) is auto-generated. Do not edit them by hand — they will be overwritten.

---

## Daily Use

Once set up, you do nothing differently.

### The automatic flow

```bash
git commit -m "feat(auth): add JWT middleware"
```

Within 1 second, invisibly:
- The commit is parsed and stored in `~/.ai-memory/memory.db`
- `.ai-memory/CONTEXT.md` is regenerated
- The daily log is updated
- Your AI assistant will read the new context on the next session

### On git push

An advisory review prints to your terminal before the push:
```
┌────────────────────────────────────────────────────┐
│  ai-memory pre-push review                         │
│                                                    │
│  Risk: LOW                                         │
│  ✓ 4 files changed across 2 modules               │
│  📐 1 decision(s) in this branch                   │
│  PR description: .ai-memory/pr-description.md     │
└────────────────────────────────────────────────────┘
```

The push always continues. This is advisory — it never blocks.

### On git pull

After a pull, CONTEXT.md automatically regenerates to include anything your teammates committed.

### Commit message tips

The system extracts signal from your commit messages:

| Keyword in message | What happens |
|-------------------|--------------|
| `decided`, `chose`, `switched`, `migrated`, `adopted`, `deprecated`, `architecture`, `adr` | Logged as an architecture decision |
| `blocked`, `blocker`, `wip`, `fixme`, `workaround`, `hack` | Logged as a blocker/known issue |
| `feat:` prefix | Logged as a new feature |
| `fix:` prefix | Logged as a bug fix |
| `test:` prefix | Logged as a test entry |

**Examples that work well:**
```bash
git commit -m "decided to use async SQLAlchemy over raw sqlite3 for connection pooling"
git commit -m "fix(auth): blocker — JWT tokens expiring too early due to clock skew"
git commit -m "feat(payments): add Stripe webhook handler"
```

### Creating a new feature or fix

When you start work on a feature or bug fix, initialize it with ai-memory. This creates a dedicated folder with templates and automatically embeds current project context.

**Start a feature:**
```bash
python ~/.ai-memory-system/scripts/memory_cli.py feature "User authentication redesign"
```

Or use setup.py directly after install:
```bash
python ~/.ai-memory-system/setup.py --feature "User authentication redesign"
```

Output:
```
[memory] created feature 'User authentication redesign' at .ai-memory/docs/02-feature/FEAT_001_user-authentication-redesign
```

**Start a fix:**
```bash
python ~/.ai-memory-system/scripts/memory_cli.py fix "Login timeout bug"
```

Output:
```
[memory] created fix 'Login timeout bug' at .ai-memory/docs/02-feature/FIX_001_login-timeout-bug
```

**What gets created:**

Each feature or fix folder contains 5 template files:
```
.ai-memory/docs/02-feature/
├── FEAT_001_user-authentication-redesign/
│   ├── feature.md          # Feature description and acceptance criteria
│   ├── plan.md             # Implementation plan (includes project context)
│   ├── scratch.md          # Working notes (for you)
│   ├── test.md             # Test cases and coverage
│   └── dod.md              # Definition of done checklist
└── FIX_001_login-timeout-bug/
    ├── feature.md          # (same as above, but for fixes)
    ├── plan.md
    ├── scratch.md
    ├── test.md
    └── dod.md
```

**Key details:**

- **Folder naming:** `FEAT_NNN_slug` or `FIX_NNN_slug` — numbers auto-increment, slug is derived from the feature name
- **feature.md** is pre-filled with your feature/fix name
- **plan.md** automatically includes a "Context" section with recent project decisions and patterns — you don't have to write them
- **dod.md** is a shared template covering code quality, documentation, testing, and deployment
- **Counter auto-increments:** The next feature will be `FEAT_002`, next fix will be `FIX_002`, etc.

**Using the files:**

```bash
# Open your feature folder
cd .ai-memory/docs/02-feature/FEAT_001_user-authentication-redesign

# Edit as you work
code feature.md plan.md scratch.md test.md dod.md

# Commit your feature folder when you're done
git add .ai-memory/docs/02-feature/FEAT_001_user-authentication-redesign/
git commit -m "feat(auth): complete user authentication redesign — see FEAT_001 for details"
```

### CLI commands (when you need them)

```bash
# Run from any directory inside your project
python ~/.ai-memory-system/scripts/memory_cli.py <command>

feature "<name>"        # Create a new feature folder with templates
fix "<name>"            # Create a new fix folder with templates
sync                    # Manually regenerate CONTEXT.md
status                  # Show all projects and entry counts
query "auth decisions"  # Search memory for anything
backfill                # Re-import git history (if hooks weren't installed earlier)
review                  # Run pre-push review manually

# Setup flags for feature/fix templates
python ~/.ai-memory-system/setup.py --feature "My new feature"
python ~/.ai-memory-system/setup.py --fix "My bug fix"
```

---

## Team Lead

What you need to know for onboarding your team.

### First-time project setup (you do this once)

1. Run setup in the project repo
2. Commit the generated files
3. Push — your team will get CONTEXT.md on their next pull

```bash
cd your-project
python ~/.ai-memory-system/setup.py
git add .ai-memory/ CLAUDE.md .cursorrules AGENTS.md GEMINI.md
git add .github/copilot-instructions.md .junie/
git commit -m "chore: add ai-memory context"
git push
```

### What each team member must do

Every developer runs setup once in their local clone:

```bash
cd your-project    # their local clone
python ~/.ai-memory-system/setup.py
```

This installs hooks locally. It does **not** overwrite the committed files.

### What team members get without installing

Even if someone **never runs setup**, they still get:
- `.ai-memory/CONTEXT.md` in the repo — their AI reads it
- `CLAUDE.md`, `.cursorrules`, etc. — all IDEs pick these up
- `decisions.md` — human-readable decision log

The only thing missing without setup: their own commits don't auto-ingest. They can manually run `backfill` later.

### Managing guidelines

Create `.ai-memory/guidelines.md` from the template and commit it. This is the team's shared coding standards. The pre-push hook checks against it.

```bash
cp ~/.ai-memory-system/templates/guidelines-python.md.template .ai-memory/guidelines.md
# or for TypeScript:
cp ~/.ai-memory-system/templates/guidelines-typescript.md.template .ai-memory/guidelines.md

# Edit to match your team's actual standards, then:
git add .ai-memory/guidelines.md
git commit -m "chore: add team coding guidelines"
```

### Merge conflicts in CONTEXT.md

CONTEXT.md is auto-generated. If two developers commit at the same time, there may be a conflict. Resolve it by accepting either version and re-running sync:

```bash
# Accept yours (or theirs — doesn't matter, both will resync)
git checkout --ours .ai-memory/CONTEXT.md
python ~/.ai-memory-system/scripts/memory_cli.py sync
git add .ai-memory/CONTEXT.md
git commit -m "chore(memory): resync context"
```

**To prevent this permanently**, add the gitattributes config from the template:
```bash
cat ~/.ai-memory-system/templates/gitattributes.template >> .gitattributes
git add .gitattributes
git commit -m "chore: configure merge strategy for auto-generated files"
```

### Sprint summaries

At the end of a sprint, any team member can generate a summary:
```bash
python ~/.ai-memory-system/scripts/memory_cli.py query "sprint summary" --format context
```

Or ask your AI: *"Generate a sprint summary using .ai-memory/skills/sprint.md"*

---

## Product Owner

You don't need to install anything. Here's what ai-memory gives you and your team.

### What it does for your team

| Problem | What ai-memory solves |
|---------|----------------------|
| "Why did we build it this way?" | Every architectural decision is logged with date and context in `decisions.md` |
| New developer takes 2 weeks to get up to speed | They run one command and get full project context in minutes |
| AI assistant gives generic advice unrelated to your stack | AI reads `.ai-memory/CONTEXT.md` — it knows your stack, your decisions, your blockers |
| "Who changed X and why?" | All commits flow through the memory system — searchable by topic, decision, date |
| Bugs caused by forgetting past anti-patterns | Anti-patterns are captured from commit history and fed back to the AI |
| Sprint retros missing detail | Auto-generated sprint summaries from actual commit history |

### What you can read (no setup needed)

These files are committed to git and human-readable:

| File | What it contains |
|------|-----------------|
| `.ai-memory/CONTEXT.md` | Live project snapshot: stack, decisions, blockers, patterns, recent activity |
| `.ai-memory/decisions.md` | Full chronological decision log with dates and authors |
| `.ai-memory/guidelines.md` | Team coding standards |
| `.ai-memory/specs/active/` | Feature specs currently in progress |
| `.ai-memory/specs/completed/` | Completed feature specs (history) |

### How to read the decision log

Open `.ai-memory/decisions.md` in any editor or on GitHub. You will see entries like:
```
[04-08] arnab: chose Stripe over PayPal for payment processing — lower fees for our volume
[04-05] dev-b: switched to async SQLAlchemy — sync version caused timeouts under load
[04-01] arnab: PWA over native app — 60% of users are desktop, native app unjustified
```

These are permanent. They survive developer turnover. They are never deleted.

---

## Where is the global storage?

The database that stores all your memory entries lives at:

| OS | Path |
|----|------|
| Windows | `C:\Users\YourName\.ai-memory\memory.db` |
| Mac/Linux | `~/.ai-memory/memory.db` |

This is **local to your machine**. It is never pushed to git. Each developer has their own copy.

If you lose it (laptop dies, fresh machine), run:
```bash
python ~/.ai-memory-system/setup.py --rebuild
```

This reimports everything from git history. No data is permanently lost as long as git history exists.

### Changing the storage location

Not currently configurable via flag, but you can set the `AI_MEMORY_HOME` environment variable (if supported by your setup) or edit `memory_config.py`:

```python
# scripts/memory_config.py, line ~22
GLOBAL_DIR = Path.home() / ".ai-memory"
# Change to, e.g.:
GLOBAL_DIR = Path("D:/ai-memory-data")
```

---

## FAQ

**Q: Where exactly do I run the setup command?**
From inside your project repo — the directory that contains `.git/`. Not from the ai-memory tool folder. Not from your home directory.

```bash
cd /my-projects/trading-app    # your project
python ~/.ai-memory-system/setup.py
```

**Q: What if I don't know where Python is?**
```bash
# Windows
where python
where python3

# Mac/Linux
which python3
which python
```
If both return nothing, Python is not installed. Download from python.org — 3.10 or later.

**Q: The hook is not triggering — my CONTEXT.md is not updating after commits.**

Check 1 — verify hooks exist:
```bash
ls .git/hooks/
```
You should see `pre-commit`, `post-commit`, `pre-push`, `post-merge`.

Check 2 — verify the Python path inside the hook:
```bash
cat .git/hooks/post-commit
```
Look for the `MEMORY_CLI=` line. Open that path in a file explorer to confirm it exists.

Check 3 — run manually to see the error:
```bash
# Replace with your actual Python path and project name
python ~/.ai-memory-system/scripts/memory_cli.py ingest --project your-project
python ~/.ai-memory-system/scripts/memory_cli.py sync --project your-project
```

Check 4 — re-run setup if hooks are missing or broken:
```bash
python ~/.ai-memory-system/setup.py
```

**Q: What if Python is installed but `python` or `python3` isn't in PATH?**
Use the full path in every command. On Windows this is typically:
```
C:\Users\YourName\AppData\Local\Programs\Python\Python314\python.exe
```

You can also add a PowerShell alias in `$PROFILE`:
```powershell
function memory { "C:\full\path\to\python.exe" "$env:USERPROFILE\.ai-memory-system\scripts\memory_cli.py" @args }
```

**Q: Can a failed hook block my commit?**
No. All hooks are written with `|| true` — they fail silently. Your commit always succeeds regardless.

**Q: I already had 500 commits before installing. Will it import them?**
Yes. Setup automatically backfills your last 200 commits. For older commits, it scans all commit messages for decisions and blockers. To re-import after setup:
```bash
python ~/.ai-memory-system/scripts/memory_cli.py backfill --project your-project
```

**Q: A teammate doesn't have ai-memory installed. Does that break anything?**
No. They get `.ai-memory/CONTEXT.md` and `decisions.md` from the repo. Their AI reads it. Their commits just won't auto-ingest until they run setup.

**Q: Can I edit CONTEXT.md manually?**
No — it is overwritten on every commit and sync. To add context that isn't a commit:
```bash
python ~/.ai-memory-system/scripts/memory_cli.py log --message "decided to deprecate the v1 API by end of Q2"
```

**Q: What files should I commit to git?**
```
.ai-memory/         (except .ai-memory/review.md and pr-description.md)
CLAUDE.md
.cursorrules
AGENTS.md
GEMINI.md
.windsurfrules
.github/copilot-instructions.md
.junie/guidelines.md
```

**Q: What should NOT be committed?**
```
~/.ai-memory/            (your personal database — never committed)
.ai-memory/review.md     (generated per-push, ignored by .gitignore)
.ai-memory/pr-description.md
*.local files in .ai-memory/
```

**Q: I'm on a new machine. How do I restore everything?**
```bash
git clone https://github.com/Az3RoS/ai-memory ~/.ai-memory-system
cd your-project
python ~/.ai-memory-system/setup.py --rebuild
```
`--rebuild` reimports all git history. CONTEXT.md and decisions.md are already in the repo.

**Q: What counts as a decision?**
Any commit message containing: `decided`, `chose`, `switched`, `migrated`, `replaced`, `adopted`, `deprecated`, `architecture`, `adr`.

Write commit messages that include these words when you make a real architectural call.

**Q: The AI is not using the context.**
Ask your AI directly:
```
Read .ai-memory/CONTEXT.md and tell me what you know about this project.
```
If it can answer, the context is working. If not, check that the pointer files (CLAUDE.md, .cursorrules, etc.) are committed and that `.ai-memory/CONTEXT.md` has content.

**Q: Two developers committed at the same time and CONTEXT.md has a merge conflict.**
Accept either version and resync:
```bash
git checkout --ours .ai-memory/CONTEXT.md
python ~/.ai-memory-system/scripts/memory_cli.py sync
git add .ai-memory/CONTEXT.md
git commit -m "chore(memory): resync"
```

**Q: I want a sprint summary.**
Ask your AI: *"Summarise the last 2 weeks of work using .ai-memory/skills/sprint.md"*

Or via CLI:
```bash
python ~/.ai-memory-system/scripts/memory_cli.py query "last 2 weeks" --format context
```

---

## Troubleshooting

### CONTEXT.md is empty after setup

Cause: No commits were ingested yet, or backfill was skipped.

Fix:
```bash
python ~/.ai-memory-system/scripts/memory_cli.py backfill --project your-project
python ~/.ai-memory-system/scripts/memory_cli.py sync --project your-project
```

---

### Hook fires but CONTEXT.md isn't in the repo

Cause: The hook runs but the file isn't staged for commit.

Check: The `pre-commit` hook stages `.ai-memory/CONTEXT.md`. If the `.ai-memory/` directory isn't tracked by git yet, `git add` inside the hook does nothing.

Fix: Add the directory once manually:
```bash
git add .ai-memory/
git commit -m "chore: track ai-memory directory"
```

---

### `ModuleNotFoundError` when running any command

Cause: You're running the command from the wrong directory, or the scripts path is wrong.

Fix: Always use the full path to `memory_cli.py`:
```bash
python ~/.ai-memory-system/scripts/memory_cli.py status
```

---

### `setup.py` runs but no pointer files (CLAUDE.md etc.) are created

Cause: The pointer files were skipped because non-ai-memory files exist with those names.

Check: Open `CLAUDE.md` (or any pointer file). If it doesn't contain `<!-- ai-memory:`, it was written by something else and won't be overwritten.

Fix: If you want ai-memory to manage it, delete the file and re-run setup:
```bash
rm CLAUDE.md
python ~/.ai-memory-system/setup.py
```

---

### `setup.py` ran but `.git/hooks/` shows no new hooks

Cause: You ran setup.py outside a git repo, or the `.git/` directory is in a parent folder.

Fix: Run setup from the directory that contains `.git/`:
```bash
ls .git/     # this should work before running setup
python ~/.ai-memory-system/setup.py
```

---

### The pre-push advisory is not appearing

Cause: `pre-push` hook not installed or `review.py` failing silently.

Check:
```bash
cat .git/hooks/pre-push
```

Fix: Re-run setup. Then test the review manually:
```bash
python ~/.ai-memory-system/scripts/memory_cli.py review
```

---

## Quick Tips

- **Use conventional commits** (`feat:`, `fix:`, `refactor:`, `chore:`). The parser understands them and produces better context.
- **Say "decided" when you decide something.** `git commit -m "decided to use Postgres over SQLite"` captures a permanent ADR automatically.
- **`backfill` is your friend** if you joined a project mid-way or installed late.
- **Don't edit CONTEXT.md** — it's overwritten on every sync. Put permanent notes in commit messages or use `memory log`.
- **guidelines.md is yours to own** — the system won't overwrite it. Maintain it like a living document.
- **CONTEXT.md is capped at ~1,500 tokens** — recent items and decisions take priority. Older routine commits age out. This is by design.
- **Decisions never age out** — they stay in CONTEXT.md forever, regardless of age.
- **Blockers stay visible** until a future commit resolves them. Write `fix: resolved [blocker description]` to signal resolution.
- **Skills are just markdown files.** Read `.ai-memory/skills/*.md` to understand what your AI can do in this project. They're plain text — edit them to match your workflow.
- **The global DB is rebuilable.** Don't worry about losing `~/.ai-memory/memory.db`. Run `setup.py --rebuild` and it regenerates from git.
- **Works offline.** No network calls. No API. No tokens consumed at write time. All processing is local.

---

## Quick Reference

```
INSTALL (once per machine)
  python ~/.ai-memory-system/setup.py   ← from inside your project repo

DAILY (automatic)
  git commit -m "..."                   ← hooks do the rest

MANUAL COMMANDS
  ...memory_cli.py status               ← check projects + counts
  ...memory_cli.py sync                 ← force regenerate CONTEXT.md
  ...memory_cli.py backfill             ← re-import git history
  ...memory_cli.py review               ← run pre-push review manually
  ...memory_cli.py query "auth"         ← search memory

FILES TO COMMIT
  .ai-memory/ CLAUDE.md .cursorrules AGENTS.md GEMINI.md
  .github/copilot-instructions.md .junie/

FILES NEVER TO COMMIT
  ~/.ai-memory/   (your personal database)

STORAGE
  Windows: C:\Users\YourName\.ai-memory\memory.db
  Mac/Linux: ~/.ai-memory/memory.db
```
