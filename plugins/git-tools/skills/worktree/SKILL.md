---
name: gs:git-tools:worktree
description: Use when the user wants to create a new git worktree with intelligent branch naming and directory setup, or when the user invokes /gs:git-tools:worktree.
---

# Create Git Worktree

You are tasked with creating a new git worktree with intelligent branch naming and directory setup.

## Input Analysis

The user will provide either:

- A full branch name (e.g., `feat/add-shadow`, `fix/button-crash`)
- An intent description (e.g., "add shadow to button", "fix panel crash")

## Step 1: Determine Branch Name

1. Check if the input contains a conventional commit prefix (`feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`, `style/`, `perf/`)
2. If it does, use the input as the branch name as-is
3. If it doesn't, infer the branch name from the intent:
   - If it describes adding/creating something new → `feat/`
   - If it describes fixing something → `fix/`
   - If it describes restructuring/improving code → `refactor/`
   - If it describes performance improvements → `perf/`
   - If it describes styling changes → `style/`
   - Convert the intent to kebab-case
   - Combine prefix + kebab-case description

## Step 2: Create Short Directory Name

Create a directory name that:

- Is approximately 15 characters or less (flexible, not rigid)
- Captures the essence of the branch name
- Removes the prefix (feat/, fix/, etc.)
- Uses key words from the branch name
- Is memorable and recognizable

Examples:

- `feat/add-shadow-to-details-button` → `shadow-btn` or `details-shadow`
- `fix/detail-panel-crash-on-load` → `panel-crash` or `load-crash`
- `refactor/asset-store-state` → `asset-store`
- `perf/optimize-chart-render` → `chart-perf`

## Step 3: Check for Conflicts

1. Create `.worktrees/` directory if it doesn't exist: `mkdir -p .worktrees`
2. List the contents of `.worktrees/` directory and check if the proposed directory name exists
3. Check if the branch name already exists: `git branch --list {branch-name}`

**If directory name conflicts**, intelligently resolve:

- Try a variation: `shadow-btn` → `btn-shadow` or `details-btn`
- Try appending a number: `shadow-btn` → `shadow-btn2`
- Keep it short and sensible

**If branch name already exists**, use `git worktree add` without `-b` to check out the existing branch instead of creating a new one.

## Step 4: Create Worktree and Setup

Execute the following commands as separate, discrete operations:

1. Create the worktree:

```bash
# New branch:
git worktree add -b {branch-name} .worktrees/{short-dir-name}
# Existing branch:
git worktree add .worktrees/{short-dir-name} {branch-name}
```

2. If `.env` exists in the project root, copy it to the new worktree:

```bash
cp .env .worktrees/{short-dir-name}/.env
```

3. If `mise.toml` or `.mise.toml` exists in the new worktree, trust it:

```bash
cd .worktrees/{short-dir-name} && mise trust
```

4. If `.envrc` exists in the new worktree, allow direnv:

```bash
cd .worktrees/{short-dir-name} && direnv allow
```

5. If `package.json` exists in the new worktree, install dependencies:

```bash
cd .worktrees/{short-dir-name} && pnpm install
```

Note: Execute each command separately. Do not chain them together with the worktree creation.

## Step 5: Report

Tell the user:

- The branch name that was created
- The worktree directory path
- Which setup steps were performed (.env copied if applicable, mise trusted if applicable, direnv allowed if applicable, dependencies installed if applicable)
