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
3. **Separate** findings into two lists based on validation results. Both lists ship in the same pending review.
   - **Inline:** findings that pass position validation. Each one becomes an inline comment on its line.
   - **Review-body:** findings that fail position validation, because the file is not in the diff or the line is outside every hunk. GitHub cannot attach these to a line, so they go in the review's top-level `body`. Re-validate all findings regardless of the `unmappable` flag — the PR may have been updated since the review was generated.

   Done when every finding is in exactly one list.

4. If the review-body list is non-empty, **build the review body** in this format:

   ```markdown
   ## Findings outside the diff

   These findings point at code that this PR does not change, so they cannot go inline.

   ### Must-fix

   **`{path}:{line}`** [source: architecture & design]

   {body}

   ### Should-fix

   **`{path}:{start_line}-{line}`** [source: Correctness & Safety]

   {body}

   ### Nit

   **`{path}:{line}`**

   {body}
   ```

   Rules: each finding is a label line, a blank line, then the body. The label is ``**`{path}:{line}`**`` (or `{path}:{start_line}-{line}` for ranges), with an optional `[source: {agent_label from first source_detail entry}]` after it. Keep the label on its own line. The writing plugin's send-lint hook reads a label and a sentence on one line as one long sentence, and bounces the POST. Use the finding's **full** body text verbatim — do not truncate it. Group by severity (must-fix → should-fix → nit). Omit empty groups.

   Step 6 sends the review body in the same POST as the inline comments.

5. Report validation results:
   - Inline findings: count
   - Review-body findings: count and list with reason (file not in diff, line not in hunk)

## Step 4: Voice Gate

Skip this step if the `writing:draft` skill is not available. Say nothing about it and go to Step 5.

Otherwise read `${CLAUDE_PLUGIN_ROOT}/references/voice-gate.md` and run the gate on every body that ships, inline and review-body findings alike, writing them to `ai-swap/drafts/technical/pr-$ARGUMENTS-bodies.md`.

This step is the only one that sees every source: findings from `gh-tools:review` and from `codex-tools:review` both arrive here. Triage has already dropped everything the user rejected, and Step 5 gates any body the user rewords. Together they gate exactly what ships.

## Step 5: Confirm

Triage has already curated these findings, and the user has already chosen to post them. Ask once, not per finding.

Present **all** findings, inline and review-body, grouped by severity (must-fix first, then should-fix, then nit). Number them in that order.

For each finding, display:

- **File:** `{path}:{start_line}-{line}` (or `{path}:{line}` for single-line)
- **Goes to:** `inline`, or `review body` with the Step 3 reason (file not in diff, line not in hunk)
- **Code:** Read the lines at the PR head with `git show {current PR head SHA from Step 2}:{path}` and show them. The local checkout can sit at an older head, for example after a rebase. If `side` or `start_side` is `LEFT`, the lines are on the old side, which the head does not have. Show them from the Step 3 diff hunk instead, keeping each line's `-`, `+` or space prefix.
- **Comment:** The proposed comment body
- **Severity:** {severity}

Then ask one AskUserQuestion, not `multiSelect`: "Post these {N} findings as one pending review on PR #{pr}, {I} inline and {B} in the review body? Pick Other to drop or edit some first, for example: drop 3, reword 5 to …" Leave out the inline and review-body counts when one of them is zero.

- "Post all {N} (Recommended)": go to Step 6.
- "Abort": stop the skill.

If the user picks Other, the text names findings to drop or reword, by number. Apply the changes, and rebuild the review body from the review-body findings that are left. If none are left, report "No comments left to post." and stop. If Step 4 ran and the user reworded any body, run the gate again on the reworded bodies only, at the same draft path. Then show the changed findings and ask this question again.

## Step 6: Post Review

1. Build the comments array from the confirmed inline findings. Each comment's `body` MUST be prefixed with the severity tag in square brackets, e.g. `[nit] {body}`, `[must-fix] {body}`, `[should-fix] {body}`. Each comment object:

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

3. **Write the payload** to `ai-swap/pr-review-$ARGUMENTS/review.json` with the Write tool, overwriting any existing file:

   ```json
   {
     "commit_id": "{current PR head SHA from Step 2}",
     "body": "{review body from Step 3}",
     "comments": [{comment objects from sub-step 1}]
   }
   ```

   Leave out `body` when there are no review-body findings. Use `"comments": []` when there are no inline findings. Writing a file keeps the bodies out of shell quoting, where an apostrophe would end the string. It also lets the writing plugin's send-lint hook read every `body` in the payload: the hook reads an `--input` file, but not stdin.

   Check the file parses: `jq -e 'has("commit_id") and (.comments | type == "array")' ai-swap/pr-review-$ARGUMENTS/review.json`

4. **Post the review:**

   ```bash
   gh api --method POST /repos/{repo}/pulls/$ARGUMENTS/reviews --input ai-swap/pr-review-$ARGUMENTS/review.json
   ```

   Do NOT include an `event` field — omitting it creates a pending (draft) review. Always batch all confirmed findings, inline and review-body, into this single call. The review body has to go in now: GitHub rejects a later PUT that adds a body to a pending review created without one (`422 Could not edit a review with a missing body`). A review-body finding reaches the PR only through this body. A separate PR comment would go public at once, ahead of the pending review.

5. If the API call fails, show the full error and stop. Do not retry. A send-lint bounce is not a failure: fix what is a real violation in `review.json`, or keep the text, and post again.

## Step 7: Report

- Show the count of inline comments, and the count of findings in the review body
- Link to the PR: `https://github.com/{repo}/pull/$ARGUMENTS`
- Remind: "Review is pending — go to the PR on GitHub to submit it with your verdict (Comment, Approve, or Request Changes)."
