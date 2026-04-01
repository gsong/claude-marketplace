---
name: gs:ai-docs:audit
description: "Comprehensive audit of docs-ai/ documentation using coordinated agent teams. Use when the user wants a full review of all documentation for accuracy, completeness, and quality. Heavier than docs-ai-update — use for periodic deep reviews, not routine maintenance."
---

# Audit Docs AI

Comprehensive documentation audit using parallel agent teams. Three phases: structural analysis → content review (parallel fanout) → apply edits + QA.

## Goal

Improve docs as quick reference material for Claude Code lookups. Prioritize:

- **Accuracy**: Verify information matches current codebase
- **Effectiveness**: Easy to find answers without extensive searching
- **Conciseness**: `file::Symbol` references over code snippets, brief explanations
- **Consistency**: Uniform terminology, formatting, and cross-references across all docs

## Process

### Phase 1: Structural Analysis

#### 1. Resolve Docs Directory

Check these locations in order. Use the **first match**:

1. `docs-ai/`
2. `docs/ai/`
3. `.claude/docs/`

If more than one exists, emit a warning: "Multiple docs directories found: [list]. Using [chosen]. Consider consolidating to a single location."

If none exist, output: "No docs-ai directory found. Run `/ai-docs:docs-ai-init` to bootstrap documentation."

#### 2. Spawn Analyst Agent

Spawn a single analyst agent (Explore type, read-only). Include the shared analysis prompt:

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/project-analysis-prompt.md"`

> **Resource fallback:** If the above is empty, the plugin may not be installed correctly. Try reading the resource relative to the skill directory: `$(dirname "${CLAUDE_SKILL_DIR}")/../resources/project-analysis-prompt.md`.

In addition to the project analysis, the analyst must also evaluate the existing docs:

- Read all current docs in `[docs-dir]/`
- **Gaps**: Topics that should be documented but aren't
- **Redundancy**: Overlapping content that should be consolidated
- **Extraneous docs**: Docs that don't match current codebase reality
- **README.md format compliance**: Verify against the canonical format:

  !`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-ai-readme-format.md"`

  > **Resource fallback:** If the above is empty, the plugin may not be installed correctly. Try reading the resource relative to the skill directory: `$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-ai-readme-format.md`.

The analyst returns structured findings:

- Files to add (with rationale)
- Files to remove (with rationale)
- Files to consolidate (merge suggestions)
- README.md updates needed
- README.md format issues

#### 3. Present Findings

Show the analyst's findings to the user. Ask for approval before proceeding to Phase 2.

Apply any approved structural changes (create/remove/consolidate files) before content review.

### Phase 2: Content Review (Parallel Fanout)

#### 4. Spawn Reviewer Agents

Spawn parallel **read-only** reviewer agents using the Agent tool (Explore type). Assign each reviewer 1 doc (or 2-3 related docs for small files).

Each reviewer's prompt must include:

- Its assigned doc file path(s)
- Relevant Phase 1 findings for those docs
- Instructions to return structured results (not edit files)

Each reviewer reads its assigned doc(s) and the relevant source code, then returns:

- **Accuracy issues**: Information that doesn't match the codebase (with proposed fix text)
- **Outdated content**: Sections that should be removed or rewritten
- **Code-to-reference**: Code snippets that should be `file::Symbol` references instead
- **Cross-doc issues**: Overlap with other docs, stale cross-references
- **Conciseness**: Verbose explanations that could be shortened

#### 5. Consolidate Results

Collect all reviewer results. Resolve cross-doc conflicts (if reviewer A and reviewer B both flagged overlapping content, decide which doc gets canonical ownership). Present the consolidated edit plan to the user for approval.

### Phase 3: Apply + QA

#### 6. Apply Edits

Apply all approved edits. Either:

- Apply directly (if changes are straightforward)
- Spawn a single writer agent with the full edit plan

#### 7. QA Check

Spawn a QA agent (Explore type, read-only) with:

- All docs (post-edit)
- Phase 1 analyst findings (to verify recommendations were addressed)
- Phase 2 cross-doc issues (to verify conflicts were resolved)

QA validates:

- Cross-references between docs point to real sections
- Spot-check `file::Symbol` references (do files/symbols exist?)
- Consistency: terminology, formatting, heading styles, voice
- Phase 1 recommendations were addressed

QA reports all issues found — both minor (typos, broken links, formatting) and significant. The orchestrating agent then applies minor fixes directly and presents significant issues for manual resolution.

#### 8. Summary

Present to user:

- Total docs reviewed
- Changes made (edits, additions, removals)
- Remaining issues (if any QA findings need manual attention)
