---
name: gs:gh-tools:triage
description: Use when the user wants to investigate and triage code review findings for a PR, or when the user invokes /gs:gh-tools:triage with a PR number. Requires running a review skill first.
---

# Triage Review

Investigate and triage code review findings for PR #$ARGUMENTS.

## Input Parsing

`$ARGUMENTS` is a PR number. The review directory is `ai-swap/pr-review-$ARGUMENTS/`.

1. Glob for `findings-*.json` in the directory (this matches `findings-gh-review.json`, `findings-codex.json`, etc. but NOT `findings.json` which is triage's own output).
2. If no `findings-*.json` files are found, stop with: "No source findings found. Run `/gs:gh-tools:review $ARGUMENTS` and/or `/gs:codex-tools:review $ARGUMENTS` first."
3. If a previous `findings.json` exists in the directory, ask the user (via AskUserQuestion): "Previous triage output found. Start fresh from source findings, or abort so you can use the existing curated output?" Options: "Start fresh" (rebuild from source files), "Abort" (stop triage, keep existing findings.json). If the user chooses to start fresh, proceed normally. If abort, stop.

## Phase 1: Merge Structured Findings

Execute directly — no subagent needed.

1. **Load and validate** each `findings-*.json` file:

   ```bash
   uv run "$(find ~/.claude/plugins/cache -name validate-findings.py -path '*/gh-tools/*' | sort -V | tail -1)" ai-swap/pr-review-$ARGUMENTS/<filename>
   ```

   If validation fails for a file, use AskUserQuestion to warn the user and ask whether to skip that file or abort entirely.

2. **Cross-source consistency check:** verify all loaded files agree on `pr`, `repo`, and `head_sha`. If any values differ, use AskUserQuestion to warn the user with the mismatched values and ask whether to:
   - Proceed using the most recent `head_sha`
   - Abort

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

For each finding in the merged list, dispatch an investigation agent (Agent tool, subagent_type: "general-purpose"). **Launch ALL agents in a single message** so they run in parallel.

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

```json
{
  "verdict": "valid | false-positive | already-addressed | pre-existing | unclear",
  "confidence": 0-100,
  "evidence": "Key findings with code snippets, git blame output, test references",
  "recommended_action": "keep | remove | reword",
  "suggested_body": "Proposed revised comment body text, or null",
  "suggested_severity": "must-fix | should-fix | nit, or null"
}
```

**Action rules:**

- `keep` — the finding is valid and the body is accurate
- `remove` — the finding is a false positive, already addressed, or not actionable
- `reword` — the finding is valid but the body should be revised (provide `suggested_body`)

---

After all agents complete, parse each result as JSON. If an agent fails or returns unparseable output, mark that finding's investigation as failed.

Report: "Investigation complete. {N} findings investigated, {F} investigation(s) failed."

## Phase 3: Triage Findings

### Sort Findings

Sort by severity (must-fix → should-fix → nit), then by investigation confidence (highest first). Findings with failed investigations sort last within their severity group.

### Triage Loop

For each finding in sorted order:

1. **Present the finding.** Output to the user:

   ```
   ## Finding {n}/{total}: {title or first 80 chars of body}   {if unmappable: [outside diff]}

   **File:** {path}:{start_line}-{line} (or {path}:{line})
   **Severity:** {severity}
   **Flagged by:** {comma-separated agent_labels from source_detail}
   {if unmappable: **Note:** This finding is outside the PR diff and will be posted as a general comment.}

   **Body:** {body}
   **Recommendation:** {recommendation, or omit if null}

   ### Investigation
   **Verdict:** {verdict} (confidence: {confidence}/100)
   **Evidence:** {evidence}
   **Recommendation:** {recommended_action}
   ```

   If investigation failed, show: "Investigation failed — showing raw finding only."

2. **Ask the user** (via AskUserQuestion):
   - "Keep" — include in output as-is (description: "Include this finding in the curated output")
   - "Remove" — exclude from output (description: "Exclude this finding — won't be posted")
   - "Edit body" — rewrite the comment (description: "Revise the comment text before including. {if suggested_body: 'Agent suggests: ' + first 80 chars of suggested_body + '...'}")

3. **Execute the user's choice:**

   **Keep:** No changes. Increment kept counter.

   **Remove:** Exclude from output list. Increment removed counter.

   **Edit body:** Use AskUserQuestion to present body editing options:
   - If `suggested_body` is non-null: first option is "Use suggested body" with a preview of the full suggested text
   - Always allow "Other" for custom text
     Update the finding's `body` with the chosen text. Increment edited counter.

## Phase 4: Output

1. **Write `ai-swap/pr-review-$ARGUMENTS/findings.json`** with the triage output schema:

   ```json
   {
     "source": "triage",
     "pr": $ARGUMENTS,
     "repo": "<repo from source files>",
     "head_sha": "<head_sha — most recent if sources differed>",
     "input_sources": ["<source IDs from each loaded file>"],
     "findings": [<kept and edited findings>]
   }
   ```

   Use 2-space indentation. Only include findings the user kept or edited (not removed).

2. **Validate the output:**

   ```bash
   uv run "$(find ~/.claude/plugins/cache -name validate-findings.py -path '*/gh-tools/*' | sort -V | tail -1)" ai-swap/pr-review-$ARGUMENTS/findings.json
   ```

   If validation fails, fix the errors and re-validate.

3. **Report summary:**

   ```
   ## Triage Complete

   | Action  | Count     |
   | ------- | --------- |
   | Kept    | {kept}    |
   | Removed | {removed} |
   | Edited  | {edited}  |

   **Final findings:** {count of findings in output}
   **Output:** ai-swap/pr-review-$ARGUMENTS/findings.json
   **Sources merged:** {comma-separated input_sources}

   Run `/gs:gh-tools:post-comments $ARGUMENTS` to review and post these as GitHub PR comments.
   ```
