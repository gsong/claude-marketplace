---
name: triage-review
description: Use when the user wants to investigate and triage code review findings for a PR, or when the user invokes /triage-review with a PR number. Requires running /pr-review first.
---

# Triage Review

Investigate and triage code review findings for $ARGUMENTS.

## Input Parsing

`$ARGUMENTS` is a PR number. The review directory is `ai-swap/pr-review-$ARGUMENTS/`.

1. List files in the directory. Classify by extension:
   - `.md` files → review markdown files
   - `.json` file → findings JSON file (target for edits); expect `findings.json`
2. If the directory doesn't exist, stop with: "Error: Directory `ai-swap/pr-review-$ARGUMENTS/` not found. Run `/c:pr-review $ARGUMENTS` first."
3. If no `.json` file is found, stop with: "Error: No JSON findings file in `ai-swap/pr-review-$ARGUMENTS/`."
4. If no `.md` file is found, stop with: "Error: No review markdown files in `ai-swap/pr-review-$ARGUMENTS/`."
5. If more than one `.json` file is found, stop with: "Error: Exactly one JSON file required, got {N}."

Read the JSON file and validate its structure: it must be an object with `pr` (number), `repo` (string), `head_sha` (string), and `findings` (array). Each finding in the array should have at least `path`, `line`, `body`, and `severity` fields. If any of these are missing or the wrong type, use AskUserQuestion to warn the user and ask whether to proceed anyway.

Report: "Loaded {N} existing findings from {json_path}. Reading {M} review file(s)."

Read all review markdown files.

## Phase 1: Extract Issues

Dispatch a single agent (Agent tool, subagent_type: "general-purpose") with this prompt:

---

You are an issue extraction agent. You will receive review markdown content and existing JSON findings. Your job is to produce a unified, deduplicated list of all discrete issues.

**Review files content:**
{paste the full content of each .md file, prefixed with its filename}

**Existing JSON findings:**
{paste the findings array from the JSON file}

**Instructions:**

1. Read each review file and identify every discrete issue mentioned. An issue is any problem, suggestion, concern, or finding — regardless of whether the review recommends action on it.

2. For each issue, extract:
   - `id`: sequential number starting at 1
   - `summary`: one-line description of the issue
   - `source`: which review file(s) mentioned it, with a brief excerpt of the original text
   - `confidence`: numeric score from the review if one was given, otherwise null
   - `severity_hint`: severity signal from the review (must-fix, should-fix, nit, critical, important, minor, etc.) or null
   - `file_path`: the referenced file path if identifiable, otherwise null
   - `line_range`: referenced line numbers (e.g., "38-45" or "45") if identifiable, otherwise null
   - `origin`: one of:
     - `review_and_json` — issue appears in review(s) AND matches an existing JSON finding (by file path + line proximity + textual similarity)
     - `review_only` — issue appears in review(s) but has no matching JSON finding
     - `json_only` — JSON finding exists but no review mentions it

3. **Deduplication:** If multiple reviews mention the same issue (same file + similar description), merge into one entry. Keep the higher confidence score. For severity, use this priority order: must-fix > should-fix > nit (keep the highest-priority hint). Cite both sources.

4. **Cross-reference with JSON:** For each existing JSON finding, check if any extracted review issue matches it (same path, nearby lines, similar concern). Mark matches as `review_and_json`. Any JSON findings with no review match become `json_only` entries.

5. Return the complete list as a JSON array. Return ONLY the JSON array, no other text.

---

Parse the agent's response as a JSON array. Report: "Extracted {N} issues ({R} from reviews, {J} from JSON, {B} in both)."

If zero issues are extracted, report "No issues found across reviews." and stop.

## Phase 2: Investigate Issues

For each extracted issue, dispatch an investigation agent (Agent tool, subagent_type: "general-purpose"). **Launch ALL agents in a single message** so they run in parallel.

Each agent receives this prompt (fill in issue-specific values):

---

You are an investigation agent. Deeply investigate this code review issue and determine if it is valid.

**Issue #{id}:** {summary}
**Source:** {source}
**File:** {file_path}
**Lines:** {line_range}
**Origin:** {origin}
**Existing JSON finding body (if any):** {body from JSON finding, or "N/A"}

**Instructions:**

1. **Read the code:** Read the referenced file and lines. If `file_path` is null, use the source excerpt to identify the relevant file.

2. **Trace related code:** Follow imports, callers, callees, and type definitions relevant to the issue. Understand the context.

3. **Check git history:** If `file_path` is known, run `git log --oneline -10 -- {file_path}`. If both `file_path` and `line_range` are known, also run `git blame -L {line_range} {file_path}`. Skip these steps if the values are null.

4. **Check test coverage:** Search for test files related to this code. Check if the flagged behavior has test coverage.

5. **Check if already addressed:** Compare the current code against the issue description. Has it been fixed since the review was generated?

6. **Return your findings as JSON** (ONLY the JSON object, no other text):

```json
{
  "issue_id": {id},
  "verdict": "valid | false-positive | already-addressed | pre-existing | unclear",
  "confidence": 0-100,
  "evidence": "Key findings with code snippets, git blame output, test references",
  "recommended_action": "keep | remove | reword | add-to-json",
  "suggested_body": "Proposed comment body text, or null",
  "suggested_severity": "must-fix | should-fix | nit, or null",
  "resolved_line": "resolved line number, or null"
}
```

**Action consistency rules:**

- If origin is `review_and_json`: recommend `keep`, `remove`, or `reword`
- If origin is `review_only`: recommend `add-to-json` (provide suggested_body, suggested_severity, resolved_line) or `remove` (meaning: skip)
- If origin is `json_only`: recommend `keep` or `remove`

---

After all agents complete, parse each result as JSON. If an agent fails or returns unparseable output, mark that issue's investigation as failed.

Report: "Investigation complete. {N} issues investigated, {F} investigation(s) failed."

## Phase 3: Triage Issues

### Sort Issues

Sort the extracted issues for presentation:

1. Separate `json_only` issues into their own group — they always appear last, regardless of severity
2. Group remaining issues by resolved severity: must-fix → should-fix → nit → unknown severity
3. Append the `json_only` group at the end
4. Within each group, sort by investigation confidence (highest first)

Resolved severity = investigation's `suggested_severity` if present, else extraction's `severity_hint`, else "unknown".

### Triage Loop

For each issue in sorted order:

1. **Present the issue.** Output to the user:

   ```
   ## Issue {id}/{total}: {summary}

   **Source:** {source}
   **File:** {file_path}:{line_range}
   **Origin:** {origin}

   ### Investigation
   **Verdict:** {verdict} (confidence: {confidence}/100)
   **Evidence:** {evidence}
   **Recommendation:** {recommended_action}
   ```

   If investigation failed, show: "Investigation failed — showing raw review text only."
   If the issue has an existing JSON finding, also show: "**Current JSON body:** {body}"

2. **Ask the user** (via AskUserQuestion) based on origin:

   **If `review_and_json`:**
   - "Keep" — no change (description: "Leave the existing finding as-is")
   - "Remove" — delete from JSON (description: "Delete this finding from the JSON file")
   - "Edit body" — rewrite the comment (description: "Rewrite the comment text. Agent suggests: {first 80 chars of suggested_body}...")

   **If `review_only`:**
   - "Add" — add to JSON (description: "Add as new finding. Severity: {resolved_severity}. Body: {first 80 chars of suggested_body}...")
   - "Skip" — don't add (description: "Don't add this to the JSON file")

   **If `json_only`:**
   - "Keep" — no change (description: "Leave the existing finding as-is")
   - "Remove" — delete from JSON (description: "Delete this orphaned finding")

3. **Execute the user's choice:**

   **Keep:** No changes. Increment kept counter.

   **Remove:** Find the matching finding in the JSON `findings` array by identity (path + line + body content). Remove it. Write the updated JSON file. Increment removed counter.

   **Edit body:** Show the user a confirmation via AskUserQuestion. If `suggested_body` is non-null, offer it as the first option ("Use suggested body") with a preview. If `suggested_body` is null, show the current JSON body as the first option ("Keep current body"). Always allow "Other" for custom text. Update the finding's `body` in the JSON. Write the updated JSON file. Increment edited counter.

   **Add:** Before adding, confirm the body text with the user via AskUserQuestion. If `suggested_body` is non-null, offer it as the first option ("Use suggested body") with a preview. Always allow "Other" for custom text. Then construct the finding object:
   - `path`: from extraction `file_path` (required — if null, use AskUserQuestion to ask user for the path)
   - `line`: from investigation `resolved_line`, or first line of extraction `line_range`, or use AskUserQuestion to ask user
   - `start_line`: if `line_range` spans multiple lines (e.g., "38-45"), set to the start value
   - `body`: the confirmed/edited body text from the step above
   - `severity`: from investigation `suggested_severity`, or extraction `severity_hint`, or use AskUserQuestion to ask user
     Append to JSON `findings` array. Write the updated JSON file. Increment added counter.

   **Skip:** No changes. Increment skipped counter.

**IMPORTANT:**

- After every modification, re-read the JSON file before writing to avoid stale state.
- Only modify the `findings` array — never touch `pr`, `repo`, or `head_sha`.
- When writing the JSON file, use 2-space indentation for readability (matching the original format).

## Phase 4: Summary

After all issues have been triaged, read the `pr` field from the JSON file and output:

## Triage Complete

| Action  | Count     |
| ------- | --------- |
| Kept    | {kept}    |
| Added   | {added}   |
| Removed | {removed} |
| Edited  | {edited}  |
| Skipped | {skipped} |

**Final findings in JSON:** {count of findings array}
**JSON file:** {json_path}

Run `/c:post-pr-comments {pr}` to review and post these as GitHub PR comments.
