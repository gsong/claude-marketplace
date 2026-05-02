---
name: gs:repo-maintenance:mise
description: Use when the user asks to upgrade, update, or bump mise-managed tool versions in `mise.toml`, or wants to check for outdated tools managed by mise. Also use when the user invokes /gs:repo-maintenance:mise.
---

# Upgrade mise-managed tool versions

Upgrade tool versions pinned in `mise.toml` using [mise](https://mise.jdx.dev/).

## Process

### 1. Pre-flight checks

1. **Check mise is available**: Run `mise --version`. If not installed, abort: "mise is not installed — see https://mise.jdx.dev/getting-started.html"
2. **Locate mise config**: Check for `mise.toml` (preferred) in the project root. Also accept `.mise.toml` as a fallback. If neither exists, abort: "No mise.toml found in project root."

### 2. Check for outdated tools

Run: `mise outdated --bump`

- The `--bump` flag compares against the latest available versions (not just within the pinned range), surfacing all upgrade candidates.
- Present the full output to the user. Columns are: Plugin, Requested, Current, Latest.
- If the output is empty, inform the user that all mise tools are up to date and stop.

### 3. Research significant updates

For tools with major or minor version changes shown in the outdated output, research changelogs and release notes for new features and breaking changes that could affect this project. Present findings to the user alongside the outdated results.

### 4. Confirm with user

Use the AskUserQuestion tool to confirm whether to apply the bump. Offer options:

- Bump all tools to latest
- Bump a subset (let the user specify which)
- Cancel

### 5. Apply updates

Based on the user's choice:

- **All tools**: `mise upgrade --bump`
- **Subset**: `mise upgrade --bump <tool1> <tool2> ...`

Notes on flags:

- `--bump` rewrites the version pin in `mise.toml` to the latest available version. Without it, `mise upgrade` keeps the pinned range and only installs newer matching versions, which would not update `mise.toml`.
- `--dry-run` / `-n` previews changes without applying. Useful if the user wants to inspect the plan before committing.
- `--interactive` / `-i` shows a selection menu — only use this if the user is at the terminal and explicitly wants it.

### 6. Verify

1. Run `mise outdated --bump` again to confirm the targeted tools are now up to date.
2. Show the user the diff of `mise.toml` so they can see exactly what was bumped.
3. Remind the user that some tools may need their per-project lockfiles, caches, or dependencies regenerated (e.g., reinstalling node_modules after a Node bump).

## Important Notes

- This skill updates `mise.toml` only — it does not perform git operations (branch, commit, push, PR).
- `mise upgrade --bump` mutates `mise.toml` in place. There is no separate "references" sweep like the `pnpm` skill — `mise.toml` is the single source of truth.
- mise has no native `minimumReleaseAge` concept. If the project uses `renovate.json` with rules that gate mise updates by age, defer to Renovate for those tools instead of running this skill.
- If the project also pins tool versions outside `mise.toml` (e.g., `.tool-versions`, `.nvmrc`, Dockerfiles, GitHub Actions `setup-*` steps), those will not be touched. Flag any such drift to the user for manual sync.
