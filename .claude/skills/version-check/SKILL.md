---
name: version-check
description: "Audit every plugin's version against its changes since the last bump, and apply the bumps you pick."
disable-model-invocation: true
---

# Plugin Version Check

Decide which plugins in this marketplace need a version bump, based on their changes since the last one. Parallel agents analyze the diffs; you collect their reports and apply the bumps the user picks.

## Phase 1 — Discovery

1. Run `/bin/ls plugins/` to enumerate all plugin subdirectories.
2. For each plugin, read `plugins/{name}/.claude-plugin/plugin.json` and extract the current `"version"` value.
3. Build a working list:
   ```
   plugin: git-tools,       dir: plugins/git-tools,       version: 1.1.0
   plugin: ai-docs,         dir: plugins/ai-docs,         version: 1.1.0
   ...
   ```

Done when the working list has a version for every plugin directory.

## Phase 2 — Parallel Analysis

Spawn **one Agent per plugin** in a single message, so they run in parallel. Use `subagent_type: "general-purpose"` and name each agent `version-check-{PLUGIN_NAME}`. Each agent receives this prompt (fill in `{PLUGIN_NAME}`, `{PLUGIN_DIR}`, and `{CURRENT_VERSION}`):

> Analyze the plugin `{PLUGIN_NAME}` at `{PLUGIN_DIR}` (current version: `{CURRENT_VERSION}`). Read `.claude/skills/version-check/version-analysis.md` and follow every step in it. Respond in exactly the report format it gives.

Done when every plugin in the working list has returned a report.

## Phase 3 — Report

Present the collected reports as a summary table:

```
Plugin          Current  Bump     New      Reason
─────────────── ──────── ──────── ──────── ──────────────────────────────
git-tools       1.1.0    minor    1.2.0    Added new X capability
ai-docs         1.1.0    none     1.1.0    No changes since last bump
codex-tools     1.0.0    patch    1.0.1    Fixed typo in skill description
utilities       1.1.0    none     1.1.0    No changes since last bump
```

Below the table, for each plugin with a recommended bump (not "none"), show:

- **Changed files:** list of files that changed
- **Changes summary:** what changed
- **Reasoning:** why this bump level

If no plugin needs a bump, report "All plugins are up to date — no version bumps needed." and stop.

## Phase 4 — Apply (User-Confirmed)

Ask which bumps to apply with one `AskUserQuestion` call using `multiSelect: true`. List each plugin that needs a bump as an option, with its recommendation as the description.

For each approved bump, edit only the `"version"` value in `plugins/{name}/.claude-plugin/plugin.json`. Then show the final state:

```
Applied version bumps:
  git-tools:    1.1.0 → 1.2.0
  codex-tools:  1.0.0 → 1.0.1
```

Done when every approved bump is in its plugin.json and the final state is shown.
