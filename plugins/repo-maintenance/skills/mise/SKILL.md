---
name: "mise"
description: "Upgrade mise-managed tool versions in mise.toml, respecting minimum_release_age. Use when the user asks to bump mise-managed tools or check which are outdated."
compatibility: "Requires mise and network access to resolve tool versions."
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

1. Read `${CLAUDE_PLUGIN_ROOT}/references/release-age.md`, resolve the project-wide value (for renovate `packageRules`, match entries covering mise-managed tools), and convert to mise's `Nd`/`Nh`/`Nm` format (e.g., `10080` minutes → `7d`). Only an explicit project value counts here; the reference's 7-day default stays out of `mise.toml`, because mise honors a cool-down only from its own config.
2. If a project-wide value is found, recommend adding `minimum_release_age = "Nd"` under `[settings]` in `mise.toml` to align mise with the existing policy. Use AskUserQuestion to confirm before editing.
3. If no project-wide value is found, inform the user that mise will resolve `latest` pins immediately and proceed without adding the setting.

### 3. Check for outdated tools

Run: `mise outdated --bump`

- The `--bump` flag compares against the latest available versions (not just within the pinned range), surfacing all upgrade candidates.
- If `minimum_release_age` is set, mise automatically filters out versions younger than the threshold — no extra flag needed.
- Present the full output to the user. Columns are: Plugin, Requested, Current, Latest.
- If the output is empty, inform the user that all mise tools are up to date and stop.

### 4. Research significant updates

For every major or minor bump, present either the breaking changes found or an explicit 'no changelog located'.

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
- Run it non-interactively.

### 7. Verify

1. Run `mise outdated --bump` again to confirm the targeted tools are now up to date.
2. Show the user the diff of `mise.toml` so they can see exactly what was bumped.
3. Search the repo for each bumped tool's old version outside `mise.toml` (`.tool-versions`, `.nvmrc`, Dockerfiles, GitHub Actions `setup-*` steps). List every hit for the user to sync by hand.
4. Remind the user that some tools may need their per-project lockfiles, caches, or dependencies regenerated (e.g., reinstalling node_modules after a Node bump).

## Important Notes

- This skill updates `mise.toml` only. Stop after editing; the user commits.
