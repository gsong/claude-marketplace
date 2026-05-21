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

### 2. Resolve minimum_release_age

Mise supports a [`minimum_release_age`](https://mise.jdx.dev/configuration/settings.html#minimum_release_age) setting that ignores newly published versions until they've been available for a configurable amount of time — protection against compromised brand-new releases. It applies when resolving fuzzy pins like `latest` or `node@22`; explicitly pinned exact versions bypass it. Only supported backends (aqua, cargo, npm, pipx, some core plugins) honor it.

**Detect current setting in `mise.toml` or `.mise.toml`:**

1. Look for `minimum_release_age` under `[settings]` (e.g., `minimum_release_age = "7d"`)
2. If present, report it to the user and use it as-is for the rest of this skill

**If not set in mise config**, check for a project-wide cool-down hint to recommend aligning:

1. **`renovate.json`**: Check top-level `minimumReleaseAge` and any `packageRules` matching mise-managed tools — parse duration strings like `"7 days"`, `"72 hours"`, `"4320 minutes"` and convert to mise's `Nd`/`Nh`/`Nm` format
2. **`pnpm-workspace.yaml`**: Look for top-level `minimumReleaseAge` (integer in minutes) — convert to days (e.g., `10080` → `7d`)
3. If multiple values found, prefer the **largest** (strictest)
4. If a project-wide value is found, recommend adding `minimum_release_age = "Nd"` under `[settings]` in `mise.toml` to align mise with the existing policy. Use AskUserQuestion to confirm before editing.
5. If no project-wide value is found, inform the user that mise will resolve `latest` pins immediately and proceed without adding the setting.

### 3. Check for outdated tools

Run: `mise outdated --bump`

- The `--bump` flag compares against the latest available versions (not just within the pinned range), surfacing all upgrade candidates.
- If `minimum_release_age` is set, mise automatically filters out versions younger than the threshold — no extra flag needed.
- Present the full output to the user. Columns are: Plugin, Requested, Current, Latest.
- If the output is empty, inform the user that all mise tools are up to date and stop.

### 4. Research significant updates

For tools with major or minor version changes shown in the outdated output, research changelogs and release notes for new features and breaking changes that could affect this project. Present findings to the user alongside the outdated results.

### 5. Confirm with user

Use the AskUserQuestion tool to confirm whether to apply the bump. Offer options:

- Bump all tools to latest
- Bump a subset (let the user specify which)
- Cancel

### 6. Apply updates

Based on the user's choice:

- **All tools**: `mise upgrade --bump`
- **Subset**: `mise upgrade --bump <tool1> <tool2> ...`

Notes on flags:

- `--bump` rewrites the version pin in `mise.toml` to the latest available version. Without it, `mise upgrade` keeps the pinned range and only installs newer matching versions, which would not update `mise.toml`.
- `--dry-run` / `-n` previews changes without applying. Useful if the user wants to inspect the plan before committing.
- `--interactive` / `-i` shows a selection menu — only use this if the user is at the terminal and explicitly wants it.
- `--minimum-release-age <DURATION>` overrides the setting for a single invocation, if the user wants a one-off stricter or looser cool-down.

### 7. Verify

1. Run `mise outdated --bump` again to confirm the targeted tools are now up to date.
2. Show the user the diff of `mise.toml` so they can see exactly what was bumped.
3. Remind the user that some tools may need their per-project lockfiles, caches, or dependencies regenerated (e.g., reinstalling node_modules after a Node bump).

## Important Notes

- This skill updates `mise.toml` only — it does not perform git operations (branch, commit, push, PR).
- `mise upgrade --bump` mutates `mise.toml` in place. There is no separate "references" sweep like the `pnpm` skill — `mise.toml` is the single source of truth.
- `minimum_release_age` only filters fuzzy version requests (`latest`, `node@22`); exact pins (`node@22.5.0`) bypass it intentionally.
- If the project also pins tool versions outside `mise.toml` (e.g., `.tool-versions`, `.nvmrc`, Dockerfiles, GitHub Actions `setup-*` steps), those will not be touched. Flag any such drift to the user for manual sync.
