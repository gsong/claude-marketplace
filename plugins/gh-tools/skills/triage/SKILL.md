---
name: "triage"
description: "Merge, investigate and curate the findings of a PR review, then post or fix them. Run after gh-tools:review or codex-tools:review."
disable-model-invocation: true
compatibility: "Requires the gh CLI (authenticated) and uv for the bundled Python validator."
argument-hint: "<pr-number>"
---

# Triage Review

Investigate and triage code review findings for PR #$ARGUMENTS, then post them or fix them.

Triage decides each finding itself from its investigation. It asks the user only about **flagged** findings, and then once about what to do next.

## Input Parsing

`$ARGUMENTS` is a PR number. The review directory is `ai-swap/pr-review-$ARGUMENTS/`.

1. Delete `ai-swap/pr-review-$ARGUMENTS/triage-state.json` if it exists (`rm -f`). Older versions of this skill left it as a checkpoint. This version does not use it.
2. Glob for `findings-*.json` in the directory (this matches `findings-gh-review.json`, `findings-codex.json`, etc. but NOT `findings.json` which is triage's own output).
3. If no `findings-*.json` files are found, stop with: "No source findings found. Run `/gh-tools:review $ARGUMENTS` and/or `/codex-tools:review $ARGUMENTS` first."
4. If a previous `findings.json` exists in the directory, ask the user (via AskUserQuestion): "Previous triage output found. Start fresh from source findings, or abort so you can use the existing curated output?" Options: "Start fresh" (rebuild from source files), "Abort" (stop triage, keep existing findings.json). If abort, stop.

## Setup

Locate the schema validator (used throughout this skill):

```bash
if [ ! -f "${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py" ]; then echo "ERROR: validate-findings.py not found at ${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py" >&2; exit 1; fi
```

Every validation command below spells out the validator path. Claude Code replaces `${CLAUDE_PLUGIN_ROOT}` with the absolute plugin path when it loads this skill. Do not store it in a shell variable: each Bash call starts a new shell, so the variable would be gone by the next command.

## Phase 1: Merge Structured Findings

Execute directly — no subagent needed.

1. **Load and validate** each `findings-*.json` file:

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py" ai-swap/pr-review-$ARGUMENTS/<filename>
   ```

   If validation fails for a file, use AskUserQuestion to warn the user and ask whether to skip that file or abort entirely.

   **After all validation/skip decisions:** if no source files remain, stop with: "All source files failed validation. Fix the source findings and retry." Do not proceed to merge or write `findings.json`.

2. **Cross-source consistency check:** verify all loaded files agree on `pr`, `repo`, and `head_sha`.

   If `pr` or `repo` differ, stop with an error showing the mismatched values.

   If `head_sha` values differ, **stop with an actionable error** (do NOT offer to proceed):

   ```
   ## SHA Mismatch — Cannot Merge Findings

   Source findings were generated against different commits:

   | Source | head_sha | Age |
   |--------|----------|-----|
   | findings-codex.json | abc1234... | current |
   | findings-gh-review.json | def5678... | N commits behind |

   Re-run the stale review(s) before triaging:
   - `/codex-tools:review $ARGUMENTS`  ← stale
   ```

   Compute "Age" via `git log --oneline {stale_sha}..{newest_sha} | wc -l`. Label the newest SHA as "current". List re-run commands only for stale sources.

3. **Merge** all findings into a single working list. Preserve each finding's `source_detail` array as-is.

4. **Deduplicate:** findings describing the same underlying issue get merged when ALL of the following are true:
   - Same `path`
   - Overlapping line range: effective starts within 3 lines of each other (effective start = `start_line` if present, otherwise `line`)
   - Same `side` (both `LEFT`, or both omitted/`RIGHT`) — findings on different sides are NOT merge-compatible
   - Describing the same underlying concern (same general topic)

   When merging:
   - Keep the higher severity (`must-fix` > `should-fix` > `nit`)
   - Concatenate `source_detail` arrays from all merged findings
   - Keep the body from the higher-severity finding
   - Keep `title` and `recommendation` from whichever source provided them (prefer the higher-severity source if both have them)

Report: "Loaded {N} findings from {M} source(s): {comma-separated source IDs}. After deduplication: {D} findings."

## Phase 2: Investigate Findings

For each finding in the merged list, dispatch an investigation agent (Agent tool, subagent_type: "general-purpose"). **Launch ALL agents in a single message** so they run in parallel. On very large PRs (roughly 40+ findings), cap concurrency by launching in batches (e.g. 15-20 agents per message, waiting for each batch to finish before the next) to avoid overloading the session.

Each agent receives this prompt (fill in finding-specific values):

---

You are an investigation agent. Deeply investigate this code review finding and determine if it is valid.

**Finding:** {title, if present, otherwise first 80 chars of body}
**File:** {path}
**Lines:** {start_line}-{line} (or just {line} if no start_line)
**Severity:** {severity}
**Body:** {body}
**Recommendation:** {recommendation, or "N/A"}
**Flagged by:** {comma-separated list of agent_labels from source_detail}

**Instructions:**

1. **Read the code:** Read the referenced file and lines. Understand the surrounding context.

2. **Trace related code:** Follow imports, callers, callees, and type definitions relevant to the issue. Understand the full picture.

3. **Check git history:** Run `git log --oneline -10 -- {path}` and `git blame -L {start_line},{line} {path}` (skip blame if no line range). Look for recent changes that might have addressed or introduced the issue.

4. **Check test coverage:** Search for test files related to this code. Check if the flagged behavior has test coverage.

5. **Check if already addressed:** Compare the current code against the finding description. Has it been fixed since the review was generated?

6. **Return your findings as JSON** (ONLY the JSON object, no other text). Do not wrap in markdown code fences:

{"verdict": "valid | false-positive | already-addressed | pre-existing | unclear", "confidence": 0-100, "evidence": "Key findings with code snippets, git blame output, test references", "recommended_action": "keep | remove | reword", "suggested_body": "Proposed revised comment body text, or null", "suggested_severity": "must-fix | should-fix | nit, or null"}

**Action rules:**

- `keep` — the finding is valid, the body is accurate, and the body meets **Body length and clarity** below
- `remove` — the finding is a false positive, already addressed, or not actionable
- `reword` — the finding is valid but the body should be revised, including for length or clarity (provide `suggested_body`)

**Verdict-to-action defaults:**

- `pre-existing` — default `recommended_action` to `remove`, and note in `evidence` that the issue predates this PR (the change list shows it to the user, who can still keep it)
- `unclear` — default `recommended_action` to `keep`, and provide a `suggested_body` that states the uncertainty so the human decides with full context

**Body length and clarity:**

This applies whether or not writing-line exists. post-comments posts only `[{severity}] {body}`, so the `recommendation` field never reaches GitHub. Each body must stand alone: what is wrong, why it matters, and what to do. Keep it under about 80 words.

- Name the subject. The comment sits on a line, but the reader still needs the referent: "The names in `MATRIX_ROWS`", not "These names". Never open with a bare pronoun.
- When a claim is abstract, give one concrete case.
- Keep the one fact your investigation corrected, such as "two call sites, not three". Put the rest of your evidence in `evidence`.
- Leave out reviewer-process notes such as "flagged by both reviews", and commit history the fixer does not need.

A body over about 80 words, or one that breaks these rules, is a `reword` even when the finding is accurate. The verdict does not change.

**Writing `suggested_body`:**

Skip this if `~/.claude/skills/writing-line/` does not exist. Nothing else changes when it is absent.

When it does exist, read the Judgment section of `rules/common.md` and of `rules/technical.md` under that directory, plus every file in its `references/`. Write `suggested_body` to those rules. Ignore the Greppable blocks — they are the gate's business, not yours.

---

After all agents complete, parse each result as JSON. If an agent fails or returns unparseable output, mark that finding's investigation as failed.

Report: "Investigation complete. {N} findings investigated, {F} investigation(s) failed."

## Phase 3: Decide

### Sort Findings

Sort by severity (must-fix → should-fix → nit), then by investigation confidence (highest first). Findings with failed investigations sort last within their severity group. The output and the questions follow this order.

### Apply Recommendations

Give each finding with a parsed investigation the decision its `recommended_action` names:

| `recommended_action` | Decision | Change to the finding           |
| -------------------- | -------- | ------------------------------- |
| `keep`               | Keep     | None                            |
| `reword`             | Edit     | `body` becomes `suggested_body` |
| `remove`             | Remove   | Left out of the output          |

A `reword` with a null `suggested_body` is a Keep.

For each Keep or Edit finding whose `suggested_severity` is set and differs from `severity`, set `severity` to `suggested_severity`.

Record one line per changed finding for the change list in Phase 4: what changed, and why in a few words taken from `evidence`. For example: "Removed. Pre-existing: the retry loop predates this PR."

### Cross-Check the Bodies

Each investigation agent saw only its own finding. Read all Keep and Edit bodies together and look for:

- **Repeat:** a body makes a point that a finding earlier in the sort order already makes. Cut the point from the later body. If no point is left, Remove it.
- **Vocabulary:** a body uses a term that another finding flags as wrong, or a term listed under `_Avoid_` in the repo's `CONTEXT.md`. Use the term that finding or `CONTEXT.md` names instead.
- **Conflict:** two findings ask for fixes that pull in opposite directions, so applying one undoes or blocks the other.

A body rewritten here makes its finding an Edit, and follows **Body length and clarity** in Phase 2. Record each rewrite in the change list.

### Flag

A flag holds a finding's decision for the user. Flag a finding when:

- its investigation failed or returned unparseable JSON
- its verdict is `unclear`
- its confidence is below 60
- the cross-check found a Conflict with another finding

### Ask

Skip this step when no finding is flagged.

Ask about every flagged finding with AskUserQuestion, up to four questions per call. A Conflict pair shares one question. Each question names the finding (title or the first 60 characters of `body`, `path:line`, severity) and says in one sentence why it is flagged.

- **Single finding:** offer Keep, Edit and Remove. Show `suggested_body` as the Edit option's `preview`, and drop Edit when there is no `suggested_body`. Put the investigation's recommendation first and append " (Recommended)". For a failed investigation, mark nothing as recommended.
- **Conflict pair:** offer "Keep {A}", "Keep {B}" and "Keep both". Put the one the evidence supports first and append " (Recommended)".

Apply each answer. An "Other" answer is the user's instruction for that finding, such as new body text.

Done when every finding has exactly one decision: Keep, Edit or Remove.

## Phase 4: Output

1. **Write `ai-swap/pr-review-$ARGUMENTS/findings.json`** with the triage output schema:

   ```json
   {
     "source": "triage",
     "pr": $ARGUMENTS,
     "repo": "<repo from source files>",
     "head_sha": "<head_sha from source files (guaranteed consistent)>",
     "input_sources": ["<source IDs from each loaded file>"],
     "findings": [<Keep and Edit findings, in sort order>]
   }
   ```

   Use 2-space indentation.

2. **Validate the output:**

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py" ai-swap/pr-review-$ARGUMENTS/findings.json
   ```

   If validation fails, fix the errors and re-validate.

3. **Report the summary and the change list:**

   ```
   ## Triage Complete

   | Decision | Count     |
   | -------- | --------- |
   | Kept     | {kept}    |
   | Edited   | {edited}  |
   | Removed  | {removed} |

   **Final findings:** {count of findings in output}
   **Output:** ai-swap/pr-review-$ARGUMENTS/findings.json
   **Sources merged:** {comma-separated input_sources}

   ### Removed
   - `{path}:{line}` [{severity}] {title}: {verdict}. {reason}

   ### Severity changed
   - `{path}:{line}` {title}: {old} → {new}. {reason}

   ### Edited
   - `{path}:{line}` [{severity}] {title}: {reason}
   ```

   Omit an empty section. Mark each decision the user made in Phase 3 with "(you chose)".

## Phase 5: Next Step

If `findings.json` has no findings, report "Nothing to post or fix." and stop.

1. **Guess the goal from PR authorship:**

   ```bash
   gh pr view $ARGUMENTS --json author --jq .author.login
   gh api user --jq .login
   ```

   The same login means the user wrote the PR, so Fix is the likely goal. A different login makes Post the likely goal.

2. **Ask once** with AskUserQuestion: "What next for the {N} curated findings? Pick Other to change a decision first." Put the guessed goal first and append " (Recommended)" to its label:
   - "Post": "Post them as a pending review on PR #{pr}. post-comments shows all the comments and asks once before it posts."
   - "Fix": "Fix them in the working tree, run the repo's checks, and commit locally without pushing."
   - "Stop": "Keep findings.json and stop."

   On "Other", apply the changes the user names to `findings.json`, validate it again, report the updated change list and ask again.

### Post

Read `${CLAUDE_PLUGIN_ROOT}/skills/post-comments/SKILL.md` and follow it, with `$ARGUMENTS` as this PR number. The Skill tool cannot invoke post-comments, because that skill allows only user invocation.

### Fix

1. **Check the checkout.** Get the head branch with `gh pr view $ARGUMENTS --json headRefName --jq .headRefName`. If a different branch is checked out, or tracked files have uncommitted changes, stop and tell the user. If `HEAD` is not `head_sha`, list `git log --oneline {head_sha}..HEAD` and ask the user whether to proceed.

2. **Fix each finding** in sort order, including findings marked `unmappable`. Read the code at `path:line` and make the change that the `body` and `recommendation` describe. Follow the repo's instructions (`CLAUDE.md`, `AGENTS.md`) for each file you touch. Make the smallest change that settles the finding. When the code shows a fix is wrong, or much larger than the finding says, skip that finding and record why.

3. **Run the repo's checks:** tests, lint and type checks. Find the commands in `package.json` scripts, `mise.toml` tasks, a `Makefile` or the CI config. Fix any failure your changes caused. A failure that also occurs at `head_sha` is pre-existing: report it and leave it.

4. **Commit** in logical groups, in the repo's commit convention. Stage only the files your fixes changed. Leave the commits unpushed; pushing is the user's call.

5. **Report** each finding as `path:line` with its commit SHA, or as skipped with the reason. Then report the check results and any pre-existing failures.

Done when every finding in `findings.json` is in a commit or listed as skipped with its reason, and every check passes or fails only as pre-existing.
