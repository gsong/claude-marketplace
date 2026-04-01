---
name: gs:ai-docs:update
description: "Update specific docs-ai/ documentation after code changes. Use when the user has made code changes and wants to update related documentation, or when invoked as /gs:ai-docs:update. Accepts an optional argument describing the change (e.g., 'added Redis caching layer'). Lightweight alternative to a full audit."
---

# Update Docs AI

Targeted documentation updates after code changes. Analyzes what changed, identifies affected docs, and updates them.

## Process

### 1. Understand the Change

**If argument provided** (e.g., `/ai-docs:docs-ai-update "added Redis caching layer"`):
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

Check these locations in order. Use the **first match**:

1. `docs-ai/`
2. `docs/ai/`
3. `.claude/docs/`

If more than one exists, emit a warning: "Multiple docs directories found: [list]. Using [chosen]. Consider consolidating to a single location."

If none exist, output: "No docs-ai directory found. Run `/ai-docs:docs-ai-init` to bootstrap documentation."

### 3. Identify Affected Docs

Spawn an analyst agent (Explore type, read-only) to:

1. Read `[docs-dir]/README.md` topic index
2. Map changed files/directories to Key Paths in topic tables
3. Read potentially affected docs
4. Return structured findings:
   - Which existing docs need updating, and what specifically changed
   - Whether any NEW docs should be created (new feature area not covered)
   - Whether any docs should be removed (deleted feature area)

### 4. Present Plan to User

Show:

```
## Proposed Documentation Updates

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

Spawn writer agents (one per affected doc, parallelized). Each writer:

- Reads current doc content + changed source files
- Updates doc to reflect new reality, preserving accurate existing content
- Uses `file::Symbol` references throughout
- If creating a new doc: auto-populate with real content using the same approach as docs-ai-init (read source files, write content, use rich stubs for gaps)

### 6. Update README.md

If docs were added or removed:

- Add new docs to the topic index
- Remove deleted docs from the topic index
- Verify every `.md` file (except README.md and quick-reference.md) appears in the index

### 7. Summary

Show what was updated, created, and removed. Flag any sections that still need manual attention.
