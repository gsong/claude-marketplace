---
name: "pnpm"
description: "Upgrade the pnpm version itself across every reference in the project, respecting minimumReleaseAge. Use when the user asks to upgrade the pnpm version itself (not project dependencies — use repo-maintenance:pnpm-deps for that)."
compatibility: "Requires npm (for `npm view`) and network access to the npm registry."
argument-hint: "[version]"
---

# Upgrade pnpm Version

Upgrade pnpm version references across the project, respecting `minimumReleaseAge` constraints.

## Process

### 1. Parse arguments

If the user specified a version (via `$ARGUMENTS` or in their request — e.g., `10.33.0`, `11.0.0-beta.4`), use it as the requested target version. Otherwise, auto-resolve the target.

### 2. Detect current pnpm version

Check these sources in order — stop at the first match:

1. **package.json**: Read the root `package.json` and extract the version from the `packageManager` field (e.g., `"pnpm@9.15.0"` → `9.15.0`)
2. **mise.toml**: Use Grep to search for `pnpm\s*=\s*"` in `mise.toml` or `.mise.toml` and extract the version
3. **GitHub Actions**: Use Grep to search `.github/workflows/` for `version:` lines near `pnpm` context (e.g., under `Setup pnpm` steps)

If no current version is found, abort: "Could not detect pnpm version in this repo."

### 3. Resolve minimumReleaseAge

Read `${CLAUDE_PLUGIN_ROOT}/references/release-age.md` and resolve the effective value — for renovate `packageRules`, match entries where `matchPackageNames` includes `"pnpm"`. Normalize to **minutes** (e.g., `"3 days"` → 4320), and report the constraint and its source per the reference.

### 4. Resolve target version

**Fetch registry data:**

Run: `npm view pnpm time --json`

This returns a JSON object mapping version strings to ISO 8601 release timestamps.

**If auto-resolving (no user-specified version):**

1. Parse the JSON output
2. Filter out:
   - Pre-release versions (any version containing `-alpha`, `-beta`, `-rc`, or similar suffixes)
   - The special keys `created` and `modified`
3. Filter to versions where `now - release_date >= minimumReleaseAge` in minutes, using the constraint from step 3 (Resolve minimumReleaseAge)
4. From remaining versions, select the one with the highest semver
5. If the selected version equals the current version, inform the user: "pnpm is already at the latest eligible version ({version})." and stop
6. Report the resolved version and its release date

**If user specified a version:**

1. Check that the version exists in the registry data — if not, abort: "Version {version} not found in npm registry"
2. If the version contains a pre-release suffix (alpha, beta, rc), warn: "Warning: {version} is a pre-release version."
3. Calculate the version's age from its release date
4. If the version's age is less than the resolved minimumReleaseAge, warn with specifics: "Warning: Version {version} was released {age} ago but minimumReleaseAge requires {constraint}." Then use AskUserQuestion to ask whether to proceed anyway
5. Report the target version and its release date

### 5. Find and update all pnpm version references

**Find references:**

Use Grep to search the entire repo for the current version string in pnpm-related contexts. Run multiple targeted searches:

1. Search for `pnpm@{current_version}` — catches package.json `packageManager`, Dockerfiles, Docker Compose files, CI scripts
2. Search for `pnpm = "{current_version}"` — catches mise.toml
3. Search for the current version string in `.github/workflows/` files, specifically near `pnpm` context

**Important:** Exclude these paths from all searches:

- `pnpm-lock.yaml`
- `node_modules/`
- `.git/`
- `dist/`
- `build/`

**Verify context:** For each match, confirm it is actually a pnpm version reference by examining the surrounding context.

**Present findings:** Show the user each file and line where a pnpm version reference was found, and the planned replacement.

**Confirm:** Use AskUserQuestion to confirm the planned replacements.

**Update references:**

Use the Edit tool to replace the current version with the target version in each verified location.

**Summarize:** After all updates, list every file that was modified and the change made.

### 6. Verify no remaining old references

Re-run the step 5 searches, same exclusions, with the old version string. If any matches remain, flag them to the user for manual review.

## Important Notes

- This skill updates pnpm version **references** only — it does not run `pnpm install` or update `pnpm-lock.yaml`
- Stop after editing; the user commits.
