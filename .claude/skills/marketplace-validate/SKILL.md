---
name: marketplace-validate
description: "Validate every plugin and the marketplace registry for internal consistency, and fix what can be fixed."
disable-model-invocation: true
---

# Marketplace Consistency Validation

Validate that every plugin and the marketplace registry are internally consistent. Runs bottom-up: validate each plugin in parallel, then cross-validate against the marketplace registry. Fixes issues directly when possible.

## Phase 1 — Discovery

1. Read `.claude-plugin/marketplace.json` to get the plugin list.
2. Run `/bin/ls plugins/` to enumerate actual plugin directories on disk.
3. Build a working list of all plugins (union of marketplace entries and disk directories).

## Phase 2 — Per-Plugin Validation (Parallel Agents)

Spawn **one Agent per plugin** using the Agent tool. Run all agents in parallel (send all Agent tool calls in a single message).

Use `subagent_type: "general-purpose"` for each agent. Give each agent a descriptive name like `validate-{PLUGIN_NAME}`. Each agent receives this prompt (fill in `{PLUGIN_NAME}` and `{PLUGIN_DIR}`):

> Validate the plugin `{PLUGIN_NAME}` at `{PLUGIN_DIR}`. Read `.claude/skills/marketplace-validate/plugin-checks.md` and perform every check in it. Respond in exactly the report format it gives.

## Phase 3 — Marketplace Registry Validation

After all plugin agents complete, validate the marketplace registry yourself:

### marketplace.json cross-checks

1. **Orphan directories**: Every directory under `plugins/` has a corresponding entry in `marketplace.json`
2. **Phantom entries**: Every entry in `marketplace.json` has a corresponding directory under `plugins/` (resolving `source` relative to the repo root)
3. **Name consistency**: Each marketplace entry's `name` matches the corresponding `plugin.json` `name`
4. **Description consistency**: Each marketplace entry's `description` matches the corresponding `plugin.json` `description` (exact match)
5. **Keyword consistency**: Each marketplace entry's `keywords` match the corresponding `plugin.json` `keywords` (same items, order-independent)
6. **Author consistency**: Each marketplace entry's `author` matches the corresponding `plugin.json` `author`
7. **Marketplace metadata**: `metadata.description` names every plugin's domain: for each marketplace entry, one word or phrase in the description covers it. Flag each plugin it leaves out.

## Phase 4 — Report

Present a consolidated report:

```
Marketplace Validation Report
═══════════════════════════════

Plugin Results
──────────────
Plugin          Status   Issues
─────────────── ──────── ──────
ai-docs         pass     0
git-tools       fail     2
...

Marketplace Registry
────────────────────
[ ] Description mismatch: git-tools — marketplace says "X", plugin.json says "Y"
[✓] All plugin directories have marketplace entries
...

Summary: X issues found across Y plugins
```

## Phase 5 — Fix

If any issues were found:

1. Group issues by type (description mismatches, missing README entries, frontmatter problems, etc.)
2. Fix each issue directly using the Edit tool:
   - **Description mismatches**: Use the plugin.json value as the source of truth for marketplace.json; use the SKILL.md body as the source of truth for skill descriptions
   - **Missing README entries**: Add them following the existing README format for that plugin
   - **Orphan README entries**: Remove them
   - **Keyword mismatches**: Use plugin.json as the source of truth
   - **Missing frontmatter fields**: Add them based on the skill content
   - **Preamble inaccuracies**: Rewrite the description to accurately reflect the skill body
3. After all fixes, present a summary of changes made
4. For issues that can't be auto-fixed (e.g., ambiguous intent), report them and ask the user

Leave the fixes uncommitted in the working tree for the user to review.
