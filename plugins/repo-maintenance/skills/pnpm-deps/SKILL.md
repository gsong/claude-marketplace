---
name: gs:repo-maintenance:pnpm-deps
description: Use when the user asks to upgrade, update, or bump pnpm project dependencies, or wants to check for outdated packages. Works for both single-project and monorepo/workspace setups. Also use when the user invokes /gs:repo-maintenance:pnpm-deps.
---

# Upgrade project dependencies

1. **Check for outdated dependencies**: `pnpm outdated -r` — present the full output to the user
2. **Research significant updates**: For packages with major/minor version changes, research changelogs for new features, improvements, and breaking changes that could affect your specific codebase. Present findings to the user before proceeding
3. **Update dependencies**: `pnpm up -r --latest` (recursive update with latest versions)
4. **Install dependencies**: `pnpm i`
5. **Run tests**: Detect the test command from `package.json` scripts (e.g., `test`, `check`, `ci`) and run it
   - **CRITICAL**: If any tests fail or errors occur, **STOP IMMEDIATELY** and fix issues before proceeding
6. **Show the diff and summarize**: Show the user the `package.json` and lockfile (`pnpm-lock.yaml`) diff so they can see exactly what changed, then summarize which packages were upgraded and highlight any breaking changes surfaced during the research step

## Important Notes

- This skill updates dependencies and runs tests only — it does not perform git operations (branch, commit, push, PR)
- Works for both single-project repos and pnpm workspaces/monorepos (`-r` is safe in both contexts)
- **Release-age cool-down**: pnpm natively honors a `minimumReleaseAge` setting read from `pnpm-workspace.yaml` (an integer number of minutes, e.g., `minimumReleaseAge: 10080` for 7 days). It applies to all dependencies including transitive ones during resolution, so `pnpm up` will skip any release still inside the cool-down window automatically — no extra flag needed. This is the primary supply-chain guard for third-party packages; if the repo does not set it, consider recommending it to the user (align with any project-wide value found in `renovate.json` if present)
