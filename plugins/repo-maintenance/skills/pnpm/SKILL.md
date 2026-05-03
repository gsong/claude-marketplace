---
name: gs:repo-maintenance:pnpm
description: Use when the user asks to upgrade, update, or bump the pnpm version itself (not dependencies), or wants to update pnpm version references across a project. Also use when the user invokes /gs:repo-maintenance:pnpm.
---

# Upgrade pnpm Version

Upgrade pnpm version references across the project, respecting `minimumReleaseAge` constraints.

## Process

### 1. Parse arguments

If `$ARGUMENTS` contains a version string (e.g., `10.33.0`, `11.0.0-beta.4`), use it as the requested target version. Otherwise, auto-resolve the target.

### 2. Detect current pnpm version

Check these sources in order — stop at the first match:

1. **package.json**: Read the root `package.json` and extract the version from the `packageManager` field (e.g., `"pnpm@9.15.0"` → `9.15.0`)
2. **mise.toml**: Use Grep to search for `pnpm\s*=\s*"` in `mise.toml` or `.mise.toml` and extract the version
3. **GitHub Actions**: Use Grep to search `.github/workflows/` for `version:` lines near `pnpm` context (e.g., under `Setup pnpm` steps)

If no current version is found, abort: "Could not detect pnpm version in this repo."

### 3. Resolve minimumReleaseAge

Check both config files and normalize to minutes:

**pnpm-workspace.yaml:**

- Read the file if it exists
- Look for a top-level `minimumReleaseAge` field — this is an integer in minutes (e.g., `1440` = 1 day)

**renovate.json:**

- Read the file if it exists
- Check top-level `minimumReleaseAge` (applies globally)
- Check `packageRules` array for entries where `matchPackageNames` includes `"pnpm"` and extract their `minimumReleaseAge`
- Parse duration strings to minutes: `"3 days"` → 4320, `"24 hours"` → 1440, `"90 minutes"` → 90
  - Split on space: `{number} {unit}`
  - Multiply: days × 1440, hours × 60, minutes × 1

**Combine:**

- If both exist, use the **larger** (stricter) value
- If neither exists, default to **7 days** (10080 minutes) and inform the user: "No minimumReleaseAge found in pnpm-workspace.yaml or renovate.json — defaulting to a 7-day cool-down."
- Report the effective constraint to the user (e.g., "Using minimumReleaseAge of 3 days (4320 minutes) from renovate.json" or "Using 7-day default cool-down (10080 minutes)")

### 4. Resolve target version

**Fetch registry data:**

Run: `npm view pnpm time --json`

This returns a JSON object mapping version strings to ISO 8601 release timestamps.

**If auto-resolving (no user-specified version):**

1. Parse the JSON output
2. Filter out:
   - Pre-release versions (any version containing `-alpha`, `-beta`, `-rc`, or similar suffixes)
   - The special keys `created` and `modified`
3. Filter to versions where `now - release_date >= minimumReleaseAge` in minutes (using the resolved constraint, which is always set — either from config or the 7-day default)
4. From remaining versions, select the one with the highest semver
5. If the selected version equals the current version, inform the user: "pnpm is already at the latest eligible version ({version})." and stop
6. Report the resolved version and its release date

**If user specified a version:**

1. Check that the version exists in the registry data — if not, abort: "Version {version} not found in npm registry"
2. If the version contains a pre-release suffix (alpha, beta, rc), warn: "Warning: {version} is a pre-release version."
3. Calculate the version's age from its release date
4. If the version's age is less than the resolved minimumReleaseAge (config or 7-day default), warn with specifics: "Warning: Version {version} was released {age} ago but minimumReleaseAge requires {constraint}." Then use AskUserQuestion to ask whether to proceed anyway
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

**Verify context:** For each match, confirm it is actually a pnpm version reference by examining the surrounding context. Do NOT replace version strings that happen to match but are for unrelated packages.

**Present findings:** Show the user each file and line where a pnpm version reference was found, and the planned replacement.

**Update references:**

Use the Edit tool to replace the current version with the target version in each verified location.

**Summarize:** After all updates, list every file that was modified and the change made.

### 6. Verify no remaining old references

Re-run the same Grep searches from step 5 using the old version string. If any matches remain (excluding `pnpm-lock.yaml`, `node_modules/`, `.git/`, `dist/`, `build/`), flag them to the user for manual review.

## Important Notes

- This skill updates pnpm version **references** only — it does not run `pnpm install` or update `pnpm-lock.yaml`
- Pre-release versions are only used when explicitly requested by the user
- The skill does not perform git operations (branch, commit, push, PR) — the user handles those
- When searching for version references, always verify the match is in a pnpm context to avoid false positives
