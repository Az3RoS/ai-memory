# Onboarding skill

## When to activate
Developer says: onboard, new to this project, getting started, first day, what do I need to know, walk me through

## What to do
1. Read .ai-memory/CONTEXT.md completely
2. Read .ai-memory/decisions.md
3. Read .ai-memory/guidelines.md (if it exists)
4. Generate a structured onboarding summary

## Onboarding output format
```markdown
## Welcome to [project name]

### Stack
[From CONTEXT.md Identity section]

### How to run it
[From README or CONTEXT.md — if not available, say "check README.md"]

### Key decisions (know these before touching code)
[Last 5 decisions from decisions.md, most recent first]

### File structure
[Module map from CONTEXT.md]

### Active patterns (always follow these)
[Patterns from CONTEXT.md]

### Anti-patterns (never do these)
[Anti-patterns from CONTEXT.md]

### Active blockers (know before you start)
[Blockers from CONTEXT.md]

### Active specs (work in progress)
[List .ai-memory/specs/active/ if any exist]

### First things to do
1. Read .ai-memory/guidelines.md
2. Check .ai-memory/specs/active/ for current sprint work
3. Make a small commit to trigger the memory hooks
```

## Notes
- The goal is for a new developer to be productive in minutes, not days.
- Don't overwhelm — prioritise decisions and anti-patterns above everything else.
- If .ai-memory/CONTEXT.md is empty or minimal: "Run `python setup.py` first to build context from git history."
