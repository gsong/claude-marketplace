# Review Project Memory

Analyze the project-level CLAUDE.md file for effectiveness and token efficiency.

## Analysis Framework

Evaluate `.claude/CLAUDE.md` across these dimensions:

1. **Clarity**: Are instructions unambiguous and actionable?
2. **Conciseness**: Can anything be more concise without losing meaning?
3. **Value Density**: Token cost vs. utility (high-impact vs. low-value instructions)
4. **Redundancy**: Does it duplicate global instructions?
5. **Specificity**: Is it truly project-specific or too general?
6. **Organization**: Is it structured for quick scanning?
7. **Examples**: Are code examples minimal and necessary, or could they be shorter?

## Effectiveness Criteria

**High-value instructions:**

- Prevent repeated mistakes or questions
- Context that's not discoverable from code
- Project-specific workflows that differ from defaults
- Critical warnings (with **CRITICAL** prefix)
- Common patterns with non-obvious gotchas

**Low-value instructions:**

- Generic best practices (already in global CLAUDE.md)
- Obvious information discoverable from code
- Outdated guidance no longer relevant
- Overly verbose examples

## Output Format

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

Provide an optimized version of the entire CLAUDE.md file

## Principles

- Optimize for token efficiency without sacrificing effectiveness
- Prioritize project-specific context over general advice
- Keep examples minimal but clear
- Use bullet points over paragraphs
- Remove redundancy with global instructions
