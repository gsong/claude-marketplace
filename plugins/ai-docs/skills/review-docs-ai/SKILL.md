---
name: review-docs-ai
description: Use when the user wants to review, audit, or improve AI-optimized documentation, or coordinate an agent team to verify and edit docs-ai files. Also use when the user invokes /review-docs-ai.
---

# Review Docs AI

Review and edit all AI-optimized documentation using an agent team for coordinated, high-accuracy results.

## Goal

Improve docs as quick reference material for Claude Code lookups. Prioritize:

- **Accuracy**: Verify information matches current codebase
- **Effectiveness**: Easy to find answers without extensive searching
- **Conciseness**: File references over code snippets, brief explanations
- **Consistency**: Uniform terminology, formatting, and cross-references across all docs

## Execution

You are the **team lead**. Use delegate mode (Shift+Tab) during Phase 2 to stay in coordination-only mode.

### Setup

1. **Discover docs directory**: Check these locations in order:
   - `docs-ai/`
   - `docs/ai/`
   - `.claude/docs/`
   - If none exist, ask user for location
2. **Create team**: Use TeamCreate with name `docs-review`

### Phase 1: Structural Analysis

1. **Spawn analyst teammate**: Use Task tool with `team_name: "docs-review"`, `name: "analyst"`, general-purpose subagent type. Analyst prompt must instruct it to:
   - **Project context**: Read key project files (package.json, go.mod, Cargo.toml, etc.) to understand project type and tech stack
   - **Codebase patterns**: Use Glob/Grep to identify major patterns (components, routes, state management, API endpoints, etc.)
   - **Existing docs**: Read all current docs to understand what's covered
   - **Documentation gaps**: Identify missing topics that should be documented based on project complexity
   - **Redundancy**: Find overlapping content that should be consolidated
   - **Extraneous docs**: Identify docs that don't match current codebase reality
   - **README.md accuracy**: Verify the documentation map accurately reflects available docs and their headings
   - **README.md format compliance**: Verify README.md follows the canonical format:

     !`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-ai-readme-format.md"`

   Analyst messages the lead with:
   - **Files to add**: List with rationale
   - **Files to remove**: List with rationale
   - **Files to consolidate**: Merge suggestions with rationale
   - **README.md updates needed**: Sections to add/remove/reorganize
   - **README.md format issues**: Deviations from canonical format that need fixing

2. **Present recommendations**: Show the analyst's findings to the user and ask for approval before proceeding
3. **Apply structural changes**: Create/remove/consolidate files per approved recommendations. The analyst stays alive for Phase 2.

### Phase 2: Content Review

1. **Create tasks**: Use TaskCreate to add one task per doc file to the shared task list. Each task description should include:
   - The doc file path
   - Relevant findings from the structural analysis (e.g., "this doc overlaps with X", "references to Y may be stale")

2. **Spawn reviewer teammates**: Spawn reviewers scaled to doc count (~3-4 docs per reviewer, cap at 5 reviewers). Use Task tool with `team_name: "docs-review"`, `name: "reviewer-N"`, general-purpose subagent type. Each reviewer's prompt must instruct them to:

   **For each claimed task from the task list:**
   1. **Read assigned doc** — Understand current content
   2. **Verify accuracy** — Check referenced files/code exist and are correct
   3. **Remove unnecessary content**:
      - Outdated information
      - Verbose explanations that could be one line
      - Code snippets that could be file::Symbol references
      - Redundant information covered elsewhere
   4. **Edit for effectiveness**:
      - Use file::Symbol references (e.g., `src/store/useAppStore.ts::useAppStore`) instead of code blocks
      - Keep explanations concise and scannable
      - Ensure headings clearly indicate content
      - Focus on "what Claude Code needs to know" not "what humans want to read"
   5. **Coordinate with teammates**:
      - When finding content that overlaps with another doc, message that doc's reviewer to agree on where canonical info lives
      - When discovering stale references or renamed code, broadcast to all reviewers
      - When unsure about codebase patterns or structural analysis intent, message the analyst
      - When adding a cross-reference to another doc, message that doc's reviewer to confirm the target section exists
   6. **Mark task complete** via TaskUpdate, then self-claim the next unblocked task from the task list

3. **Wait for all review tasks to complete**. Do not edit docs yourself — coordinate only.

### Phase 3: Quality Assurance

1. **Spawn QA teammate**: Use Task tool with `team_name: "docs-review"`, `name: "qa"`, general-purpose subagent type. QA prompt must instruct it to:
   - Read every doc file that was edited in Phase 2
   - **Validate cross-references**: Ensure links between docs point to real sections that exist
   - **Validate file::Symbol references**: Spot-check that referenced symbols exist in the referenced files (grep for the symbol name)
   - **Check consistency**: Terminology, formatting, heading styles, and voice should be uniform across all docs
   - **Check completeness**: Verify the structural analysis recommendations from Phase 1 were addressed
   - **Fix minor issues directly**: Typos, broken links, formatting inconsistencies
   - **Report significant issues**: Message the lead with a prioritized list of anything requiring reviewer attention

2. **Address QA findings**: For significant issues, message the relevant reviewer to fix. For anything remaining, fix directly.

### Cleanup

1. **Shut down all teammates**: Send shutdown requests (via SendMessage with `type: "shutdown_request"`) to analyst, all reviewers, and QA
2. **Clean up team**: Use TeamDelete after all teammates confirm shutdown
3. **Summarize**: Present total changes across all docs to the user
