# Sprint summary skill

## When to activate
Developer says: sprint, summary, retro, retrospective, what did we do this week, what did we ship, weekly report

## What to do
1. Read .ai-memory/CONTEXT.md for project context
2. Run: `python scripts/memory_cli.py query --format context` (or read CONTEXT.md)
3. Filter entries to the sprint period (default: last 14 days)
4. Group by: decisions, features, fixes, blockers resolved, tests
5. Generate sprint summary

## Sprint summary format
```markdown
## Sprint Summary: [date range]
**Project:** [slug]
**Contributors:** [from git log --format="%an" | sort -u]

### Shipped
[Features and fixes from this sprint — group by module]

### Decisions made
[Decision entries from this sprint]

### Blockers resolved
[Blockers that were fixed]

### Active blockers (carry forward)
[Blockers still open from CONTEXT.md]

### Stats
- Commits: N
- Files changed: M (estimated)
- Decisions: P
- Tests added: Q (from test-type commits)

### Next sprint focus
[Active specs from .ai-memory/specs/active/ — what's in progress]
```

## Multi-project sprint
If asked for a cross-project summary:
```
python scripts/memory_cli.py status
```
Then query each project separately and combine.

## Export
The sprint summary is plain markdown. To share:
- Copy/paste into your team's communication channel
- Save to .ai-memory/sprints/YYYY-WNN.md for historical record

## Notes
- Reference decisions by date [MM-DD] format.
- Focus on decisions and blockers — those are the high-signal items.
- If asked for a retro format, add: "What went well / What to improve / Action items" sections.
