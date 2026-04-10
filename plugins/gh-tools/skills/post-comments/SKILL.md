---
name: gs:gh-tools:post-comments
description: Use when the user wants to post code-level review comments to a GitHub PR as a pending review, or when the user invokes /gs:gh-tools:post-comments. Requires running /gs:gh-tools:triage first to curate findings.
---

# Post PR Comments

Post code-level review comments to GitHub PR #$ARGUMENTS as a pending review.

**Prerequisite:** Run `/gs:gh-tools:triage $ARGUMENTS` first to curate findings.

## Step 1: Load Findings

1. Check for `ai-swap/pr-review-$ARGUMENTS/findings.json`
   - If it exists: read and parse it. Report: "{N} findings loaded for PR #{pr} in {repo}"
   - If it does NOT exist:
     - Check for `findings-*.json` files in the directory
     - If `findings-*.json` files exist: tell the user "Source findings exist but haven't been triaged. Run `/gs:gh-tools:triage $ARGUMENTS` first." and stop.
     - If no `findings-*.json` files exist: tell the user "No findings found. Run `/gs:gh-tools:review $ARGUMENTS` first." and stop.

## Step 2: Staleness Check

1. Get current PR head: `gh pr view $ARGUMENTS --json headRefOid --jq .headRefOid`
2. Compare with `head_sha` from the JSON
3. If they differ:
   - Warn: "The PR has been updated since the review (reviewed: `{head_sha}`, current: `{current_sha}`). Findings may reference stale line numbers."
   - Ask the user (via AskUserQuestion) whether to proceed anyway or abort

## Step 3: Validate Positions

1. Get the PR diff: `gh pr diff $ARGUMENTS`
2. For each finding, verify:
   - The `path` exists in the diff
   - The `line` (and `start_line` if present) falls within a diff hunk
3. If any findings are invalid, **append** them to `ai-swap/pr-review-$ARGUMENTS/general-comments.md`:
   - Before appending, read the existing file (if present) and check for entries with the same `path` + `line` to avoid duplicates. Skip any finding that already has a matching entry.
   - Each bullet includes a source tag if `source_detail` is present: `[source: {agent_label from first source_detail entry}]`
   - If the file already exists (from the review skill), append new findings under existing severity headers or add new severity headers as needed.
   - If the file doesn't exist, create it with the full format:

   ```markdown
   ## Findings Outside the Diff

   The following review findings reference code that isn't part of this PR's diff, so they couldn't be posted as inline comments.

   ### Must-fix

   - [source: architecture & design] **`{path}:{line}`** — {body}...

   ### Should-fix

   - [source: Correctness & Safety] **`{path}:{start_line}-{line}`** — {body}...

   ### Nit

   - **`{path}:{line}`** — {body}...
   ```

   Rules: each finding is a bullet with optional `[source: {label}]` prefix, then ``**`{path}:{line}`**`` (or `{path}:{start_line}-{line}` for ranges) followed by `— {body}`. Group by severity (must-fix → should-fix → nit). Omit empty groups.

4. Report validation results:
   - Valid findings: list count
   - Invalid findings: list with reason (file not in diff, line not in hunk) — these will be skipped for inline posting
   - If any were written to `general-comments.md`: "{N} findings written to `general-comments.md`"

## Step 4: Present for Approval

Present findings grouped by severity (must-fix first, then should-fix, then nit).

For each finding, display:

- **File:** `{path}:{start_line}-{line}` (or `{path}:{line}` for single-line)
- **Code:** Read the actual lines from the file and show them
- **Comment:** The proposed comment body
- **Severity:** {severity}

Then use AskUserQuestion (multiSelect: true) to ask which findings to post. Each option should be labeled as:
`[{severity}] {path}:{line} — {first 60 chars of body}...`

## Step 5: Edit Comments (optional)

After the user selects findings to post, ask (via AskUserQuestion):
"Want to edit any comment text before posting?"

- If yes: for each approved finding, show the body and ask if they want to change it
- If no: proceed to posting

## Step 6: Post Review

1. Build the comments array from approved findings. Each comment's `body` MUST be prefixed with the severity tag in square brackets, e.g. `[nit] {body}`, `[must-fix] {body}`, `[should-fix] {body}`. Each comment object:

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

2. Build and post the review via `gh api`. Construct the full JSON payload and pipe via stdin:

   ```bash
   jq -n '{commit_id: $cid, comments: $c}' \
     --arg cid "<head_sha from JSON>" \
     --argjson c '<comments array as JSON>' |
     gh api --method POST /repos/{repo}/pulls/$ARGUMENTS/reviews --input -
   ```

   Do NOT include an `event` field — omitting it creates a pending (draft) review.

3. **IMPORTANT: GitHub API limitation** — You cannot add comments to an existing pending review. A user can only have one pending review per PR. If a pending review already exists, you must either:
   - **Delete it first** (`gh api --method DELETE /repos/{repo}/pulls/{pr}/reviews/{review_id}`) and recreate with all comments in one call, OR
   - **Submit it first** (`gh api --method POST /repos/{repo}/pulls/{pr}/reviews/{review_id}/events --input <(echo '{"event":"COMMENT"}')`) before creating a new pending review

   Always batch all approved comments into a single `POST .../reviews` call to avoid this issue.

4. If the API call fails, show the full error and stop. Do not retry.

## Step 7: Report

- Show count of posted comments
- Link to the PR: `https://github.com/{repo}/pull/$ARGUMENTS`
- If `ai-swap/pr-review-$ARGUMENTS/general-comments.md` exists: "**{N} findings couldn't be posted inline** and were saved to `ai-swap/pr-review-$ARGUMENTS/general-comments.md`. You can copy-paste this file's contents as a general PR comment."
- Remind: "Review is pending — go to the PR on GitHub to submit it with your verdict (Comment, Approve, or Request Changes)."
