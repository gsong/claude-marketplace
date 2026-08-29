---
name: "gs:gh-tools:post-comments"
description: "Post curated code-level review comments to a GitHub PR as a pending review. Use when the user wants to post code-level review comments to a GitHub PR, or invokes /gs:gh-tools:post-comments with a PR number. Requires running /gs:gh-tools:triage first to curate findings."
compatibility: "Requires the gh CLI (authenticated) and uv for the bundled Python validator."
argument-hint: "<pr-number>"
---

# Post PR Comments

Post code-level review comments to GitHub PR #$ARGUMENTS as a pending review.

**Prerequisite:** Run `/gs:gh-tools:triage $ARGUMENTS` first to curate findings.

## Setup

Locate the schema validator (used throughout this skill):

```bash
VALIDATOR="${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py"
if [ ! -f "$VALIDATOR" ]; then echo "ERROR: validate-findings.py not found at $VALIDATOR" >&2; exit 1; fi
```

Use `uv run "$VALIDATOR" <file>` for all validation commands below.

## Step 1: Load Findings

1. Check for `ai-swap/pr-review-$ARGUMENTS/findings.json`
   - If it exists: validate it first with `uv run "$VALIDATOR" ai-swap/pr-review-$ARGUMENTS/findings.json`. If validation fails, report the errors and stop.
   - If valid: read and parse it. Report: "{N} findings loaded for PR #{pr} in {repo}"
   - If it does NOT exist:
     - Check for `findings-*.json` files in the directory
     - If `findings-*.json` files exist: tell the user "Source findings exist but haven't been triaged. Run `/gs:gh-tools:triage $ARGUMENTS` first." and stop.
     - If no `findings-*.json` files exist: tell the user "No findings found. Run `/gs:gh-tools:review $ARGUMENTS` first." and stop.

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

Skip this step if `~/.claude/skills/writing-line/` does not exist. Say nothing about it and go to Step 5.

This is the last point before the text reaches GitHub, and it is the only one that sees every source: findings from `gs:gh-tools:review` and from `gs:codex-tools:review` both arrive here. Gating here also gates exactly what ships, since triage has already dropped everything the user rejected.

The gate is a PostToolUse hook. It fires on any write under `ai-swap/drafts/<profile>/`, so writing the bodies there is what runs it.

1. **Write every postable body** to `ai-swap/drafts/technical/pr-{PR}-bodies.md` under the repo root. It is a sibling of `ai-swap/pr-review-{PR}/`, not a child. Pass the Write tool the absolute path. One section per finding:

   ```markdown
   ## {index} / `{path}:{line}`

   {body text}
   ```

   Use the **Write tool**, not a shell heredoc. The gate matches `Write`, `Edit`, and `MultiEdit` by tool name, so a `cat >` in Bash writes the file and fires nothing.

   Backtick the path in the heading, exactly as shown. The gate blanks inline code before it runs its rules. A range like `foo.py:12-34` then cannot report as a hyphenated number range. Leave the path bare and your own heading trips that rule.

   Keep the rest of the heading punctuation plain. An em dash in your own section headings counts toward the em dash density the gate reports on the draft as a whole.

   Backtick or fence every code fragment a body quotes, for the same reason. The gate scans neither, which is what keeps a `--` inside quoted code from reporting as a double hyphen.

2. **Read the gate's report and fix what is a real violation.** One misread is expected in this material:

   - A sentence ending inside a closing quotation mark is not seen as a sentence end. Two sentences then merge and report as one long run. Rephrase to move the quote off the boundary, or drop the quotation marks.

   A number-range report is not a misread. It means a `path:line` reference went in unbackticked. Backtick it.

   Say so if a rule misreads the same passage twice. That is a signal the rule is wrong, and the user can retire it.

3. **Fold the corrected text back** onto the findings, then delete the draft file.

   Deleting it is safe. A second hook keeps a snapshot of each draft so it can tell a
   later edit from the original, and a third sweeps that snapshot at the end of the turn
   once the draft is gone. Leave the file behind instead and the next run on this PR
   diffs its fresh bodies against this run's, which records the whole file as if you had
   corrected it.

Step 5 then presents gated text, and Step 6 still lets the user edit any of it before posting.

## Step 5: Present for Approval

Present **inline-postable** findings grouped by severity (must-fix first, then should-fix, then nit). General-comment findings were already curated during triage and are handled by Step 3.

For each finding, display:

- **File:** `{path}:{start_line}-{line}` (or `{path}:{line}` for single-line)
- **Code:** Read the actual lines from the file and show them
- **Comment:** The proposed comment body
- **Severity:** {severity}

Then use AskUserQuestion (multiSelect: true) to ask which findings to post. Each option should be labeled as:
`[{severity}] {path}:{line} — {first 60 chars of body}...`

## Step 6: Edit Comments (optional)

After the user selects findings to post, ask (via AskUserQuestion):
"Want to edit any comment text before posting?"

- If yes: for each approved finding, show the body and ask if they want to change it
- If no: proceed to posting

## Step 7: Post Review

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

   Do NOT include an `event` field — omitting it creates a pending (draft) review. Always batch all approved comments into a single call.

4. If the API call fails, show the full error and stop. Do not retry.

## Step 8: Report

- Show count of posted comments
- Link to the PR: `https://github.com/{repo}/pull/$ARGUMENTS`
- If `ai-swap/pr-review-$ARGUMENTS/general-comments.md` exists: "**{N} findings couldn't be posted inline** and were saved to `ai-swap/pr-review-$ARGUMENTS/general-comments.md`. You can copy-paste this file's contents as a general PR comment."
- Remind: "Review is pending — go to the PR on GitHub to submit it with your verdict (Comment, Approve, or Request Changes)."
