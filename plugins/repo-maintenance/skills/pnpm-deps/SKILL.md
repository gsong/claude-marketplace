---
name: "gs:repo-maintenance:pnpm-deps"
description: "Upgrade pnpm project dependencies and run the test suite, respecting the project's release-age cool-down. Works for single projects and workspaces. Use when the user asks to upgrade, update, or bump pnpm project dependencies (not the pnpm version itself — use /gs:repo-maintenance:pnpm for that), or wants to check for outdated packages. Also use when the user invokes /gs:repo-maintenance:pnpm-deps."
compatibility: "Requires pnpm and network access to the npm registry."
---

# Upgrade project dependencies

Upgrade pnpm project dependencies, respecting the project's release-age cool-down.

## Process

### 1. Check for outdated dependencies

Run `pnpm outdated -r` and present the full output to the user. If nothing is outdated, inform the user and stop.

### 2. Research significant updates

For packages with major or minor version changes, research changelogs and release notes for new features and breaking changes that could affect this project. Present findings to the user before proceeding.

### 3. Confirm with user

Use the AskUserQuestion tool to confirm how to proceed. Offer options:

- Upgrade everything to latest
- Upgrade within existing semver ranges only
- Upgrade a subset (let the user specify which packages)
- Cancel

### 4. Update dependencies

Based on the user's choice:

- **Everything**: `pnpm up -r --latest`
- **Within ranges**: `pnpm up -r`
- **Subset**: `pnpm up -r --latest <pkg1> <pkg2> ...`

`pnpm up` writes the lockfile and installs — no separate `pnpm i` needed.

### 5. Run tests

Detect the test command from `package.json` scripts (e.g., `test`, `check`, `ci`) and run it. Failing tests after an upgrade usually mean a breaking change landed — stop, identify which package caused the failure, and use AskUserQuestion to ask whether to fix forward or pin the previous version.

### 6. Show the diff and summarize

Show the user the `package.json` and lockfile (`pnpm-lock.yaml`) diff so they can see exactly what changed, then summarize which packages were upgraded and highlight any breaking changes surfaced during the research step.

## Important Notes

- This skill updates dependencies and runs tests only — it does not perform git operations (branch, commit, push, PR)
- Works for both single-project repos and pnpm workspaces/monorepos (`-r` is safe in both contexts)
- **Release-age cool-down**: pnpm natively honors a `minimumReleaseAge` setting read from `pnpm-workspace.yaml` (resolution details in `${CLAUDE_PLUGIN_ROOT}/references/release-age.md`). It applies to all dependencies including transitive ones during resolution, so `pnpm up` will skip any release still inside the cool-down window automatically — no extra flag needed. This is the primary supply-chain guard for third-party packages; if the repo does not set it, consider recommending it to the user (align with any project-wide value found in `renovate.json` if present)
