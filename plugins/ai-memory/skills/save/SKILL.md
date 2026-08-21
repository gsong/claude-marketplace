---
name: gs:ai-memory:save
description: Use when the user wants to save, capture, or record a summary of the current session's work for future Claude Code sessions — e.g. "write handoff notes", "before we wrap up, save what we did", "remember this for next session". Also use when the user invokes /gs:ai-memory:save.
---

# Save Project Memory

Capture a succinct summary of the current session's work to enable future Claude Code sessions to understand what was done and continue debugging or enhancement.

## Process

1. **Ask the user for a topic/title** describing what was accomplished (e.g., "commodity-based routing", "auth system refactor")

2. **Analyze recent work:**
   - Run `git status` and `git diff` to see unstaged changes
   - Run `git log --oneline -10` to see recent commits in this session
   - If changes are already committed, use `git diff HEAD~N` (where N covers the session's commits) to see the full scope. Determine N by counting the session's commits in the `git log` output from the previous step.
   - Identify key files modified
   - Understand the scope of changes

3. **Extract and document:**
   - Core problem solved or feature added
   - Key design decisions made (the "why")
   - Non-obvious patterns or gotchas discovered
   - What was tested/verified
   - Important file locations and relationships

4. **Create memory document:**
   - Filename: `ai-swap/memories/{YYYY-MM-DD}-{topic-slug}.md`
   - `ai-swap/memories/` is intended as a local, git-ignored scratch location for these notes. Before writing, verify it is ignored (`git check-ignore -q ai-swap` or equivalent); if it isn't, or the project has no such convention, warn the user and ask where memories should live before writing.
   - Use ISO date format (e.g., `2025-10-08-commodity-routing.md`). Use the `/gs:utilities:date` skill if available to get today's date; otherwise run `date +%F`. Don't guess the date.
   - Follow structure below

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

## Optimization Principles

**DO:**

- Focus on "why" over "what" (code already shows what)
- Include design decisions and trade-offs
- Document non-obvious patterns
- Use concise bullet points
- Reference file locations
- Include enough context for debugging/enhancement

**DON'T:**

- Include code snippets unless absolutely critical for understanding
- Explain obvious changes that are clear from the code
- Duplicate information available elsewhere
- Write paragraphs when bullets suffice
- Include implementation details that are self-evident

The goal is maximum effectiveness per token: future Claude should understand the session's context, key decisions, and be able to continue work without re-discovering everything.
