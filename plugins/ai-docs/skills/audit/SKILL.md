---
name: "gs:ai-docs:audit"
description: "Comprehensive audit of docs-ai/ documentation using coordinated agent teams. Use when the user wants a full review of all documentation for accuracy, completeness, and quality. Also use when the user invokes /gs:ai-docs:audit. Heavier than /gs:ai-docs:update — use for periodic deep reviews, not routine maintenance."
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

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-dir-resolution.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/docs-dir-resolution.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

#### 2. Spawn Analyst Agent

Spawn a single analyst agent (Explore type, read-only). Include the shared analysis prompt:

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/project-analysis-prompt.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/project-analysis-prompt.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

In addition to the project analysis, the analyst must also evaluate the existing docs:

- Read all current docs in `[docs-dir]/`. Source paths in those docs, and Key Paths in the README, are relative to `[path-root]` — join before reading or globbing, or every reference looks broken
- **Gaps**: Topics that should be documented but aren't
- **Redundancy**: Overlapping content that should be consolidated
- **Extraneous docs**: Docs that don't match current codebase reality
- **README.md format compliance**: Verify against the canonical format:

  !`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-ai-readme-format.md"`

  > **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/docs-ai-readme-format.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

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

Spawn parallel **read-only** reviewer agents using the Agent tool (Explore type). Assign each reviewer 1 doc (or 2-3 related docs for small doc sets with fewer than 4 total docs), and cap the fanout at 10 agents — a monorepo package can carry 30+ docs, and one agent each stops buying anything at that point. Above 10 docs, group related docs into 10 batches.

Each reviewer's prompt must include:

- Its assigned doc file path(s), plus `[path-root]` for resolving the code they reference
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

- Apply directly (edits touching ≤2 docs)
- Spawn a single writer agent (general-purpose type — it needs Write, which Explore lacks) with the full edit plan (3+ docs)

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

#### 8. Stamp Verified Docs

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/verification-stamp.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/verification-stamp.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

Stamp **every** doc in the docs directory (including README.md and quick-reference.md), not just edited ones — the audit verified them all against the current codebase. The audit covers the one `[docs-dir]` it resolved; if the project has other docs directories under other path roots, say so in the summary rather than implying the whole project was audited.

#### 9. Summary

Present to user:

- Total docs reviewed
- Changes made (edits, additions, removals)
- Remaining issues (if any QA findings need manual attention)
