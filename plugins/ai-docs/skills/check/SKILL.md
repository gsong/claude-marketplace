---
name: "gs:ai-docs:check"
description: "Check documentation freshness and detect drift, returning a staleness report with recommended actions. Read-only — modifies nothing. Use when the user wants to know which docs-ai/ files may be outdated relative to code changes. Also use when the user invokes /gs:ai-docs:check."
---

# Check Docs AI Freshness

Orchestrated documentation freshness check using parallel per-doc checker agents. Three phases: discovery → parallel checking fanout → consolidated report.

## Process

### Phase 1: Discovery

#### 1. Resolve Docs Directory

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-dir-resolution.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/docs-dir-resolution.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

#### 2. Read README.md

Read `[docs-dir]/README.md`. Parse the topic index to get the full list of docs with their Key Paths.

README.md and quick-reference.md carry no Key Paths and are deliberately excluded here — `/gs:ai-docs:audit` verifies them instead.

#### 3. Git Availability Check

Run `git log -1 --format=%ct` to verify the repo has git history.

- If it succeeds: set `git_available = true`
- If it fails: set `git_available = false`

### Phase 2: Parallel Freshness Check

#### 4. Spawn Checker Agents

Spawn parallel **read-only** checker agents using the Agent tool (Explore type). Assign each agent 1 doc (or 2-3 related docs for small doc sets with fewer than 4 total docs).

Each checker agent's prompt must include:

- The docs directory path
- Its assigned doc file path(s)
- The Key Paths for each assigned doc (from the topic index)
- Whether git is available (`git_available`)
- Instructions to return structured results (not edit files)

Each checker performs:

**If git is available:**

1. Establish the baseline. Read the doc's first line. If it is a verification stamp:

```markdown
<!-- verified-against: [full-commit-sha] -->
```

and the SHA is a known commit (`git cat-file -e [sha]^{commit}` succeeds), use that SHA as the baseline. The stamp is the commit the doc was last generated or verified against — it is more precise than the doc's own git timestamp.

2. If there is no stamp (or the SHA is unknown, e.g. after a rebase or in a shallow clone), fall back to the doc's last-modified commit:

```
git log -1 --format=%H -- [docs-dir]/[filename].md
```

Note in the result that the doc is unstamped.

3. For each Key Path in the doc's topic table row, count commits since the baseline:

```
git rev-list --count [baseline]..HEAD -- [key-path]
```

4. If any Key Path count is greater than zero, flag as potentially stale.

**Always (git or not):**

5. Spot-check 3-5 `file::Symbol` references from the doc:

- Does the referenced file exist? (use Glob)
- Does the referenced symbol exist in that file? (use Grep)

6. Check if Key Path files/directories still exist (use Glob)

**Each checker returns a structured result:**

- Doc filename
- Rating: `fresh`, `possibly stale`, or `likely stale`
- Baseline used: stamp SHA or doc timestamp fallback (unstamped)
- Key Path change details (commits behind, if git available)
- Broken references (list of `file::Symbol` that failed validation)
- Missing Key Paths (files/directories that no longer exist)

**Rating criteria:**

- **fresh** — Key Paths unchanged since the baseline, all checked references valid
- **possibly stale** — Key Paths had changes but references still valid
- **likely stale** — references broken OR Key Paths significantly changed (10+ commits behind)

Rate conservatively — "possibly stale" is better than a false "likely stale".

### Phase 3: Consolidate and Report

#### 5. Report

Collect all checker results. Output in this format:

```
## Docs Freshness Report

[If git unavailable: "⚠ Staleness detection limited (no git history). Results based on reference validity only."]

### Likely Stale

- [filename].md — Key Paths changed [N] commits ago, [N] broken references
  - Broken: `file::Symbol` not found in [file]

### Possibly Stale

- [filename].md — Key Paths had minor changes, references still valid

### Fresh

- [filename].md, [filename].md

### Recommended Actions

- Run `/gs:ai-docs:update "[description]"` to fix [specific doc]
- Run `/gs:ai-docs:audit` for comprehensive review ([N] docs need attention)
[If any docs are unstamped: "- [N] docs have no verification stamp. Run `/gs:ai-docs:audit` to verify and stamp them."]
```

## Critical Rules

- **Read-only** — do not modify any files
- Be specific about what's broken (which references, which Key Paths)
- If git is unavailable, clearly state this limitation in the report header
