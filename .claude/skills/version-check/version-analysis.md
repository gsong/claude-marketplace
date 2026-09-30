# Per-plugin version analysis

Decide whether the plugin named in your prompt needs a version bump. `{PLUGIN_NAME}` is the plugin name, `{PLUGIN_DIR}` its directory, and `{CURRENT_VERSION}` its current `version`. You are done when you have classified every changed file since the anchor.

## Step 1 — Find the version anchor

Run: `git log -L '/"version"/,+1:{PLUGIN_DIR}/.claude-plugin/plugin.json' --format="%H" -s`

The first SHA in the output is the **anchor**: the most recent commit that changed the `version` line itself. Anchor on the version line, not the whole file — a description or keyword edit to plugin.json would otherwise reset the anchor and hide real changes since the last bump.

If the command errors or returns empty output, report bump `none` with reasoning "Plugin has no version history yet."

## Step 2 — Get changes since the anchor

1. Run `git diff {SHA} -- {PLUGIN_DIR}/`. It diffs against the working tree, so uncommitted edits count.
2. Run `git status --porcelain -- {PLUGIN_DIR}/`. Untracked files are changes too: a new skill that isn't committed yet still warrants a bump.

If both are empty, report bump `none` with reasoning "No changes since last version bump."

## Step 3 — Classify

Read the full diff. Then run `git log --format="%s" {SHA}..HEAD -- {PLUGIN_DIR}/`. This repo uses conventional commits, so the subjects signal intent: `feat:` → minor, `fix:`/`docs:`/`chore:` → patch, `!` or BREAKING CHANGE → major. The diff is the ground truth; use the subjects to confirm or question your classification.

| Bump              | Criteria                                                                                                                                                        |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Patch** (x.y.Z) | Bug fixes, typo corrections, wording/formatting improvements, documentation updates within existing skills, minor clarifications, updated dependency references |
| **Minor** (x.Y.0) | New skills added, new capabilities or features in existing skills, non-breaking behavioral changes, significant documentation restructuring                     |
| **Major** (X.0.0) | Renamed or removed skills, changed skill invocation patterns, removed functionality, fundamental behavior changes that would surprise existing users            |

The plugin's bump is the highest level any single change reaches. Between two levels for one change, pick the lower.

## Step 4 — Report

Respond with EXACTLY this format (no other text):

```
PLUGIN: {PLUGIN_NAME}
CURRENT_VERSION: {CURRENT_VERSION}
BUMP: none|patch|minor|major
NEW_VERSION: {calculated new version, or same as current if none}
CHANGED_FILES: {comma-separated list of changed files relative to repo root, or "none"}
REASONING: {1-2 sentence explanation of why this bump level was chosen}
CHANGES_SUMMARY: {1-2 sentence human-readable summary of what changed}
```
