---
name: gs:codex-tools:review
description: Code review a pull request using parallel Codex agents. Use when the user asks for a Codex code review, wants a GPT-based review, or invokes /gs:codex-tools:review.
---

# Codex Code Review

Review a pull request using OpenAI's Codex CLI via parallel agents.

## Arguments

- **Required:** PR number (first positional argument)
- **Optional flags:**
  - `--model <model>` — Codex model (default: `gpt-5.4`)
  - `--effort <level>` — Reasoning effort: low, medium, high, xhigh (default: `high`)
  - `--threshold <number>` — Confidence display threshold (default: `50`)

## Process

Follow these steps precisely:

### Step 1: Eligibility & Context Gathering

Run these directly (no subagents):

1. `gh pr view <number> --json state,additions,deletions,title,body,author` — check eligibility:
   - If closed → stop
   - If < 5 lines changed → stop
   - Drafts ARE allowed
2. `gh pr diff <number>` — save the full diff
3. Glob for CLAUDE.md files: check project root + directories containing modified files. Collect **file paths only** (not contents — Codex will read them itself).
4. Extract the list of modified file paths from the diff.

### Step 2: Parallel Codex Review

Launch **3 parallel agents** (using the Agent tool). Each agent:

1. Constructs a Codex prompt using the template below
2. Runs: `codex exec -m <model> -c model_reasoning_effort="<effort>" -s read-only --ephemeral "<prompt>"`
3. Parses the Codex output into structured JSON findings
4. Returns the findings

**Codex prompt template:**

All agent prompts follow this structure. Only embed context that Codex cannot access itself — Codex has read-only access to all project files and can run read-only commands like `git log` and `git blame`.

```
You are reviewing PR #<number> (<title>) in <repo>.
Author: <author>

## Your Role
<agent-specific role — see below>

## PR Diff
<full diff from gh pr diff>

## Modified Files
<list of file paths extracted from diff>

## Project Rules
<if CLAUDE.md files found>
The following CLAUDE.md files contain project rules. Read them yourself:
<list of file paths>
<else>
No CLAUDE.md files found.
<endif>

## Instructions
- You have read-only access to all project files. Read any file you need for context.
- Only flag issues in lines modified by this PR.
- Assign each issue a confidence score (0-100):
  - 0: False positive, pre-existing issue, or doesn't hold up to scrutiny
  - 25: Might be real but could be false positive. Stylistic issues not in CLAUDE.md.
  - 50: Verified real but possibly a nitpick or rare in practice
  - 75: Very likely real, impacts functionality or explicitly required in CLAUDE.md
  - 100: Confirmed, will happen frequently, evidence directly supports it
- For CLAUDE.md issues: read the file and verify the rule actually exists before flagging.
- Return each issue as a JSON object on its own line:
  {"file": "<path>", "lines": "<start>-<end>", "category": "<cat>", "confidence": <0-100>, "description": "<desc>"}
- If no issues: return {"no_issues": true}

## What NOT to flag
- Pre-existing issues not introduced in this PR
- Issues a linter, typechecker, or compiler would catch
- Pedantic nitpicks a senior engineer wouldn't mention
- Formatting, import ordering, or type annotation issues
- Intentional functionality changes
- General code quality unless explicitly required in CLAUDE.md
- Issues called out in CLAUDE.md but silenced in code (e.g. lint-ignore comments)
```

**The 3 agent roles:**

- **Agent A — CLAUDE.md + Code Comments Compliance:** "Audit the changes for compliance with the CLAUDE.md rules listed below. Read each CLAUDE.md file yourself and only flag violations that are specifically and directly called out. CLAUDE.md is guidance for writing code — not all rules apply during review. Also check that code comments in the modified files are still accurate after the changes. Flag cases where comments are now stale or misleading."

- **Agent B — Bug Scan + Git History:** "Scan the diff for bugs — focus on obvious issues with real impact, not nitpicks. Also run `git log` and `git blame` on the modified files to check for historical context: reverted patterns, repeated mistakes, or regressions. Ignore likely false positives."

- **Agent C — Test Quality:** "Evaluate any test files in the diff for quality and value. For each test, check: (1) Does it assert meaningful behavior, or is it testing something trivial (e.g., trivial getters/setters, re-testing framework behavior)? Flag low-value tests. (2) Are there existing tests in the codebase that already cover the same path? Run `grep` or read test files in the same directory to check for integration tests that already verify this behavior. Flag duplicates. (3) Are unit tests justified, or would an integration test better verify the overall behavior? Unit tests are fine for complex standalone logic, but prefer integration tests for verifying end-to-end behavior. (4) Flag tests that exist only to increase coverage without catching real bugs — these are a net negative. If no test files are in the diff, return {\"no_issues\": true}."

### Step 3: Output Results

**Terminal output:**

Display results grouped by confidence tier, filtered by `--threshold`:

```
## Codex Code Review — PR #<number>

### Summary
<PR title + brief description>

### Issues Found (N total, M shown above threshold)

**High Confidence (80+)**

1. [<category>] <file>:<lines> — <description> (confidence: <score>)

**Medium Confidence (50-79)**

2. [<category>] <file>:<lines> — <description> (confidence: <score>)

**Below Threshold**
N issues hidden (below confidence <threshold>). See full report.

### No Issues From
- <list agents that found nothing>
```

If no issues found at all:

```
## Codex Code Review — PR #<number>

No issues found. Checked for bugs, CLAUDE.md compliance, and test quality using Codex.
```

**Markdown report:**

Write the full report (all findings regardless of threshold) to `ai-swap/pr-review-<number>/codex-review.md` using the Write tool.

## Notes

- Use `gh` to interact with GitHub, not web fetch
- Do not check build signal or attempt to build/typecheck
- All Codex invocations use `--ephemeral` to avoid persisting sessions
- All Codex invocations use `-s read-only` sandbox mode
- **Do NOT pre-read source files or CLAUDE.md contents to embed in the Codex prompt.** Codex runs in `read-only` sandbox mode and can read files itself. Only embed the PR diff (from GitHub, which Codex cannot access) and tell Codex to read everything else.
- Shell-escape prompts properly when passing to `codex exec`
- Make a todo list first to track progress through the steps
