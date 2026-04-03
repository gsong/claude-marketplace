---
name: gs:gh-tools:review
description: Use when the user wants a comprehensive code review for a GitHub pull request, or when the user invokes /gs:gh-tools:review with a PR number.
---

# PR Review

Perform a comprehensive code review for PR #$ARGUMENTS

**All output goes to `ai-swap/pr-review-$ARGUMENTS/` - never post comments to GitHub directly.**

## Phase 1: Setup

1. Checkout the PR branch: `gh pr checkout $ARGUMENTS`
2. Get PR metadata: `gh pr view $ARGUMENTS --json title,body,files,additions,deletions`

## Phase 2: Initial Reviews (parallel)

Launch these two agents in parallel. **Agents return findings only - do not write to files.**

1. **superpowers:code-reviewer agent** (Task tool)
   - Prompt: "Review PR #$ARGUMENTS. Return your findings as structured output. Do not write to any files. Do not post comments to GitHub."

2. **/code-review:code-review skill** (Skill tool)
   - Run: `/code-review:code-review $ARGUMENTS`

Wait for both to complete before proceeding.

## Phase 3: Synthesis

**You (the orchestrator) write the final report.** Do not delegate this step.

1. Read the findings returned by both agents
2. Deduplicate issues (same issue from multiple agents = one item)
3. Categorize by severity and actionability
4. Write the consolidated report to `ai-swap/pr-review-$ARGUMENTS/review.md`

## Output Format

The final report must contain:

```markdown
# PR #$ARGUMENTS Review

## Decision: MERGE | NO MERGE

## Action Items

<!-- Issues that must be fixed before merge -->

## Needs Decision

<!-- Items requiring user input or clarification -->

## Findings by Source

### superpowers:code-reviewer

<!-- Summary of findings -->

### /code-review:code-review

<!-- Summary of findings -->
```

## Phase 4: Structured JSON Output

After writing the markdown report, also produce a machine-readable JSON file for `/gs:gh-tools:post-comments`.

1. Get the current PR head SHA: `gh pr view $ARGUMENTS --json headRefOid --jq .headRefOid`
2. Get the repo in `owner/repo` format: `gh repo view --json nameWithOwner --jq .nameWithOwner`
3. Get the PR diff: `gh pr diff $ARGUMENTS`
4. For each finding across **all** sections of the markdown report — include anything that has not been actively disproven. Only exclude findings that are confirmed false positives or duplicates of another included finding. Do not exclude findings just because they scored below a threshold or were categorized as low-severity — if the issue is real, include it:
   - Identify the `path` (file path relative to repo root)
   - Identify the `line` (end line in the new version of the file) and optional `start_line` (for multi-line ranges)
   - Verify both `line` and `start_line` fall within a diff hunk for that file — if not, skip the finding and note it was unmappable
   - Set `severity` to `must-fix`, `should-fix`, or `nit` based on the finding's categorization
   - Set `side` to `LEFT` only if the comment targets a deleted line; otherwise omit (defaults to `RIGHT`)
   - Validate `body` is under 65536 characters
5. Write the JSON to `ai-swap/pr-review-$ARGUMENTS/findings.json`:

```json
{
  "pr": $ARGUMENTS,
  "repo": "owner/repo",
  "head_sha": "<commit SHA>",
  "findings": [
    {
      "path": "relative/file/path.ts",
      "line": 45,
      "start_line": 38,
      "body": "Comment text with **markdown** support",
      "severity": "must-fix"
    }
  ]
}
```

6. Report how many findings were mapped to diff positions and how many were skipped.
7. Remind the user: "Run `/gs:gh-tools:post-comments $ARGUMENTS` to review and post these as GitHub PR comments."

## Review Focus

- User-facing behavior correctness
- Maintainability
- Testing philosophy (minimize mocks, test real implementations)
- Test quality and value:
  - Flag tests that don't assert meaningful behavior (e.g., testing trivial getters/setters, re-testing framework behavior)
  - Flag tests that duplicate coverage already provided by other tests in the codebase — check for existing integration tests that already cover the path
  - Prefer integration tests that verify overall behavior over unit tests, unless the unit has complex standalone logic worth isolating
  - Tests that only exist to bump coverage without catching real bugs should be flagged for removal

Skip praise and lengthy analysis - actionable items only.
