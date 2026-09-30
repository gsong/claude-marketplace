---
name: "save"
description: 'Write a handoff note so the next session can resume this one''s work, decisions, and gotchas. Use when the user wants to save or hand off the session''s work, e.g. "write handoff notes", "before we wrap up".'
---

# Save Session Handoff

Write a succinct handoff note for the current session's work so the next Claude Code session can understand what was done and continue debugging or enhancement.

## Process

1. **Ask the user for a topic/title** describing what was accomplished (e.g., "commodity-based routing", "auth system refactor")

2. **Analyze recent work:**
   - Run `git status` and `git diff` to see unstaged changes
   - Run `git log --oneline -10` to see recent commits in this session
   - If changes are already committed, use `git diff HEAD~N` (where N covers the session's commits) to see the full scope. Determine N by counting the session's commits in the `git log` output from the previous step.
   - Done when every file the session touched is either listed under Files Reference or knowingly left out as trivial.

3. **Create the handoff:**
   - Filename: `ai-swap/memories/{YYYY-MM-DD}-{topic-slug}.md`
   - `ai-swap/memories/` is intended as a local, git-ignored scratch location for handoffs. Before writing, verify it is ignored (`git check-ignore -q ai-swap` or equivalent); if it isn't, or the project has no such convention, warn the user and ask where handoffs should live before writing.
   - Use ISO date format (e.g., `2025-10-08-commodity-routing.md`). Use the `utilities:date` skill if available to get today's date; otherwise run `date +%F`. Don't guess the date.
   - Write the document with the structure below; the braces say what each section holds.

## Document Structure

```markdown
# {Title}

**Date:** {YYYY-MM-DD}

## Summary

{1-2 sentence overview of what was accomplished}

## Key Changes/Decisions

- {Design decision with rationale}
- {Non-obvious pattern or gotcha}
- {Important architectural choice}

## Testing/Verification

- {What was tested}
- {What was verified}

## Future Considerations

- {Potential improvements or edge cases to watch}
- {Related work that might be needed}

## Files Reference

**{Category}:**

- `path/to/file.ts` - Brief description
- `path/to/other.ts:123` - Specific line reference if critical
```

## What to Record

Record only what the next session cannot recover from the repo: the reason behind each choice, the gotcha no code confesses, and what was verified. Bullets and file paths, not prose or code.
