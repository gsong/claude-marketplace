---
name: gs:codex-tools:review
description: Code review a pull request using parallel Codex adversarial reviews. Use when the user asks for a Codex code review, wants a GPT-based review, or invokes /gs:codex-tools:review.
---

# Codex Code Review

Review a pull request using 3 parallel Codex adversarial reviews, each with a
specialized focus area.

## Arguments

- **Required:** PR number (first positional argument)
- **Optional flags:**
  - `--model <model>` — Codex model (passed through to adversarial-review)

## Process

Follow these steps precisely:

### Step 1: Eligibility & Context Gathering

Run these directly (no subagents):

1. `gh pr view <number> --json state,additions,deletions,title,body,author,comments,labels,baseRefName` — check eligibility:
   - If closed → stop
   - If < 5 lines changed → stop
   - Drafts ARE allowed
2. Parse the PR body and comments for issue references:
   - **GitHub issues:** `#123` or full GitHub issue URLs → resolve via `gh issue view <number> --json title,body`
   - **Other references** (Linear URLs, Jira IDs, etc.): include the raw reference text in the context block. Instruct agents to resolve using available skills/tools if present.
   - If resolution fails for any reference, include the raw text and move on.
3. Build a **PR context block** to prepend to each agent's focus text:

<!-- prettier-ignore -->
```text
PR #<number>: "<title>"
Author: <author>
Description: <body, truncated to ~500 chars if long>
Labels: <labels>
PR Comments: <conversation comments, truncated>
Referenced Issues:
- #<gh-issue>: <title> — <body summary>
- <external-ref>: (agent should resolve using available tools)
```

4. Check out the PR branch locally:

```bash
gh pr checkout <number>
```

5. Determine the base ref from the PR metadata (`baseRefName` from the `gh pr view` output).

6. Resolve the codex companion script path:

```bash
find ~/.claude/plugins/cache -name "codex-companion.mjs" -path "*/codex/*" | sort -V | tail -1
```

If no path is found, stop with: "Error: codex plugin not installed. Run `/codex:setup` first."

### Step 2: Parallel Agent Dispatch

Launch **3 parallel agents** (using the Agent tool, `subagent_type: "general-purpose"`). Pass each agent:

- The resolved companion script path from Step 1.6
- The base ref from Step 1.5
- The PR context block
- Its agent-specific focus text
- The `--model` flag if one was passed to the skill

Each agent:

1. Writes its full focus text (PR context block + agent-specific focus) to a temp file
2. Invokes adversarial-review via Bash using the companion script path:

```bash
node "<companion-path>" adversarial-review --base <base-ref> --wait -- "$(cat <temp-file>)"
```

- `--wait` ensures foreground execution (no interactive prompts)
- `--` separates flags from focus text to prevent misparse
- If `--model` was passed, add it before `--`: `--model <model>`

3. Captures the structured JSON output (verdict, findings, next_steps)
4. For any external issue references encountered, attempts resolution using available skills/tools
5. Returns the parsed findings

**The 3 agent roles and focus text:**

**Agent A — Correctness & Safety:**

Prepend the PR context block, then:

> Focus on logical correctness: off-by-one errors, null/undefined paths, type coercion bugs, boundary conditions, error handling gaps, and security boundaries (injection, auth bypass, data exposure). Trace data flow through changed functions.

**Agent B — Concurrency, State & Integration:**

Prepend the PR context block, then:

> Focus on state management, race conditions, resource lifecycle (leaks, dangling references, unclosed handles), API contract violations, backwards compatibility breaks, and how changes interact with code outside the diff. Check git history for reverted patterns or repeated mistakes in modified files.

**Agent C — Test & Specification Integrity:**

Prepend the PR context block, then:

> Focus on whether tests verify the claimed behavior change, whether assertions are meaningful or tautological, whether edge cases from the implementation are covered, and whether existing tests or code comments are now stale or misleading due to the changes.

### Step 3: Result Aggregation

After all 3 agents return:

1. **Collect** — each agent returns structured JSON with `verdict`, `summary`, `findings[]`, and `next_steps[]`. The findings schema:

```json
{
  "severity": "critical | high | medium | low",
  "title": "finding title",
  "body": "description of the issue",
  "file": "path/to/file",
  "line_start": 10,
  "line_end": 20,
  "confidence": 0,
  "recommendation": "concrete fix suggestion"
}
```

2. **Deduplicate** — if two agents flag the same file + overlapping line range, merge into one finding. Keep the higher severity. Combine descriptions, noting which agent perspectives caught it.
3. **Overall verdict** — `needs-attention` if any agent returns `needs-attention`; `approve` only if all three approve.
4. **Sort** — by severity (critical → high → medium → low), then confidence descending.

### Step 4: Output Results

**Terminal output:**

Display all findings grouped by severity:

<!-- prettier-ignore -->
```text
## Codex Code Review — PR #<number>

### Summary
<PR title + brief description>

### Issues Found (N total)

**Critical / High**

1. [<severity>/<agent>] <file>:<lines> — <title> (confidence: <score>)
   <body>
   Recommendation: <recommendation>

**Medium / Low**

2. [<severity>/<agent>] <file>:<lines> — <title> (confidence: <score>)

### No Issues From
- <list agents that found nothing>
```

If no issues found at all:

<!-- prettier-ignore -->
```text
## Codex Code Review — PR #<number>

No issues found. Checked correctness, integration safety, and test quality
using 3 parallel Codex adversarial reviews.
```

**Markdown report:**

Write the full report (all findings) to `ai-swap/pr-review-<number>/codex-review.md` using the Write tool. Include agent source for each finding.

## Notes

- Use `gh` to interact with GitHub, not web fetch
- Do not check build signal or attempt to build/typecheck
- **Do not auto-apply fixes.** Present findings and let the user decide what to fix.
- **Do not pre-read source files to embed in prompts.** Codex reads files itself via the companion script's read-only sandbox. Only pass the PR context (which Codex can't access from GitHub) and the focus text.
- All adversarial-review invocations use `--wait` for foreground execution
- Make a todo list first to track progress through the steps
