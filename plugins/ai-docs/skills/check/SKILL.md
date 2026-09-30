---
name: "check"
description: "Report which docs-ai/ files are stale relative to their Key Paths. Read-only."
disable-model-invocation: true
---

# Check Docs AI Freshness

Orchestrated documentation freshness check using parallel per-doc checker agents. Three phases: discovery → parallel checking fanout → consolidated report.

Every file stays as found; the report is the only output.

## Process

### Phase 1: Discovery

#### Resolve Docs Directory

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-dir-resolution.md"`

> **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/docs-dir-resolution.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

#### Read README.md

Read `[docs-dir]/README.md`. Parse the topic index to get the full list of docs with their Key Paths.

README.md and quick-reference.md carry no Key Paths and are deliberately excluded here — `ai-docs:audit` verifies them instead.

#### Git Availability Check

Run `git log -1 --format=%ct` to verify the repo has git history.

- If it succeeds: set `git_available = true`
- If it fails: set `git_available = false`

### Phase 2: Parallel Freshness Check

#### Spawn Checker Agents

Spawn parallel **read-only** checker agents using the Agent tool (Explore type). Assign each agent 1 doc (or 2-3 related docs for small doc sets with fewer than 4 total docs).

Cap the fanout at 10 agents. Large docs directories exist — a monorepo package can carry 30+ docs — and one agent per doc stops being parallelism at that point. Above 10 docs, group related docs into 10 batches.

Each checker agent's prompt must include:

- The docs directory path `[docs-dir]` and the path root `[path-root]`
- Its assigned doc file path(s)
- The Key Paths for each assigned doc (from the topic index), plus the instruction to resolve each as `[path-root]/[key-path]`
- Whether git is available (`git_available`)
- Instructions to return structured results (not edit files)

Each checker performs:

1. Resolve each Key Path as `[path-root]/[key-path]` and Glob it. If none resolve, rate `unresolved` and stop.

2. **If git is available**, establish the baseline and count changes:

   !`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/staleness-baseline.md"`

   > **Resource fallback:** If the above is empty, the shell pre-exec didn't run. Read the file with the Read tool at `${CLAUDE_SKILL_DIR}/../../resources/staleness-baseline.md` (resolve `${CLAUDE_SKILL_DIR}` to an absolute path first).

3. Spot-check 3-5 `file::Symbol` references from the doc (git or not):

   - Does the referenced file exist? (use Glob)
   - Does the referenced symbol exist in that file? (use Grep)

**Each checker returns a structured result:**

- Doc filename
- Rating: `fresh`, `possibly stale`, `likely stale`, or `unresolved`
- Baseline used: stamp SHA or the doc's last-modified commit (unstamped)
- Key Path change details (commits behind, if git available)
- Broken references (list of `file::Symbol` that failed validation)
- Missing Key Paths (files/directories that no longer exist)

**Rating criteria:**

- **fresh** — Key Paths resolve, are unchanged since the baseline, and all checked references are valid
- **unresolved** — none of the doc's Key Paths resolve under `[path-root]`. This is a resolution problem, not a doc problem: report it as such instead of rating the doc
- **possibly stale** — Key Paths had changes but references still valid
- **likely stale** — references broken OR Key Paths significantly changed (10+ commits behind)

Rate conservatively — "possibly stale" is better than a false "likely stale".

### Phase 3: Consolidate and Report

#### Report

Collect all checker results. Output in this format:

```
## Docs Freshness Report

Checked [docs-dir] (path root [path-root])

[If git unavailable: "⚠ Staleness detection limited (no git history). Results based on reference validity only."]

### Likely Stale

- [filename].md — Key Paths changed [N] commits ago, [N] broken references
  - Broken: `file::Symbol` not found in [file]

### Possibly Stale

- [filename].md — Key Paths had minor changes, references still valid

### Fresh

- [filename].md, [filename].md

### Unresolved

- [filename].md — no Key Path resolved under [path-root]; staleness not checked

### Recommended Actions

- Run `/ai-docs:update "[description]"` to fix [specific doc]
- Run `/ai-docs:audit` for comprehensive review ([N] docs need attention)
[If any docs are unstamped: "- [N] docs have no verification stamp. Run `/ai-docs:audit` to verify and stamp them."]
```
