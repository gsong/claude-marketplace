---
name: "init"
description: "Bootstrap or refresh a docs-ai/ directory, one per workspace in a monorepo, with content generated from code analysis."
disable-model-invocation: true
---

# Initialize Docs AI

Bootstrap a `docs-ai/` directory structure with auto-populated content for Claude Code documentation lookups.

## Goal

Create AI-optimized documentation that enables effective Claude Code assistance via the ai-docs:lookup skill. This produces **real content** (not just TODO stubs) by reading source files identified during analysis.

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

In refresh mode, present the recommendations as three lists against the existing docs: add, keep, extraneous (with rationale).

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

Spawn content-writer agents, parallelized, ~3-4 docs per agent, each given the source files the analyzer identified for its docs and this brief:

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/doc-writer-brief.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/doc-writer-brief.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

In refresh mode a writer reads the existing doc first; every section whose `file::Symbol` references still resolve stays, sections describing removed code go, new sections are added.

### 6. Generate README.md

Load the canonical README format:

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-ai-readme-format.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/docs-ai-readme-format.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

Populate `[docs-dir]/README.md` following this format exactly.

**Verification:** Before presenting to the user, check that every `.md` file in the docs directory (except README.md and quick-reference.md) appears in the topic index. If any are missing, add them.

### 7. Stamp Docs

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/verification-stamp.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/verification-stamp.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

Stamp every file in the docs directory (including README.md and quick-reference.md).

### 8. Summary

Show:

1. **Files created**: List with line counts
2. **Stubs needing attention**: Files/sections with `<!-- NEEDS CONTENT` markers, listed explicitly
3. **Next steps**: Suggest filling stubs manually or running `/ai-docs:update` after making related code changes

## Execution Notes

- The docs directory is the whole deliverable; the plugin's hook and lookup skill are the only wiring, so leave `.claude/` untouched
