---
name: gs:gh-tools:triage
description: Use when the user wants to investigate and triage code review findings for a PR, or when the user invokes /gs:gh-tools:triage with a PR number. Requires running a review skill first.
---

# Triage Review

Investigate and triage code review findings for PR #$ARGUMENTS.

## Input Parsing

`$ARGUMENTS` is a PR number. The review directory is `ai-swap/pr-review-$ARGUMENTS/`.

1. Glob for `findings-*.json` in the directory (this matches `findings-gh-review.json`, `findings-codex.json`, etc. but NOT `findings.json` which is triage's own output).
2. If no `findings-*.json` files are found:
   - If `triage-state.json` exists in the directory, delete it silently (`rm -f`).
   - Stop with: "No source findings found. Run `/gs:gh-tools:review $ARGUMENTS` and/or `/gs:codex-tools:review $ARGUMENTS` first."
3. If `triage-state.json` exists in the directory:
   - Attempt to parse it as JSON. If unparseable, delete it silently (`rm -f`) and continue to step 4 as if it didn't exist. If the parsed JSON is missing the `decisions` object or `finding_order` array, also treat it as corrupt: delete silently and continue to step 4.
   - Read the `decisions` object and the `finding_order` array.
   - **If `findings.json` also exists** (both checkpoint and prior output), ask the user (via AskUserQuestion): "Found partial triage progress ({count of decisions}/{count of finding_order} findings decided) and a previous triage output." Options:
     - "Resume in-progress triage" — carry forward previous decisions, prior `findings.json` will be replaced on completion
     - "Start fresh" — delete `triage-state.json` (`rm -f`) and proceed normally (prior `findings.json` will be replaced)
     - "Abort" — stop triage, keep existing `findings.json`
   - **If only `triage-state.json` exists** (no prior output), ask the user (via AskUserQuestion): "Found partial triage progress ({count of decisions}/{count of finding_order} findings decided in prior session). Resume where you left off, or start fresh?" Options: "Resume" (carry forward previous decisions), "Start fresh" (delete state file, triage from scratch).
   - **Resume**: Set a resume flag and store the loaded `decisions` map for Phase 3. Proceed to Phase 1 and Phase 2 normally (they are automated and idempotent). Provenance validation happens after Phase 1 merge — see "Initialize Checkpoint" below.
   - **Start fresh**: Delete `triage-state.json` (`rm -f`) and proceed normally.
   - **Abort**: Stop.
4. If a previous `findings.json` exists in the directory (no checkpoint), ask the user (via AskUserQuestion): "Previous triage output found. Start fresh from source findings, or abort so you can use the existing curated output?" Options: "Start fresh" (rebuild from source files), "Abort" (stop triage, keep existing findings.json). If abort, stop.

## Setup

Locate the schema validator (used throughout this skill):

```bash
VALIDATOR="${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py"
if [ ! -f "$VALIDATOR" ]; then echo "ERROR: validate-findings.py not found at $VALIDATOR" >&2; exit 1; fi
```

Use `uv run "$VALIDATOR" <file>` for all validation commands below.

## Phase 1: Merge Structured Findings

Execute directly — no subagent needed.

1. **Load and validate** each `findings-*.json` file:

   ```bash
   uv run "$VALIDATOR" ai-swap/pr-review-$ARGUMENTS/<filename>
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
   - `/gs:codex-tools:review $ARGUMENTS`  ← stale
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

{"verdict": "valid | false-positive | already-addressed | pre-existing | unclear", "confidence": 0-100, "evidence": "Key findings with code snippets, git blame output, test references", "recommended_action": "keep | remove | reword", "suggested_body": "Proposed revised comment body text, or null", "suggested_severity": "must-fix | should-fix | nit, or null"}

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

### Initialize Checkpoint

1. **Compute identity hashes.** For each finding in the sorted list, compute:

   `sha256(path + ":" + line + ":" + (side || "RIGHT") + ":" + sorted_agent_labels + ":" + (title || body[:64]))`

   Where `sorted_agent_labels` is a comma-joined string of all `agent_label` values from `source_detail`, sorted alphabetically (e.g. `"Correctness & Safety,architecture & design"`). This ensures the hash is stable regardless of `source_detail` merge order during deduplication.

   Truncate to the first 12 hex characters. This is the finding's stable identity hash used for checkpointing. Store it on the finding as `_identity_hash` for use in the triage loop.

   Note: the `side` field only appears in the schema when its value is `"LEFT"`; absence means RIGHT. The `title` (or body prefix) distinguishes different concerns flagged at the same file location. Hash collisions are statistically negligible for typical PR sizes.

2. **Write initial `triage-state.json`.** Construct the JSON object in memory first. If resuming (resume flag set in Input Parsing step 3), use the loaded `decisions` map; otherwise use `{}`. Always compute `finding_order` from the current sort order. Then write to `ai-swap/pr-review-$ARGUMENTS/triage-state.json`:

   ```json
   {
     "head_sha": "<head_sha from source findings>",
     "source_files": ["findings-codex.json", "findings-gh-review.json"],
     "finding_order": ["<hash1>", "<hash2>", ...],
     "decisions": {}
   }
   ```

   `source_files` is the sorted list of source filenames loaded in Phase 1.

   If the write fails, warn the user but continue — triage will still work, just without checkpoint protection.

3. **Validate checkpoint provenance (resume only).** If the resume flag is set, compare the checkpoint's `head_sha` and `source_files` against the current values from Phase 1. If either mismatches:
   - Warn the user: "Checkpoint was created against different source findings (SHA or source files changed). Previous decisions cannot be safely replayed."
   - Ask the user (via AskUserQuestion): "Start fresh" (clear the resume flag, delete `triage-state.json`, rewrite a fresh checkpoint) or "Abort".
   - Do not offer resume — stale decisions are not safe to replay.

### Triage Loop

For each finding in sorted order:

0. **Check for prior decision (resume only).** If a resume flag is set and this finding's `_identity_hash` exists in the loaded `decisions` map:
   - Apply the recorded decision silently: if `"keep"`, include the finding in the output list and increment kept counter; if `"remove"`, exclude and increment removed counter; if `"edit"`, update the finding's `body` with the recorded `edited_body`, include in output list, and increment edited counter.
   - Skip to the next finding (do not present or ask).

1. **Present the finding.** `{n}` is the finding's position in the sorted list (1-indexed), counting all findings including those replayed from checkpoint. Output to the user:

   ```
   ## Finding {n}/{total}: {title or first 80 chars of body}
   {if unmappable: [outside diff]}

   **File:** {path}:{start_line}-{line} (or {path}:{line})
   **Severity:** {severity}
   **Flagged by:** {comma-separated agent_labels from source_detail}
   {if unmappable: **Note:** This finding is outside the PR diff and will be saved to `general-comments.md` instead of posted inline.}

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

4. **Checkpoint.** After executing the user's choice, immediately update `triage-state.json`:
   - Update the in-memory `triage-state.json` object (the same object written in Initialize Checkpoint) by adding this finding's `_identity_hash` to the `decisions` map. Use the canonical action value: `"keep"` for Keep, `"remove"` for Remove, `"edit"` for Edit body. If `"edit"`, also include `"edited_body"` with the final body text.
   - Write the updated object to disk. If the write fails, warn the user but continue.

## Phase 4: Output

1. **Strip internal fields.** Remove `_identity_hash` from each finding in the output list. This field is used internally for checkpointing and must not appear in the output.

2. **Write `ai-swap/pr-review-$ARGUMENTS/findings.json`** with the triage output schema:

   ```json
   {
     "source": "triage",
     "pr": $ARGUMENTS,
     "repo": "<repo from source files>",
     "head_sha": "<head_sha from source files (guaranteed consistent)>",
     "input_sources": ["<source IDs from each loaded file>"],
     "findings": [<kept and edited findings>]
   }
   ```

   Use 2-space indentation. Only include findings the user kept or edited (not removed).

3. **Validate the output:**

   ```bash
   uv run "$VALIDATOR" ai-swap/pr-review-$ARGUMENTS/findings.json
   ```

   If validation fails, fix the errors and re-validate.

4. **Clean up checkpoint state:**

   ```bash
   rm -f ai-swap/pr-review-$ARGUMENTS/triage-state.json
   ```

5. **Report summary:**

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
