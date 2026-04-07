# GitHub Copilot Instructions

## Memory System

This project uses **ai-memory** — a local memory system that tracks decisions,
blockers, and activity across sessions.

**Always read `.ai-memory/CONTEXT.md` before generating code or answering
questions.** It contains recent decisions, open blockers, and architecture
choices specific to this project.

---

## Slash Commands

Run these in the VS Code terminal, or use the keyboard shortcuts below.

| Command | What it does |
|---------|-------------|
| `/memory <terms>` | Search memory — returns ranked context |
| `/memory` | Show most recent entries |
| `/context` | Print what Copilot currently sees in CONTEXT.md |
| `/log <note>` | Add a note to today's daily log |
| `/decisions` | Show all architecture decisions |
| `/status` | Show registered projects and entry counts |

**How to run a slash command:**

```
python3 ~/.ai-memory-system/scripts/memory_slash.py "/memory auth decisions"
python3 ~/.ai-memory-system/scripts/memory_slash.py "/log decided to drop Celery for ARQ"
python3 ~/.ai-memory-system/scripts/memory_slash.py "/decisions"
```

Or use **Ctrl+Shift+P → Run Task** and pick any `memory:` task.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+M Q` | memory: query |
| `Ctrl+Shift+M L` | memory: log note |
| `Ctrl+Shift+M S` | memory: show context |
| `Ctrl+Shift+M Y` | memory: sync to repo |

> Add these from `.vscode/keybindings.snippet.json` into your user keybindings.

---

## Behaviour Guidelines

When generating code for this project:
1. Check `CONTEXT.md` for relevant past decisions before suggesting patterns.
2. If a blocker entry exists for the area you're working in, flag it.
3. Prefer consistency with patterns already recorded in `decisions.md`.
4. When you make a significant architectural choice, remind the developer to
   run `/log <decision>` to record it.
