# Resolving the release-age cool-down

Shared logic for resolving a project's minimum release age — the cool-down window that guards against upgrading to freshly published (possibly compromised) releases. Skills read this file, resolve the effective value, then normalize it to the unit they need.

## Sources

Check both config files in the project root:

**`renovate.json`** (if it exists):

1. Check top-level `minimumReleaseAge` — applies globally to all packages
2. Check the `packageRules` array for entries matching the ecosystem being upgraded (e.g., `matchManagers` includes `"github-actions"`, or `matchPackageNames` includes `"pnpm"`, or `matchPackagePatterns` referencing relevant patterns) — extract `minimumReleaseAge` from matching rules
3. Values are duration strings: `{number} {unit}` (e.g., `"3 days"`, `"72 hours"`, `"4320 minutes"`)

**`pnpm-workspace.yaml`** (if it exists):

- Look for a top-level `minimumReleaseAge` field — an integer in **minutes** (e.g., `1440` = 1 day, `10080` = 7 days)
- Treat it as a project-wide cool-down hint even though it natively scopes to pnpm — it signals the maintainer's general comfort threshold for new releases

## Parsing durations

Normalize everything to minutes for comparison:

- renovate duration strings: split on space into `{number} {unit}`, then convert — days × 1440, hours × 60, minutes × 1 (e.g., `"3 days"` → 4320, `"24 hours"` → 1440)
- pnpm-workspace values are already minutes

The calling skill then converts the winning value to its own unit, rounding up.

## Combine rule

1. If multiple values are found across sources, use the **largest** (strictest)
2. If none are found, default to **7 days** (10080 minutes) and inform the user: "No minimumReleaseAge found in renovate.json or pnpm-workspace.yaml — defaulting to a 7-day cool-down."
3. Report the effective constraint and its source to the user (e.g., "Using minimumReleaseAge of 3 days from renovate.json", "Using 3 days from pnpm-workspace.yaml as a hint", or "Using 7-day default cool-down")
