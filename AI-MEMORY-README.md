# ai-memory — Developer Guide

> **What is this?**
> A local memory system that remembers your commits, decisions, and blockers — and feeds that history to GitHub Copilot automatically. The more you commit, the smarter Copilot gets about your project.

---

## Contents

- [One-time Setup](#one-time-setup)
- [Per-Project Setup](#per-project-setup)
- [Daily Use](#daily-use)
- [Slash Commands](#slash-commands)
- [My context is empty — backfill existing commits](#my-context-is-empty)
- [FAQ](#faq)
- [Troubleshooting](#troubleshooting)

---

## One-time Setup

Do this **once on your machine**, not per project.

### 1. Find your Python path

Open Command Prompt and run:

```cmd
where python
```

You will see something like:

```
C:\Python311\python.exe
```

or

```
C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe
```

**Copy that path.** You will use it in every command below instead of `python`.

### 2. Copy the memory system to your home folder

```cmd
xcopy /E /I .ai-memory-system %USERPROFILE%\.ai-memory-system
```

### 3. Add a shortcut (optional but recommended)

Open your PowerShell profile file:

```powershell
notepad $PROFILE
```

Add this line — **replace the path with your actual Python path from step 1**:

```powershell
function memory { C:\Python311\python.exe "$env:USERPROFILE\.ai-memory-system\scripts\memory_cli.py" @args }
```

Save and reload:

```powershell
. $PROFILE
```

Test it:

```cmd
memory status
```

You should see `Projects: 0`. That is correct.

> **No PowerShell profile?** If you get an error, run this first:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
> Then try again.

---

## Per-Project Setup

Do this **once per repo** — after cloning.

Open a terminal in your project root and run — **replace the Python path**:

```cmd
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_cli.py init --project your-project-name --repo .
```

Or if you set up the shortcut:

```cmd
memory init --project your-project-name --repo .
```

Use a short slug — lowercase, no spaces. Examples: `signal`, `my-api`, `trading-app`.

**What this does:**
- Installs git hooks in `.git/hooks/`
- Creates `.ai-memory/` folder in your repo
- Creates `CONTEXT.md` — the file Copilot reads
- Registers the project in your global memory database

**Commit the new files:**

```cmd
git add .ai-memory/ .github/copilot-instructions.md .vscode/
git commit -m "chore: add ai-memory setup"
```

---

## Daily Use

**You do nothing differently.** Just commit as normal:

```cmd
git add .
git commit -m "feat(auth): added JWT middleware"
```

After every commit, the hooks automatically:
1. Ingest the commit into memory
2. Update `.ai-memory/CONTEXT.md`
3. Update the daily log

Copilot reads the updated `CONTEXT.md` on the next code generation.

---

## Slash Commands

Run these in the VS Code terminal. Replace `C:\Python311\python.exe` with your actual Python path.

| Command | What it does |
|---|---|
| `/memory <terms>` | Search memory for anything relevant |
| `/memory` | Show most recent entries |
| `/context` | See exactly what Copilot is reading |
| `/log <note>` | Add a note that isn't a commit |
| `/decisions` | Show all architecture decisions |
| `/status` | Show registered projects and entry counts |

**How to run:**

```cmd
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_slash.py "/memory auth"

C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_slash.py "/log decided to use JWT over sessions"

C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_slash.py "/decisions"
```

Or via VS Code: `Ctrl+Shift+P` → `Run Task` → pick any `memory:` task.

---

## My Context is Empty

You set up the system but already had commits before running `init`. The hooks only catch **new** commits — anything before is invisible. Fix it by backfilling.

### Backfill last 20 commits (recommended)

Run this in your project root — **replace the Python path**:

```cmd
for /f "tokens=1,* delims=|" %H in ('git log --pretty^=format^:"%H|%s" -20') do (
  C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_cli.py ingest --message "%I"
)
```

### Then sync to rebuild CONTEXT.md

```cmd
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_cli.py sync
```

### Check it worked

```cmd
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_slash.py "/context"
```

You should now see your commits, decisions, and blockers listed.

---

## How to tell Copilot to use the context

### For code generation — already automatic

`CONTEXT.md` is wired into Copilot via `.vscode/settings.json`. Every inline suggestion and `/generate` call reads it. Nothing to do.

### For a chat session — paste this once at the start

```
Read .ai-memory/CONTEXT.md and use it as background context for this session.
Summarise what you know about this project before we start.
```

### To check what Copilot is following

In Copilot Chat, ask:

```
What instructions are you currently following for this workspace?
```

Or open `Ctrl+Shift+P` → `Copilot: Show Instructions` to see every active instruction file.

---

## FAQ

**Q: Do I need to do anything after each commit?**
No. The git hooks handle everything. Just commit normally.

**Q: Will a failed hook block my commit?**
No. All hooks fail silently. Your commit always goes through regardless.

**Q: Someone else on the team doesn't have the system set up. Does that break anything?**
No. `CONTEXT.md` and `decisions.md` are plain markdown files committed to git. Anyone can open and read them. They just won't get the automatic updates until they run `init`.

**Q: How do I log something that isn't a commit?**
Use `/log`:
```cmd
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_slash.py "/log decided not to use Redis — overkill for current scale"
```

**Q: How do I search for a specific decision or bug from last week?**
```cmd
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_slash.py "/memory blocker"
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_slash.py "/memory auth decisions"
```

**Q: Can I edit CONTEXT.md manually?**
No. It is auto-generated and will be overwritten on the next commit or sync. Add notes via `/log` or commit messages instead.

**Q: How do I add a new project?**
Just run `init` again in the new repo. The global memory database tracks all projects independently.

**Q: What counts as a decision?**
Any commit message containing these words is automatically flagged as a decision:
`decided`, `chose`, `switched`, `migrated`, `replaced`, `adopted`, `deprecated`, `architecture`, `adr`

**Q: Where is the memory database stored?**
At `%USERPROFILE%\.ai-memory\memory.db` — on your machine only, never pushed to git.

**Q: How do I see how much memory has been built up?**
```cmd
memory status
```

---

## Troubleshooting

---

### `memory` command not found

**Cause:** The PowerShell function was not added or the profile was not reloaded.

**Fix:**
```powershell
notepad $PROFILE
```
Add the function (replace path with yours):
```powershell
function memory { C:\Python311\python.exe "$env:USERPROFILE\.ai-memory-system\scripts\memory_cli.py" @args }
```
Then:
```powershell
. $PROFILE
```

---

### `python` or `python3` not recognised

**Cause:** Python is not on your system PATH.

**Fix:** Use the full path instead:
```cmd
where python
```
Use whatever it returns in all commands. Example: `C:\Python311\python.exe`

---

### CONTEXT.md is empty after init

**Cause:** No commits have been ingested yet.

**Fix:** Backfill your existing commits — see [My Context is Empty](#my-context-is-empty) above.

---

### CONTEXT.md is not updating after commits

**Cause 1:** Hooks were not installed correctly.

**Check:**
```cmd
dir .git\hooks\
```
You should see `pre-commit` and `post-commit` listed. If not, re-run init:
```cmd
memory init --project your-project-name --repo .
```

**Cause 2:** The Python path inside the hook is wrong.

**Check:** Open `.git\hooks\post-commit` in a text editor. Find the `MEMORY_CLI` line and verify the path exists on your machine.

**Fix:** Replace the path in the hook file with your correct Python path.

---

### Copilot doesn't seem to know about my project

**Step 1:** Check what it sees:
```cmd
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_slash.py "/context"
```

**Step 2:** If the context looks right but Copilot isn't using it, paste this into Copilot Chat:
```
Read .ai-memory/CONTEXT.md and summarise what you know about this project.
```

**Step 3:** Check `.vscode/settings.json` exists in your repo and contains:
```json
"github.copilot.chat.codeGeneration.instructions": [
  { "file": ".ai-memory/CONTEXT.md" }
]
```

---

### `memory status` shows Projects: 0 after init

**Cause:** You ran `init` but the project was not registered in the global config.

**Fix:** Re-run init with the full path:
```cmd
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_cli.py init --project your-project-name --repo .
```

---

### Permission denied on hook files

**Cause:** Windows sometimes blocks execution of hook files.

**Fix:** Open `.git\hooks\post-commit` and `.git\hooks\pre-commit` in a text editor, verify they contain the correct Python path, then re-save them.

---

### The backfill command produced errors

**Cause:** Some commit messages contain special characters that break the `for` loop.

**Fix:** Run ingest manually for each commit instead:
```cmd
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_cli.py ingest --message "your commit message here"
```
Then sync:
```cmd
C:\Python311\python.exe %USERPROFILE%\.ai-memory-system\scripts\memory_cli.py sync
```

---

## Keyboard Shortcuts

Add these to your VS Code keybindings (`Ctrl+Shift+P` → `Preferences: Open Keyboard Shortcuts JSON`):

```json
[
  { "key": "ctrl+shift+m q", "command": "workbench.action.tasks.runTask", "args": "memory: query" },
  { "key": "ctrl+shift+m l", "command": "workbench.action.tasks.runTask", "args": "memory: log note" },
  { "key": "ctrl+shift+m s", "command": "workbench.action.tasks.runTask", "args": "memory: show context" },
  { "key": "ctrl+shift+m y", "command": "workbench.action.tasks.runTask", "args": "memory: sync to repo" }
]
```

---

## Quick Reference Card

```
SETUP (once per machine)
  where python                          → find your Python path
  memory init --project <name> --repo . → set up a repo

DAILY
  git commit -m "..."                   → automatic, nothing else needed

SEARCH
  /memory <terms>                       → search memory
  /decisions                            → all architecture decisions
  /context                              → what Copilot sees right now

LOG
  /log <note>                           → add a note without committing

DIAGNOSE
  memory status                         → check projects + entry counts
  /context                              → verify CONTEXT.md has content
```

---

*Questions? Ask your team lead or check `.github/copilot-instructions.md` for how Copilot is configured for this project.*
