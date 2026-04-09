# Feature implementation skill

## When to activate
Developer says: new feature, implement, add X, build X, I need to create

## What to do
1. Read .ai-memory/CONTEXT.md for:
   - Relevant existing decisions (check if this feature is constrained by any)
   - File patterns (which files should be created/modified together)
   - Anti-patterns (what NOT to do)
   - Module map (where does this feature belong?)
2. Check .ai-memory/specs/active/ for an existing spec for this feature
3. If no spec exists and feature is non-trivial: suggest creating one first (use spec.md skill)
4. Plan implementation following the patterns in CONTEXT.md

## Implementation checklist
Before writing code, verify:
- [ ] Which module does this belong to? (see Module map in CONTEXT.md)
- [ ] Are there existing decisions that affect this feature?
- [ ] Which files need to be created? (apply file pair patterns)
- [ ] Are there anti-patterns to avoid? (see Anti-patterns in CONTEXT.md)
- [ ] Does this need a migration? (if touching data models)

## Output format
```
## Implementation plan: [Feature name]

**Module:** [which directory]
**Files to create/modify:** [list]
**Decisions referenced:** [from CONTEXT.md]
**Patterns applied:** [from CONTEXT.md]

### Steps
1. [First step]
2. [Second step]
...

### Notes
[Any risks, edge cases, or things to watch out for]
```

## Notes
- Always check anti-patterns first — avoid repeating known mistakes.
- If this creates a new architectural decision, note it: "Commit message should include 'decided' so it's captured as a decision."
