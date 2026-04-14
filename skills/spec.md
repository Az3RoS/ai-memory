# Feature spec skill

## When to activate
Developer says: spec, specification, requirement, feature plan, design doc, RFC, I want to build

## What to do
1. Read .ai-memory/CONTEXT.md for relevant decisions and existing patterns
2. Ask the developer for (if not already given):
   - Feature name
   - Problem it solves
   - Success criteria (2-5 measurable outcomes)
3. Generate a spec using the template below
4. Save to .ai-memory/specs/active/<feature-name>.md
5. Confirm: "Spec saved to .ai-memory/specs/active/<feature-name>.md"

## Spec template
```markdown
# Spec: [Feature Name]
**Status:** active
**Created:** [date]
**Author:** [from git config]

## Problem
[1-2 sentences. What breaks or is missing without this?]

## Solution
[2-4 sentences. What we're building and why this approach.]

## Success criteria
- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2]
- [ ] [Measurable outcome 3]

## Decisions made
[Any architectural decisions made during spec — these should also go in decisions.md]

## Out of scope
[Explicitly list what this spec does NOT cover]

## Implementation notes
[Technical notes, patterns to follow, risks]
```

## Notes
- Keep specs concise. A spec is a contract, not a novel.
- Move to .ai-memory/specs/completed/ when all criteria are met.
- Reference decisions by date format [MM-DD] to match CONTEXT.md.
# Feature spec skill

## When to activate
Developer says: spec, specification, requirement, feature plan, design doc, RFC, I want to build

## What to do
1. Read .ai-memory/CONTEXT.md for relevant decisions and existing patterns
2. Ask the developer for (if not already given):
   - Feature name
   - Problem it solves
   - Success criteria (2-5 measurable outcomes)
3. Generate a spec using the template below
4. Save to .ai-memory/specs/active/<feature-name>.md
5. Confirm: "Spec saved to .ai-memory/specs/active/<feature-name>.md"

## Spec template
```markdown
# Spec: [Feature Name]
**Status:** active
**Created:** [date]
**Author:** [from git config]

## Problem
[1-2 sentences. What breaks or is missing without this?]

## Solution
[2-4 sentences. What we're building and why this approach.]

## Success criteria
- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2]
- [ ] [Measurable outcome 3]

## Decisions made
[Any architectural decisions made during spec — these should also go in decisions.md]

## Out of scope
[Explicitly list what this spec does NOT cover]

## Implementation notes
[Technical notes, patterns to follow, risks]
```

## Notes
- Keep specs concise. A spec is a contract, not a novel.
- Move to .ai-memory/specs/completed/ when all criteria are met.
- Reference decisions by date format [MM-DD] to match CONTEXT.md.
