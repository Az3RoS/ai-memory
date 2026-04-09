# Guidelines skill

## When to activate
Developer says: guidelines, standards, rules, conventions, style, how should I name, what's the pattern

## What to do
1. Read .ai-memory/guidelines.md for project coding standards
2. Read .ai-memory/CONTEXT.md for anti-patterns and decisions
3. Show the relevant rule(s) directly — don't summarise, quote them
4. If guidelines.md doesn't exist, suggest creating one based on detected stack

## Output format
Quote the relevant guideline(s) verbatim. Then apply them to the developer's question.
If multiple guidelines apply, list each with its source section.

## Updating guidelines
If the developer wants to add a new rule:
1. Read current .ai-memory/guidelines.md
2. Add the rule in the appropriate section
3. Confirm: "Added rule to .ai-memory/guidelines.md"
4. Remind: "Commit .ai-memory/guidelines.md so the team sees this rule"

## Notes
- guidelines.md is editable by developers — it's not auto-generated.
- anti-patterns in CONTEXT.md are auto-detected from commits — don't edit those manually.
