---
name: gs:repo-maintenance:gha
description: Use when the user asks to upgrade or update GitHub Actions workflow dependencies, check for outdated actions, or use actions-up. Also use when the user invokes /gs:repo-maintenance:gha.
---

# Upgrade GitHub Actions Dependencies

Upgrade GitHub Actions workflow dependencies using [actions-up](https://github.com/azat-io/actions-up), respecting `minimumReleaseAge` constraints from `renovate.json`.

## Process

### 1. Pre-flight checks

1. **Check for GitHub Actions workflows**: Verify `.github/workflows/` directory exists in the project repo. If not, abort: "This repo doesn't use GitHub Actions workflows."

### 2. Resolve minimumReleaseAge

Check both config files and normalize to days (round up). The pnpm-workspace.yaml value is treated as a project-wide cool-down hint even though it natively scopes to pnpm — it signals the maintainer's general comfort threshold for new releases.

**`renovate.json`** (if it exists in the project root):

1. Check top-level `minimumReleaseAge` — applies globally to all packages
2. Check `packageRules` array for entries matching GitHub Actions:
   - Entries where `matchManagers` includes `"github-actions"`
   - Or `matchPackagePatterns` / `matchPackageNames` referencing action patterns (e.g., `"actions/*"`)
   - Extract `minimumReleaseAge` from matching rules
3. Parse duration strings to days:
   - Split on space: `{number} {unit}`
   - Convert: days × 1, hours ÷ 24 (round up), minutes ÷ 1440 (round up)
   - Examples: `"3 days"` → 3, `"72 hours"` → 3, `"4320 minutes"` → 3

**`pnpm-workspace.yaml`** (if it exists in the project root):

- Look for a top-level `minimumReleaseAge` field — integer in minutes (e.g., `1440` = 1 day)
- Convert to days, rounding up: `minutes ÷ 1440` (e.g., `1440` → 1, `4320` → 3, `10080` → 7)

**Combine:**

1. If multiple values found across sources, use the **largest** (strictest)
2. If none found, default to **7 days** and inform the user: "No minimumReleaseAge found in renovate.json or pnpm-workspace.yaml — defaulting to a 7-day cool-down."
3. Report the effective constraint and its source to the user (e.g., "Using minimumReleaseAge of 3 days from renovate.json", "Using 3 days from pnpm-workspace.yaml as a hint", or "Using 7-day default cool-down")

### 3. Dry-run preview

Run with sandbox disabled:

```bash
GITHUB_TOKEN=$(gh auth token) npx actions-up --yes --dry-run --min-age N
```

- `N` is the resolved minimumReleaseAge in days (or `7` if none was found in renovate.json)
- Present the full output to the user
- If the output shows no updates available, inform the user and stop

### 4. Research significant updates

For actions with major or minor version changes shown in the dry-run output, research their changelogs and release notes for new features and breaking changes that could affect your specific workflows. Present findings to the user alongside the dry-run results.

### 5. Confirm with user

Ask the user if they want to apply the updates shown in the dry-run. Use the AskUserQuestion tool.

### 6. Apply updates

If the user confirms, run with sandbox disabled:

```bash
GITHUB_TOKEN=$(gh auth token) npx actions-up --yes --min-age N
```

- Use the same `--min-age` value as the dry-run
- Present the results showing what was updated
- Summarize: list the workflow files modified and which actions were upgraded, including breaking change highlights from the research step

## Important Notes

- This skill updates workflow files in place — it does not perform git operations (branch, commit, push, PR)
- `actions-up` pins updated actions to exact commit SHAs with version comments for security
- `actions-up` auto-discovers `.github/workflows/*.yml`, `.github/actions/*/action.yml`, and root `action.yml`/`action.yaml`
- GITHUB_TOKEN is set via `gh auth token` to avoid API rate limits
- `actions-up` runs via `npx` — no global install required
