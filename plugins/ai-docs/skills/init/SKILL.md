---
name: "gs:ai-docs:init"
description: "Bootstraps a docs-ai/ directory — analyzes the project, generates docs with auto-populated content, builds the README topic index, and stamps everything. Use when the user wants to bootstrap or initialize AI-optimized documentation for a project, or set up a docs-ai directory. Also use when the user invokes /gs:ai-docs:init."
---

# Initialize Docs AI

Bootstrap a `docs-ai/` directory structure with auto-populated content for Claude Code documentation lookups.

## Goal

Create AI-optimized documentation that enables effective Claude Code assistance via the gs:ai-docs:lookup skill. This produces **real content** (not just TODO stubs) by reading source files identified during analysis.

## Process

### 1. Check Prerequisites

Resolve existing docs directories with the shared rules, so init agrees with every other skill about what already exists:

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-dir-resolution.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/docs-dir-resolution.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

If any docs directory is found, ask the user which mode, and which directory it applies to when there is more than one:

- **Fresh start** — delete the existing directory and recreate from scratch
- **Refresh** — re-analyze project structure, add missing docs, flag extraneous docs, but preserve existing content in files that are still relevant

If none is found, decide **where** the new directory goes before creating anything:

- **Single-package project** — `docs-ai/` at the project root.
- **Monorepo** — one `docs-ai/` per workspace that a developer works in, at that workspace's root (`apps/woody/docs-ai/`), so its Key Paths stay relative to its own code and the package can move without a rewrite. A root `docs-ai/` earns its place only for genuinely cross-cutting topics — the build graph, the deploy pipeline, shared conventions — and its Key Paths then point at repo-root paths like `turbo.json` or `packages/ui/`.

Bootstrapping a whole monorepo in one pass produces a lot of docs of uneven value. Propose the workspace (or the small set of workspaces) to start with, and let the user confirm the placement before step 2.

### 2. Analyze Project

Spawn an analyst subagent (Explore type, read-only). Include this shared analysis prompt in the subagent's instructions:

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/project-analysis-prompt.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/project-analysis-prompt.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

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

Create the directory at the location confirmed in step 1. The directory it sits in — the project or workspace root, not an intermediate `docs/` or `.claude/` — is the `[path-root]` that all Key Paths will be written against.

```
[docs-dir]/
├── README.md (documentation map — always created)
├── quick-reference.md (cheat sheet — always created)
├── architecture.md (tech stack overview — always created)
└── [approved docs from recommendations]
```

### 5. Auto-Populate Content

Spawn content-writer agents (general-purpose type — writers need Write, which Explore lacks; parallelized, ~3-4 docs per agent). Each writer:

- Reads the relevant source files identified by the analyzer
- Writes real content using `file::Symbol` references (not code blocks), with paths relative to `[path-root]` — for `apps/woody/docs-ai/`, write `app/routes.ts::routes`, not `apps/woody/app/routes.ts::routes`
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

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/docs-ai-readme-format.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

Populate `[docs-dir]/README.md` following this format exactly.

**Verification:** Before presenting to the user, check that every `.md` file in the docs directory (except README.md and quick-reference.md) appears in the topic index. If any are missing, add them.

### 7. Stamp Docs

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/verification-stamp.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/verification-stamp.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

Stamp every file in the docs directory (including README.md and quick-reference.md). The stamp records which commit the docs were generated against. gs:ai-docs:check and gs:ai-docs:lookup use it as the staleness baseline.

If the working tree has uncommitted changes, note in the summary that docs were generated against HEAD plus uncommitted changes.

### 8. Summary

Show:

1. **Files created**: List with line counts
2. **Stubs needing attention**: Files/sections with `<!-- NEEDS CONTENT` markers, listed explicitly
3. **Next steps**: Suggest filling stubs manually or running `/gs:ai-docs:update` after making related code changes

## Execution Notes

- Create all files using Write tool
- Do not create `.claude/agents/` or modify `.claude/CLAUDE.md` — the plugin handles gs:ai-docs:lookup and reminders via its built-in skill and hook
- Use `file::Symbol` references throughout (e.g., `src/store/useAppStore.ts::useAppStore`), not code blocks
