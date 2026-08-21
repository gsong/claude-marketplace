---
name: "gs:ai-docs:update"
description: "Update specific docs-ai/ documentation after code changes — a lightweight alternative to a full audit. Use when the user has made code changes and wants to update related documentation. Also use when the user invokes /gs:ai-docs:update, optionally with a description of the change (e.g., 'added Redis caching layer')."
argument-hint: "[what changed]"
---

# Update Docs AI

Targeted documentation updates after code changes. Analyzes what changed, identifies affected docs, and updates them.

## Process

### 1. Understand the Change

**If argument provided** (e.g., `/gs:ai-docs:update "added Redis caching layer"`):
Use the argument as the change description.

**If no argument provided:**
Analyze recent git changes to infer what changed:

```bash
# Check for uncommitted changes first
git diff --name-only
git diff --cached --name-only

# Then recent commits (check depth first)
git log --oneline -5
COMMIT_COUNT=$(git rev-list --count HEAD 2>/dev/null || echo 0)
if [ "$COMMIT_COUNT" -ge 4 ]; then
  git diff HEAD~3 --name-only
elif [ "$COMMIT_COUNT" -ge 2 ]; then
  git diff HEAD~$((COMMIT_COUNT - 1)) --name-only
fi
```

If git history is unavailable (no commits, shallow clone, errors), ask the user to describe the change — the argument is required in this case.

### 2. Resolve Docs Directory

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-dir-resolution.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/docs-dir-resolution.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

The changed paths git reports are relative to the repo root. Key Paths are relative to `[path-root]`. Strip the `[path-root]` prefix from each changed path before you compare — `apps/woody/app/routes.ts` matches the Key Path `app/routes.ts`. Comparing the two forms directly finds nothing, and finding nothing looks the same as having nothing to update.

When the change spans several path roots (a diff touching two packages that each have their own docs directory), handle one docs directory per run and tell the user which other path roots the diff touched, so they can rerun for those. Updating one and staying silent about the rest leaves docs wrong without saying so.

### 3. Identify Affected Docs

Spawn an analyst agent (Explore type, read-only) to:

1. Read `[docs-dir]/README.md` topic index
2. Map changed files/directories to Key Paths in topic tables, comparing them under a common root as described above
3. Read potentially affected docs
4. Return structured findings:
   - Which existing docs need updating, and what specifically changed
   - Whether any NEW docs should be created (new feature area not covered)
   - Whether any docs should be removed (deleted feature area)

### 4. Present Plan to User

Show:

```
## Proposed Documentation Updates

Docs directory: [docs-dir] (path root [path-root])
[If the diff touched other path roots with their own docs: "Also changed: [path-root list] — rerun there."]

### Docs to Update
- [filename].md — [what changed and why]

### New Docs to Create
- [filename].md — [rationale]

### Docs to Remove
- [filename].md — [rationale]

Proceed? (y/n)
```

Wait for user approval.

### 5. Execute Updates

Spawn writer agents (general-purpose type — writers need Write, which Explore lacks; one per affected doc, parallelized). Each writer:

- Reads current doc content + changed source files
- Updates doc to reflect new reality, preserving accurate existing content
- Uses `file::Symbol` references throughout
- If creating a new doc: auto-populate with real content using the same approach as gs:ai-docs:init (read source files, write content, use rich stubs for gaps)

### 6. Update README.md

If docs were added or removed:

- Add new docs to the topic index
- Remove deleted docs from the topic index
- Verify every `.md` file (except README.md and quick-reference.md) appears in the index

### 7. Stamp Updated Docs

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/verification-stamp.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/verification-stamp.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

Stamp only the docs that were updated or created (plus README.md if it changed). Leave untouched docs alone — their stamps still reflect when they were last verified.

If the working tree has uncommitted changes, note in the summary that docs were verified against HEAD plus uncommitted changes.

### 8. Summary

Show what was updated, created, and removed. Flag any sections that still need manual attention.
