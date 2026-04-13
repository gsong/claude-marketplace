---
name: gs:gh-tools:review
description: Use when the user wants a comprehensive code review for a GitHub pull request, or when the user invokes /gs:gh-tools:review with a PR number.
---

# PR Review

Perform a comprehensive code review for PR #$ARGUMENTS

**All output goes to `ai-swap/pr-review-$ARGUMENTS/` — never post comments to GitHub directly.**

## Setup

Locate the schema validator (used in Phase 3 and Phase 4):

```bash
VALIDATOR="${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py"
if [ ! -f "$VALIDATOR" ]; then echo "ERROR: validate-findings.py not found at $VALIDATOR" >&2; exit 1; fi
```

Use `uv run "$VALIDATOR" <file>` for all validation commands below.

## Phase 1: Setup

1. **Clean output directory:** Remove stale artifacts from prior runs so they don't interfere:
   ```bash
   rm -f ai-swap/pr-review-$ARGUMENTS/findings-gh-review.json ai-swap/pr-review-$ARGUMENTS/general-comments.md
   ```
   Only delete artifacts this skill produces (`findings-gh-review.json`) or that become stale after a new review (`general-comments.md` from post-comments). Never delete `findings.json` — it contains the user's curated triage decisions and cannot be regenerated.
2. Checkout the PR branch: `gh pr checkout $ARGUMENTS`
3. Get PR metadata: `gh pr view $ARGUMENTS --json title,body,files,additions,deletions,headRefOid`
4. Get repo name: `gh repo view --json nameWithOwner --jq .nameWithOwner`
5. Get PR diff: `gh pr diff $ARGUMENTS`
6. Store all of the above — you will pass metadata to review agents and everything to the synthesis agent.

## Phase 2: Reviews (parallel)

Launch these two agents **in a single message** so they run in parallel.

Both agents receive this preamble at the top of their prompt:

> **CRITICAL: Do NOT post comments, reviews, or any content to the GitHub PR. Do NOT use `gh pr comment`, `gh api` to create reviews, or any other mechanism to write to the PR. Do NOT write to any files. Your ONLY job is to analyze the code and return your findings as text output.**

### Agent 1: superpowers:code-reviewer (Agent tool)

- `subagent_type`: `superpowers:code-reviewer`
- Prompt must include:
  - The no-posting preamble above
  - PR metadata (title, body, file list with additions/deletions)
  - "Review PR #$ARGUMENTS. Focus on: architecture, design patterns, maintainability, and testing philosophy. Return your findings as structured text. For each finding include: file path, line number(s), severity (must-fix / should-fix / nit), and description."

### Agent 2: feature-dev:code-reviewer (Agent tool)

- `subagent_type`: `feature-dev:code-reviewer`
- Note: this agent type lacks Bash access — it physically cannot run `gh` commands or post to GitHub.
- Prompt must include:
  - The no-posting preamble above
  - PR metadata (title, body, file list with additions/deletions)
  - "Review PR #$ARGUMENTS. The PR branch is already checked out — read the local files directly. Focus on: bugs, logic errors, security vulnerabilities, code quality, and adherence to project conventions. Return your findings as structured text. For each finding include: file path, line number(s), severity (must-fix / should-fix / nit), confidence score (0-100), and description."

Wait for both agents to complete before proceeding.

## Phase 3: Synthesis (single agent)

Launch one agent (Agent tool) to write the final report and structured JSON. Pass it everything it needs in the prompt — this agent starts with a clean context.

- `subagent_type`: `general-purpose`

### Synthesis agent prompt

Include ALL of the following in the agent's prompt:

1. A synthesis-specific preamble: **"CRITICAL: Do NOT post comments, reviews, or any content to the GitHub PR. Do NOT use `gh pr comment`, `gh api` to create reviews, or any other mechanism to write to the PR. Do NOT run any `gh` commands. You MUST write output files under `ai-swap/` as instructed below — that is your primary job."**
2. PR number: $ARGUMENTS
3. Head SHA, repo name, and full PR diff (from Phase 1)
4. Full text output from Agent 1 (superpowers:code-reviewer findings)
5. Full text output from Agent 2 (feature-dev:code-reviewer findings)
6. The review focus areas (below)
7. The output format specs (below)
8. The validator step (below)
9. The hard gate (below)

#### Review focus areas

- User-facing behavior correctness
- Maintainability
- Testing philosophy (minimize mocks, test real implementations)
- Test quality and value:
  - Flag tests that don't assert meaningful behavior (e.g., testing trivial getters/setters, re-testing framework behavior)
  - Flag tests that duplicate coverage already provided by other tests in the codebase — check for existing integration tests that already cover the path
  - Prefer integration tests that verify overall behavior over unit tests, unless the unit has complex standalone logic worth isolating
  - Tests that only exist to bump coverage without catching real bugs should be flagged for removal

Skip praise and lengthy analysis — actionable items only.

#### Instructions for the synthesis agent

1. **Filter and organize only.** Do not introduce new findings — your job is to deduplicate, categorize, and map the agents' findings. Use the review focus areas above as a lens for prioritization, not as a prompt for new analysis.
2. **Deduplicate:** Merge findings that describe the same issue from both agents into one item. Keep the higher severity.
3. **Categorize** by severity and actionability.
4. **Use the PR metadata provided in the prompt** (head SHA, repo name, and diff — all fetched by the orchestrator in Phase 1). Do NOT run any `gh` commands.
5. **Map findings to diff positions.** For each finding from the review agents — include anything that has not been actively disproven. Only exclude findings that are confirmed false positives or duplicates of another included finding. Do not exclude findings just because they scored below a threshold or were categorized as low-severity — if the issue is real, include it:
   - Identify the `path` (file path relative to repo root)
   - Identify the `line` (end line in the new version of the file) and optional `start_line` (for multi-line ranges)
   - Verify both `line` and `start_line` fall within a diff hunk for that file — if not, include the finding in `findings-gh-review.json` with `"unmappable": true` set on it. Do not exclude any findings from the JSON based on diff position.
   - Set `severity` to `must-fix`, `should-fix`, or `nit` based on the finding's categorization
   - Set `side` to `LEFT` only if the comment targets a deleted line; otherwise omit (defaults to `RIGHT`)
   - Validate `body` is under 65536 characters

6. **Write `ai-swap/pr-review-$ARGUMENTS/findings-gh-review.json`:** The file MUST be named exactly `findings-gh-review.json`, NOT `findings.json`. The downstream triage skill globs for `findings-*.json` to discover source files — `findings.json` is reserved for triage's own output and will be ignored.

   **REQUIRED top-level fields** (validation fails without these):
   - `"source"`: always `"gh-review"` for this skill
   - `"pr"`, `"repo"`, `"head_sha"`, `"findings"`

   **REQUIRED fields on every finding** (validation fails without these):
   - `"path"`, `"line"`, `"body"`, `"severity"`, `"source_detail"`

```json
{
  "source": "gh-review",
  "pr": $ARGUMENTS,
  "repo": "owner/repo",
  "head_sha": "<commit SHA>",
  "findings": [
    {
      "path": "relative/file/path.ts",
      "line": 45,
      "start_line": 38,
      "body": "Comment text with **markdown** support",
      "severity": "must-fix",
      "source_severity": "must-fix",
      "confidence": 85,
      "title": "Short title for the finding",
      "recommendation": "Concrete fix suggestion",
      "source_detail": [
        {
          "skill": "gs:gh-tools:review",
          "agent": "superpowers:code-reviewer",
          "agent_label": "architecture & design"
        }
      ]
    }
  ]
}
```

`source_detail` is **always an array**, even for single-source findings. For findings both agents flagged, include both entries:

```json
"source_detail": [
  {"skill": "gs:gh-tools:review", "agent": "superpowers:code-reviewer", "agent_label": "architecture & design"},
  {"skill": "gs:gh-tools:review", "agent": "feature-dev:code-reviewer", "agent_label": "bugs & security"}
]
```

The body should note when both agents flagged the same issue.

`title` and `recommendation` are optional — include when the reviewer provided them.

`unmappable` is only set when `true` — omit it for findings that map to valid diff positions.

**You MUST write this file even if zero findings** (use `"findings": []`).

7. **Report** how many findings were mapped to diff positions and how many were flagged as unmappable.

8. **Run the schema validator** on the findings file:

   ```bash
   uv run "$VALIDATOR" ai-swap/pr-review-$ARGUMENTS/findings-gh-review.json
   ```

   If validation fails, fix the errors in the JSON and re-validate before proceeding.

#### Hard gate

> **You MUST write `findings-gh-review.json` before completing. After writing it, confirm it was written by reading it back with the Read tool. Run the schema validator and confirm it passes. Do not return until the file exists and is valid.**

Wait for the synthesis agent to complete before proceeding.

## Phase 4: Verification

After the synthesis agent completes, the orchestrator (you) verifies the output:

1. Check that `ai-swap/pr-review-$ARGUMENTS/findings-gh-review.json` exists: `ls ai-swap/pr-review-$ARGUMENTS/findings-gh-review.json`
2. **Check for wrong filename:** `ls ai-swap/pr-review-$ARGUMENTS/findings.json` — if this file exists:
   - If `findings-gh-review.json` does NOT exist: the synthesis agent used the wrong name. Rename it: `mv ai-swap/pr-review-$ARGUMENTS/findings.json ai-swap/pr-review-$ARGUMENTS/findings-gh-review.json` and warn the user.
   - If `findings-gh-review.json` ALSO exists: `findings.json` is likely from a previous triage run containing the user's curated decisions. **Do not auto-delete.** Warn the user and ask (via AskUserQuestion) whether to delete it or keep it. It won't interfere with the new review output, but may be stale.
3. If `findings-gh-review.json` is still missing after step 2: report the failure to the user. Show what the synthesis agent returned so the user can debug.
4. If the file exists:
   - **Run the schema validator** (the synthesis agent may have skipped it):
     ```bash
     uv run "$VALIDATOR" ai-swap/pr-review-$ARGUMENTS/findings-gh-review.json
     ```
     If validation fails, fix the JSON yourself (common issues: missing top-level `"source": "gh-review"`, missing `"source_detail"` on findings) and re-validate until it passes.
   - Show the synthesis agent's summary (finding counts, mapped vs unmappable)
   - If step 2 renamed the file, warn: "The synthesis agent wrote `findings.json` instead of `findings-gh-review.json` — renamed automatically, but this indicates the agent didn't follow the naming instruction."
   - Remind the user: "Run `/gs:gh-tools:triage $ARGUMENTS` to investigate and curate findings before posting."
