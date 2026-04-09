# Contextual help skill

## When to activate
Developer says: help, how do I, show me, what's the best way, I'm stuck, how does X work

## What to do
1. Read .ai-memory/CONTEXT.md to understand the project stack and decisions
2. Check if the answer relates to a known blocker (listed in CONTEXT.md)
3. Check if there's a relevant decision that constrains the answer
4. Give the answer in terms of THIS project's stack and patterns

## Key principles
- Answer using the project's actual stack (from CONTEXT.md), not generic advice
- Reference existing decisions: "As per [04-05] we use async SQLAlchemy, so..."
- If a blocker in CONTEXT.md is relevant, call it out first
- If the question implies a pattern violation, point it out

## Format
Direct answer first. Context second.
```
[Direct answer — 1-3 sentences]

In this project: [how it applies given CONTEXT.md — what files/patterns to use]

Reference: [decision or pattern from CONTEXT.md if relevant]
```

## When the answer isn't in CONTEXT.md
If no relevant decision or pattern exists:
1. Give the best general answer for the detected stack
2. Suggest: "Consider adding this to .ai-memory/guidelines.md if it becomes a pattern"
