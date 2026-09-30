---
name: "review"
description: 'Audit the project CLAUDE.md for token cost against value and report keep/condense/remove edits with before/after text. Use when the user wants to trim CLAUDE.md, e.g. "is my CLAUDE.md too long".'
---

# Review Project Memory

Analyze the project-level CLAUDE.md file for effectiveness and token efficiency.

## Setup

1. Locate the project-level file to analyze: check `./CLAUDE.md` first, then `.claude/CLAUDE.md`. If neither exists, tell the user and stop.
2. Read `~/.claude/CLAUDE.md` (the global file) — this is needed to accurately assess what is "redundant with global instructions" vs. genuinely project-specific

## What Earns Its Place

An instruction earns its tokens when it changes what the agent does: a convention the code does not show, a workflow that differs from defaults, a gotcha, or a must-not-violate rule (mark those **CRITICAL**, a convention this skill recommends). It does not when it is a cache of what the code or config already answers, a no-op the model does by default or the global CLAUDE.md already says, stale, or an example longer than its point. Keep each instruction unambiguous, actionable, and scannable: bullets, not paragraphs.

## Output Format

Every instruction in the file appears in exactly one of Keep, Condense, or Remove. Add lists what is missing.

Provide a structured analysis:

### Summary

- **Effectiveness Score**: 1-10 (10 = optimal value/token ratio)
- **Current Token Count**: Estimate
- **Potential Savings**: Estimated tokens that could be saved

### Analysis

#### Keep (High Value)

List instructions worth preserving with brief rationale

#### Condense (Medium Value, Verbose)

Provide before/after examples:

```
Before: [verbose version]
After: [concise version]
Savings: ~X tokens
```

#### Remove (Low Value/Redundant)

List with rationale for removal

#### Add (Missing Critical Context)

Identify gaps that cause repeated questions or mistakes

### Recommended Rewrite

Offer to produce an optimized version of the entire CLAUDE.md file, and produce one when the user asks. Default to the targeted before/after edits above rather than emitting a full rewrite unprompted — for large files a wholesale rewrite risks changing more than the user wanted.
