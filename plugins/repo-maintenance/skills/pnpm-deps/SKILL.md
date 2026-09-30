---
name: "pnpm-deps"
description: "Upgrade pnpm project dependencies and run the test suite, respecting pnpm's minimumReleaseAge setting. Use when the user asks to upgrade pnpm project dependencies (not the pnpm version itself — use repo-maintenance:pnpm for that), or wants to check for outdated packages."
compatibility: "Requires pnpm and network access to the npm registry."
---

# Upgrade project dependencies

Upgrade pnpm project dependencies, respecting pnpm's `minimumReleaseAge` setting.

## Process

### 1. Check the release-age cool-down

Read `pnpm-workspace.yaml`. If `minimumReleaseAge` is absent, resolve a value with `${CLAUDE_PLUGIN_ROOT}/references/release-age.md` and offer via AskUserQuestion to add it before upgrading. Otherwise report the value in effect.

### 2. Check for outdated dependencies

Run `pnpm outdated -r` and present the full output to the user. If nothing is outdated, inform the user and stop.

### 3. Research significant updates

For every major or minor bump, present either the breaking changes found or an explicit 'no changelog located'.

### 4. Confirm with user

Use the AskUserQuestion tool to confirm how to proceed. Offer options:

- Upgrade everything to latest
- Upgrade within existing semver ranges only
- Upgrade a subset (let the user specify which packages)
- Cancel

### 5. Update dependencies

Based on the user's choice:

- **Everything**: `pnpm up -r --latest`
- **Within ranges**: `pnpm up -r`
- **Subset**: `pnpm up -r --latest <pkg1> <pkg2> ...`

`pnpm up` writes the lockfile and installs — no separate `pnpm i` needed.

### 6. Run tests

Detect the test command from `package.json` scripts (e.g., `test`, `check`, `ci`) and run it. If no such script exists, say so and continue to step 7. Failing tests after an upgrade usually mean a breaking change landed — stop, identify which package caused the failure, and use AskUserQuestion to ask whether to fix forward or pin the previous version.

### 7. Show the diff and summarize

Show the user the `package.json` and lockfile (`pnpm-lock.yaml`) diff so they can see exactly what changed, then summarize which packages were upgraded and highlight any breaking changes surfaced during the research step.

## Important Notes

- This skill updates dependencies and runs tests only. Stop after editing; the user commits.
- Works for both single-project repos and pnpm workspaces/monorepos (`-r` is safe in both contexts)
- **Release-age cool-down**: pnpm natively honors the `minimumReleaseAge` setting in `pnpm-workspace.yaml`. It applies to all dependencies including transitive ones during resolution, so `pnpm up` will skip any release still inside the cool-down window automatically — no extra flag needed. This is the primary supply-chain guard for third-party packages.
