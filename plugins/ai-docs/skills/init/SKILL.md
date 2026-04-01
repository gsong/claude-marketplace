---
name: gs:ai-docs:init
description: Use when the user wants to bootstrap or initialize AI-optimized documentation for a project, or set up a docs-ai directory. Also use when the user invokes /gs:ai-docs:init.
---

# Initialize Docs AI

Bootstrap a `docs-ai/` directory structure with auto-populated content for Claude Code documentation lookups.

## Goal

Create AI-optimized documentation that enables effective Claude Code assistance via the docs-ai-lookup skill. Unlike v1, this produces **real content** (not just TODO stubs) by reading source files identified during analysis.

## Process

### 1. Check Prerequisites

Search for existing docs in all supported locations (in order):

1. `docs-ai/`
2. `docs/ai/`
3. `.claude/docs/`

If more than one exists, warn: "Multiple docs directories found: [list]."

If any found, ask the user which mode:

- **Fresh start** — delete existing directory and recreate from scratch
- **Refresh** — re-analyze project structure, add missing docs, flag extraneous docs, but preserve existing content in files that are still relevant

If not found, proceed with creation in `docs-ai/`.

### 2. Analyze Project

Spawn an analyst subagent (Explore type, read-only). Include this shared analysis prompt in the subagent's instructions:

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/project-analysis-prompt.md"`

> **Resource fallback:** If the above is empty, the plugin may not be installed correctly. Try reading the resource relative to the skill directory: `$(dirname "${CLAUDE_SKILL_DIR}")/../resources/project-analysis-prompt.md`.

The analyst produces:

- Project overview, tech stack, recommended docs with rationale
- For each recommended doc: suggested section headings AND the source files/patterns that would populate each section

### 3. Present Recommendations

Show analysis to user with recommendations. Ask for approval/modifications before creating files.

User can:

- Accept all recommendations
- Remove docs they don't want
- Add docs not suggested
- Modify category structure

### 4. Create Directory Structure

```
[docs-dir]/
├── README.md (documentation map — always created)
├── quick-reference.md (cheat sheet — always created)
├── architecture.md (tech stack overview — always created)
└── [approved docs from recommendations]
```

### 5. Auto-Populate Content

Spawn content-writer agents (parallelized, ~3-4 docs per agent). Each writer:

- Reads the relevant source files identified by the analyzer
- Writes real content using `file::Symbol` references (not code blocks)
- Keeps it concise — lookup reference, not tutorial
- Marks unpopulatable sections with rich stubs:

  ```markdown
  ## [Section Name]

  <!-- NEEDS CONTENT: Describe [specific thing].
       Start by reading: src/auth/middleware.ts::authMiddleware
       Key questions to answer:
       - How are tokens validated?
       - What's the refresh flow?
       Example format: "Tokens are validated via file::Symbol. Refresh uses..." -->
  ```

### 6. Generate README.md

Load the canonical README format:

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-ai-readme-format.md"`

> **Resource fallback:** If the above is empty, the plugin may not be installed correctly. Try reading the resource relative to the skill directory: `$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-ai-readme-format.md`.

Populate `[docs-dir]/README.md` following this format exactly.

**Verification:** Before presenting to the user, check that every `.md` file in the docs directory (except README.md and quick-reference.md) appears in the topic index. If any are missing, add them.

### 7. Summary

Show:

1. **Files created**: List with line counts
2. **Stubs needing attention**: Files/sections with `<!-- NEEDS CONTENT` markers, listed explicitly
3. **Next steps**: Suggest filling stubs manually or running `/ai-docs:docs-ai-update` after making related code changes

## Execution Notes

- Create all files using Write tool
- Do not create `.claude/agents/` or modify `.claude/CLAUDE.md` — the plugin handles docs-ai-lookup and reminders via its built-in skill and hook
- Use `file::Symbol` references throughout (e.g., `src/store/useAppStore.ts::useAppStore`), not code blocks
