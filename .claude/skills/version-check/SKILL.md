---
name: version-check
description: Use when the user wants to check if plugin versions need bumping, audit version status, or prepare a release. Also use when the user invokes /version-check.
---

# Plugin Version Check

Analyze all plugins in this marketplace to determine if their version numbers need bumping based on changes since the last version update. Use parallel agents for thorough semantic analysis of diffs.

## Phase 1 — Discovery

1. Run `ls plugins/` to enumerate all plugin subdirectories.
2. For each plugin, read `plugins/{name}/.claude-plugin/plugin.json` and extract the current `"version"` value.
3. Build a working list:
   ```
   plugin: git-workflow,    dir: plugins/git-workflow,    version: 1.1.0
   plugin: docs-memory,     dir: plugins/docs-memory,     version: 1.1.0
   ...
   ```

## Phase 2 — Parallel Analysis

Spawn **one Agent per plugin** using the Agent tool. Run all agents in parallel (send all Agent tool calls in a single message).

Each agent receives the following prompt (fill in `{PLUGIN_NAME}`, `{PLUGIN_DIR}`, and `{CURRENT_VERSION}`):

> Analyze the plugin `{PLUGIN_NAME}` at `{PLUGIN_DIR}` (current version: `{CURRENT_VERSION}`) to determine if a version bump is needed.
>
> **Step 1 — Find the version anchor commit:**
> Run: `git log -S '"version"' --format="%H" -- {PLUGIN_DIR}/.claude-plugin/plugin.json`
> Take the first SHA from the output (most recent commit that changed the version string).
> If this command returns empty output, use the SHA of the commit that created the file:
> Run: `git log --diff-filter=A --format="%H" -- {PLUGIN_DIR}/.claude-plugin/plugin.json`
> If both commands return empty output, report: bump = "none", reasoning = "Plugin has no git history yet."
>
> **Step 2 — Get changes since the anchor:**
> Run: `git diff {SHA}..HEAD -- {PLUGIN_DIR}/`
> If the diff is empty, report: bump = "none", reasoning = "No changes since last version bump."
>
> **Step 3 — Semantic analysis:**
> If changes exist, read the full diff output carefully. Classify the changes using this guide:
>
> | Bump              | Criteria                                                                                                                                                        |
> | ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
> | **Patch** (x.y.Z) | Bug fixes, typo corrections, wording/formatting improvements, documentation updates within existing skills, minor clarifications, updated dependency references |
> | **Minor** (x.Y.0) | New skills added, new capabilities or features in existing skills, non-breaking behavioral changes, significant documentation restructuring                     |
> | **Major** (X.0.0) | Renamed or removed skills, changed skill invocation patterns, removed functionality, fundamental behavior changes that would surprise existing users            |
>
> When in doubt between two levels, prefer the lower one.
>
> **Step 4 — Report:**
> Respond with EXACTLY this format (no other text):
>
> ```
> PLUGIN: {PLUGIN_NAME}
> CURRENT_VERSION: {CURRENT_VERSION}
> BUMP: none|patch|minor|major
> NEW_VERSION: {calculated new version, or same as current if none}
> CHANGED_FILES: {comma-separated list of changed files relative to repo root, or "none"}
> REASONING: {1-2 sentence explanation of why this bump level was chosen}
> CHANGES_SUMMARY: {1-2 sentence human-readable summary of what changed}
> ```

Use `subagent_type: "general-purpose"` for each agent. Give each agent a descriptive name like `version-check-{PLUGIN_NAME}`.

## Phase 3 — Report

After all agents complete, collect their reports and present a formatted summary:

```
Plugin          Current  Bump     New      Reason
─────────────── ──────── ──────── ──────── ──────────────────────────────
git-workflow    1.1.0    minor    1.2.0    Added new X capability
docs-memory     1.1.0    none     1.1.0    No changes since last bump
codex-tools     1.0.0    patch    1.0.1    Fixed typo in skill description
utilities       1.1.0    none     1.1.0    No changes since last bump
```

Below the table, for each plugin with a recommended bump (not "none"), show:

- **Changed files:** list of files that changed
- **Changes summary:** what changed
- **Reasoning:** why this bump level

If NO plugins need a bump, report "All plugins are up to date — no version bumps needed." and stop.

## Phase 4 — Apply (User-Confirmed)

If any plugins need bumps, use AskUserQuestion with `multiSelect: true` to ask which bumps to apply. List each plugin needing a bump as an option with its recommendation as the description.

For each approved bump, use the Edit tool to update the `"version"` field in `plugins/{name}/.claude-plugin/plugin.json`. Change only the version value — do not modify any other fields.

After applying, show the final state:

```
Applied version bumps:
  git-workflow: 1.1.0 → 1.2.0
  codex-tools:  1.0.0 → 1.0.1
```
