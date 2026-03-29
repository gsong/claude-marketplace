# Save Project Memory

Capture a succinct summary of the current session's work to enable future Claude Code sessions to understand what was done and continue debugging or enhancement.

## Process

1. **Ask the user for a topic/title** describing what was accomplished (e.g., "commodity-based routing", "auth system refactor")

2. **Analyze recent work:**
   - Run `git status` and `git diff` to see changes
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
   - Use ISO date format (e.g., `2025-10-08-commodity-routing.md`)
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

- ✅ {What was tested}
- ✅ {What was verified}

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

## Example

See `ai-swap/commodity-based-routing.md` for reference.

The goal is maximum effectiveness per token: future Claude should understand the session's context, key decisions, and be able to continue work without re-discovering everything.
