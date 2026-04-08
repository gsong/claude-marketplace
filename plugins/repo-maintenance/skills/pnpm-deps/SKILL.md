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

## Important Notes

- This skill updates dependencies and runs tests only — it does not perform git operations (branch, commit, push, PR)
- Works for both single-project repos and pnpm workspaces/monorepos (`-r` is safe in both contexts)
