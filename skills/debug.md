# Debug skill

## When to activate
Developer says: bug, fix, error, failing, broken, exception, traceback, it's not working, why is

## What to do
1. Read .ai-memory/CONTEXT.md immediately — check:
   - **Blockers section**: is this a known blocker?
   - **Anti-patterns**: is this a known mistake pattern?
   - **Recent decisions**: did a recent change cause this?
2. Ask for (if not provided): error message, stack trace, and what changed recently
3. Cross-reference the error with CONTEXT.md before suggesting fixes

## Debugging approach
```
Step 1: Check CONTEXT.md blockers — is this already known?
Step 2: Check anti-patterns — is this a pattern violation?
Step 3: Check recent activity — what changed in the last 7 days?
Step 4: Diagnose the specific error
Step 5: Suggest fix consistent with project decisions
```

## Output format
```
**Known issue?** [yes — see blocker from [date] | no]
**Root cause:** [1 sentence]
**Fix:** [specific code or steps]
**Prevent recurrence:** [add to anti-patterns / update guidelines if applicable]
```

## If it's a known blocker
Reference the blocker from CONTEXT.md:
"This matches the blocker from [date]: [blocker description]. Known workaround: [if any]."

## Notes
- Never suggest workarounds for known blockers without referencing the blocker.
- If the fix resolves a blocker: "After this fix, you can remove the blocker from .ai-memory/CONTEXT.md on next sync."
