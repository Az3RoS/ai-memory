# Code review skill

## When to activate
Developer says: review, check, pre-push, PR, pull request, code quality, ready to ship

## What to do
1. Read .ai-memory/CONTEXT.md for project context and patterns
2. Run: `git diff --cached --stat` (staged) or `git diff main...HEAD --stat` (branch)
3. For each changed file:
   a. Check if a corresponding test file exists (from patterns in CONTEXT.md)
   b. Check naming conventions match guidelines in .ai-memory/guidelines.md
   c. Flag any anti-patterns listed in .ai-memory/CONTEXT.md
4. Check if any decisions in CONTEXT.md are relevant to these changes
5. Score risk: HIGH if auth/payment/config/migration touched; MEDIUM if 5+ files; LOW otherwise
6. Generate review summary

## Output format
```
### Review: [branch name or "staged changes"]
**Risk:** LOW | MEDIUM | HIGH
**Changes:** N files across M modules
**Decisions referenced:** [list from CONTEXT.md or "none"]
**Warnings:** [list or "none found"]
**Recommendation:** ship | address warnings first
```

## Notes
- Never block the developer. All review output is advisory.
- Reference decisions by date: [04-08] not by vague description.
- If .ai-memory/review.md exists (written by pre-push hook), read it first.
