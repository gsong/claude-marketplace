---
name: "post-comments"
description: "Post curated review findings to a GitHub PR as a pending review. Run after gh-tools:triage."
disable-model-invocation: true
compatibility: "Requires the gh CLI (authenticated) and uv for the bundled Python validator."
argument-hint: "<pr-number>"
---

# Post PR Comments

Post code-level review comments to GitHub PR #$ARGUMENTS as a pending review.

## Step 1: Load Findings

1. Check for `ai-swap/pr-review-$ARGUMENTS/findings.json`
   - If it exists: locate the schema validator, then validate the file with it. If validation fails, report the errors and stop.

     ```bash
     if [ ! -f "${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py" ]; then echo "ERROR: validate-findings.py not found at ${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py" >&2; exit 1; fi
     uv run "${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py" ai-swap/pr-review-$ARGUMENTS/findings.json
     ```

   - If valid: read and parse it. Report: "{N} findings loaded for PR #{pr} in {repo}"
   - If it does NOT exist:
     - Check for `findings-*.json` files in the directory
     - If `findings-*.json` files exist: tell the user "Source findings exist but haven't been triaged. Run `/gh-tools:triage $ARGUMENTS` first." and stop.
     - If no `findings-*.json` files exist: tell the user "No findings found. Run `/gh-tools:review $ARGUMENTS` first." and stop.

## Step 2: Staleness Check

1. Get current PR head: `gh pr view $ARGUMENTS --json headRefOid --jq .headRefOid`
2. Compare with `head_sha` from the JSON
3. If they match, proceed to Step 3.
4. If they differ, compute staleness context and present an interactive warning:

   **Fetch the PR head first** — the commits may not be local:

   ```bash
   git fetch origin {current_sha}
   ```

   **Compute context:**
   - Commit list: `git log --oneline {head_sha}..{current_sha}`
   - Changed files: `git diff --name-status {head_sha}..{current_sha}`
   - Cross-reference finding paths against changed files to count affected findings

   If the objects still aren't available after the fetch (the `git log`/`git diff` commands fail), warn the user that the staleness diff is unavailable and skip the commit/file lists — still report the SHA mismatch and ask whether to proceed.

   **Present to user:**

   ```
   ## Stale Findings Detected

   Findings were generated against `{head_sha}`, but the PR head is now `{current_sha}` ({N} commits ahead).

   **Commits since review:**
   - {sha1} {message1}
   - {sha2} {message2}
   ...

   **Files changed since review:**
   - {path} ({status: modified/added/deleted})
   ...

   **Findings that touch changed files:** {count} of {total}
   ```

   Then ask the user (via AskUserQuestion) whether to proceed anyway or abort. This is an interactive warning, not a hard failure — the user may judge that findings are still valid despite new commits (e.g., trivial changes to unrelated files).

## Step 3: Validate Positions

1. Get the PR diff: `gh pr diff $ARGUMENTS`
2. For each finding, verify:
   - The `path` exists in the diff
   - The `line` (and `start_line` if present) falls within a diff hunk. **Side-aware validation:** if the finding has `side: "LEFT"`, validate line numbers against the **old-side** range from the hunk header (`-start,count`, which covers both context and deleted lines). If `side` is omitted (defaults to RIGHT), validate against the **new-side** range from the hunk header (`+start,count`, which covers both context and added lines).
3. **Separate** findings into two lists based on validation results:
   - **Inline-postable:** findings that pass position validation.
   - **General-comment:** findings that fail position validation. Re-validate all findings regardless of the `unmappable` flag — the PR may have been updated since the review was generated.
4. If the general-comment list is non-empty, **write** `ai-swap/pr-review-$ARGUMENTS/general-comments.md` (overwriting any existing file):

   ```markdown
   ## Findings Outside the Diff

   The following review findings reference code that isn't part of this PR's diff, so they couldn't be posted as inline comments.

   ### Must-fix

   - [source: architecture & design] **`{path}:{line}`** — {body}

   ### Should-fix

   - [source: Correctness & Safety] **`{path}:{start_line}-{line}`** — {body}

   ### Nit

   - **`{path}:{line}`** — {body}
   ```

   Rules: each finding is a bullet with optional `[source: {agent_label from first source_detail entry}]` prefix, then ``**`{path}:{line}`**`` (or `{path}:{start_line}-{line}` for ranges) followed by `— {body}`. Use the finding's **full** body text verbatim — do not truncate it. Group by severity (must-fix → should-fix → nit). Omit empty groups.

5. If zero general-comment findings, delete any existing `general-comments.md`: `rm -f ai-swap/pr-review-$ARGUMENTS/general-comments.md`
6. Report validation results:
   - Inline-postable findings: count
   - General-comment findings: count and list with reason (file not in diff, line not in hunk)
   - If `general-comments.md` was written: "{N} findings written to `general-comments.md`"
   - If `general-comments.md` was deleted (stale from previous run): note that it was cleaned up

## Step 4: Voice Gate

Skip this step if the `writing:draft` skill is not available. Say nothing about it and go to Step 5.

Otherwise read `${CLAUDE_PLUGIN_ROOT}/references/voice-gate.md` and run the gate on every postable body, writing them to `ai-swap/drafts/technical/pr-$ARGUMENTS-bodies.md`.

This step is the only one that sees every source: findings from `gh-tools:review` and from `codex-tools:review` both arrive here. Triage has already dropped everything the user rejected, and Step 5 gates any body the user rewords. Together they gate exactly what ships.

## Step 5: Confirm

Triage has already curated these findings, and the user has already chosen to post them. Ask once, not per finding.

Present **inline-postable** findings grouped by severity (must-fix first, then should-fix, then nit). Number them in that order. General-comment findings were already curated during triage and are handled by Step 3.

For each finding, display:

- **File:** `{path}:{start_line}-{line}` (or `{path}:{line}` for single-line)
- **Code:** Read the lines at the PR head with `git show {current PR head SHA from Step 2}:{path}` and show them. The local checkout can sit at an older head, for example after a rebase. If `side` or `start_side` is `LEFT`, the lines are on the old side, which the head does not have. Show them from the Step 3 diff hunk instead, keeping each line's `-`, `+` or space prefix.
- **Comment:** The proposed comment body
- **Severity:** {severity}

Then ask one AskUserQuestion, not `multiSelect`: "Post these {N} comments as a pending review on PR #{pr}? Pick Other to drop or edit some first, for example: drop 3, reword 5 to …"

- "Post all {N} (Recommended)": go to Step 6.
- "Abort": stop the skill.

If the user picks Other, the text names findings to drop or reword, by number. Apply the changes. If none are left, report "No comments left to post." and stop. If Step 4 ran and the user reworded any body, run the gate again on the reworded bodies only, at the same draft path. Then show the changed findings and ask this question again.

## Step 6: Post Review

1. Build the comments array from the confirmed findings. Each comment's `body` MUST be prefixed with the severity tag in square brackets, e.g. `[nit] {body}`, `[must-fix] {body}`, `[should-fix] {body}`. Each comment object:

   ```json
   {
     "path": "{path}",
     "line": {line},
     "body": "[{severity}] {body}"
   }
   ```

   `line` must be an integer (not a string). `start_line` must also be an integer if present.
   Include `start_line` only if it was present in the finding.
   Include `side` only if it was present in the finding (omitting defaults to `RIGHT`).
   Include `start_side` only if it was present in the finding (omitting defaults to `RIGHT`).

2. **Preflight: check for existing pending review.** A user can only have one pending review per PR — the POST will 422 if one already exists.

   ```bash
   gh api --paginate --slurp /repos/{repo}/pulls/$ARGUMENTS/reviews | jq '[.[][] | select(.state == "PENDING")] | first'
   ```

   Pipe to a separate `jq` — `gh` rejects `--slurp` together with `--jq` or `--template`. `--slurp` returns an array of pages, so the filter needs `.[][]` to reach individual reviews.

   - If no pending review exists → proceed to sub-step 3.
   - If a pending review is found → report its ID and comment count, then ask the user (via AskUserQuestion) how to proceed:
     - **Delete it** — `gh api --method DELETE /repos/{repo}/pulls/{pr}/reviews/{review_id}` — then proceed to sub-step 3.
     - **Submit it as-is** — `gh api --method POST /repos/{repo}/pulls/{pr}/reviews/{review_id}/events --input <(echo '{"event":"COMMENT"}')` — then proceed to sub-step 3.
     - **Abort** — stop the skill.

3. Build and post the review via `gh api`. Construct the full JSON payload and pipe via stdin:

   ```bash
   jq -n '{commit_id: $cid, comments: $c}' \
     --arg cid "<current PR head SHA from Step 2>" \
     --argjson c '<comments array as JSON>' |
     gh api --method POST /repos/{repo}/pulls/$ARGUMENTS/reviews --input -
   ```

   Do NOT include an `event` field — omitting it creates a pending (draft) review. Always batch all confirmed comments into a single call.

4. If the API call fails, show the full error and stop. Do not retry.

## Step 7: Report

- Show count of posted comments
- Link to the PR: `https://github.com/{repo}/pull/$ARGUMENTS`
- If `ai-swap/pr-review-$ARGUMENTS/general-comments.md` exists: "**{N} findings couldn't be posted inline** and were saved to `ai-swap/pr-review-$ARGUMENTS/general-comments.md`. You can copy-paste this file's contents as a general PR comment."
- Remind: "Review is pending — go to the PR on GitHub to submit it with your verdict (Comment, Approve, or Request Changes)."
