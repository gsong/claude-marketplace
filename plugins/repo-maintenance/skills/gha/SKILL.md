---
name: "gs:repo-maintenance:gha"
description: "Upgrade GitHub Actions workflow dependencies with actions-up, respecting the project's release-age cool-down. Use when the user asks to upgrade or update GitHub Actions workflow dependencies, check for outdated actions, or use actions-up. Also use when the user invokes /gs:repo-maintenance:gha."
compatibility: "Requires npx and the gh CLI (authenticated), plus network access to the GitHub API."
---

# Upgrade GitHub Actions Dependencies

Upgrade GitHub Actions workflow dependencies using [actions-up](https://github.com/azat-io/actions-up), respecting `minimumReleaseAge` constraints from `renovate.json`.

## Process

### 1. Pre-flight checks

1. **Check for GitHub Actions workflows**: Verify `.github/workflows/` directory exists in the project repo. If not, abort: "This repo doesn't use GitHub Actions workflows."

### 2. Resolve minimumReleaseAge

Read `${CLAUDE_PLUGIN_ROOT}/references/release-age.md` and resolve the effective value — for renovate `packageRules`, match GitHub Actions entries (`matchManagers` includes `"github-actions"`, or patterns like `"actions/*"`). Normalize to **days**, rounding up (e.g., 4320 minutes → 3 days), and report the constraint and its source per the reference.

### 3. Dry-run preview

Run with sandbox disabled — the command needs network access to query the GitHub API:

```bash
GITHUB_TOKEN=$(gh auth token) npx actions-up --yes --dry-run --min-age N
```

- `N` is the resolved minimumReleaseAge in days from step 2
- Present the full output to the user
- If the output shows no updates available, inform the user and stop

### 4. Research significant updates

For actions with major or minor version changes, research changelogs and release notes for new features and breaking changes that could affect this project. Present findings to the user before proceeding.

### 5. Confirm with user

Ask the user if they want to apply the updates shown in the dry-run. Use the AskUserQuestion tool.

### 6. Apply updates

If the user confirms, run with sandbox disabled — the command needs network access and writes workflow files:

```bash
GITHUB_TOKEN=$(gh auth token) npx actions-up --yes --min-age N
```

- Use the same `--min-age` value as the dry-run
- Present the results showing what was updated
- Summarize: list the workflow files modified and which actions were upgraded, including breaking change highlights from the research step

## Important Notes

- This skill updates workflow files in place — it does not perform git operations (branch, commit, push, PR)
- `actions-up` pins updated actions to exact commit SHAs with version comments for security
- `actions-up` scans the `.github/` directory by default (workflows and composite actions); a repo-root `action.yml`/`action.yaml` is only picked up with `--recursive`
- GITHUB_TOKEN is set via `gh auth token` to avoid API rate limits
- `actions-up` runs via `npx` — no global install required
