---
name: marketplace-validate
description: Validate internal consistency of the marketplace and all its plugins. Use when you want to check that plugin manifests, skills, hooks, resources, READMEs, and the marketplace registry are all accurate and consistent with each other. Also use when the user invokes /marketplace-validate.
---

# Marketplace Consistency Validation

Validate that every plugin and the marketplace registry are internally consistent. Runs bottom-up: validate each plugin in parallel, then cross-validate against the marketplace registry. Fixes issues directly when possible.

## Phase 1 — Discovery

1. Read `.claude-plugin/marketplace.json` to get the plugin list.
2. Run `/bin/ls plugins/` to enumerate actual plugin directories on disk.
3. Build a working list of all plugins (union of marketplace entries and disk directories).

## Phase 2 — Per-Plugin Validation (Parallel Agents)

Spawn **one Agent per plugin** using the Agent tool. Run all agents in parallel (send all Agent tool calls in a single message).

Each agent receives the plugin name and directory path, and performs ALL of the following checks. Use `subagent_type: "general-purpose"` for each agent. Give each agent a descriptive name like `validate-{PLUGIN_NAME}`.

### Agent prompt template

Fill in `{PLUGIN_NAME}` and `{PLUGIN_DIR}`:

> Validate the plugin `{PLUGIN_NAME}` at `{PLUGIN_DIR}` for internal consistency. Perform every check below and report findings.
>
> **Important**: Use the Read tool to read files, Glob to find files, and Grep to search content. Do NOT use cat, find, or grep via Bash.
>
> ---
>
> ### A. Plugin Manifest (`{PLUGIN_DIR}/.claude-plugin/plugin.json`)
>
> 1. File exists and is valid JSON
> 2. Required fields present: `name`, `description`, `version`
> 3. `name` matches the plugin directory name (`{PLUGIN_NAME}`)
> 4. `version` is valid semver (e.g., `1.0.0`, `2.1.3`)
> 5. If `keywords` present, it's a non-empty array of strings
> 6. If `hooks` field present, the referenced file exists and is valid JSON
> 7. If `author` present, it has a `name` field
>
> ### B. Skills (`{PLUGIN_DIR}/skills/`)
>
> For each subdirectory under `skills/`:
>
> 1. Contains a `SKILL.md` file
> 2. `SKILL.md` has valid YAML frontmatter (between `---` delimiters at the top)
> 3. Frontmatter has a `description` field (required)
> 4. If frontmatter has a `name` field, it matches the skill directory name
> 5. **Preamble accuracy**: Read the FULL skill body (everything after the frontmatter). Check that the `description` field is an accurate summary of what the skill actually does. Flag if the description is misleading, outdated, or missing key functionality. Be specific about what's wrong.
>
> ### C. Hooks (`{PLUGIN_DIR}/hooks/`)
>
> If a hooks directory exists:
>
> 1. `hooks.json` exists and is valid JSON
> 2. Has a top-level `hooks` object
> 3. Each hook event key is a valid event type (e.g., `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Notification`, `Stop`, `SubagentStop`)
> 4. Each hook entry has `hooks` array with objects containing `type` and `command`
> 5. Any script files referenced by commands exist on disk (resolve `${CLAUDE_PLUGIN_ROOT}` to `{PLUGIN_DIR}`)
> 6. If the plugin.json has a `hooks` field:
>    - The referenced file must exist and be valid JSON
>    - **Duplicate detection**: `hooks/hooks.json` is auto-loaded by Claude Code. If the `hooks` field resolves to `hooks/hooks.json` (e.g., `"./hooks/hooks.json"`), flag it as an error — the field should be removed to avoid duplicate loading. The `hooks` field should only reference _additional_ hook files beyond the standard `hooks/hooks.json`.
>
> ### D. Resources (`{PLUGIN_DIR}/resources/`)
>
> If a resources directory exists:
>
> 1. Every file in the directory is non-empty
> 2. Any resources referenced from SKILL.md files (via `$CLAUDE_SKILL_DIR` relative paths or direct references) actually exist
>
> ### E. Agents (`{PLUGIN_DIR}/agents/`)
>
> If an agents directory exists:
>
> 1. Each subdirectory contains an `AGENT.md` file
> 2. `AGENT.md` has valid YAML frontmatter with at minimum a `description` field
> 3. If frontmatter has a `name` field, it matches the agent directory name
>
> ### F. Commands (`{PLUGIN_DIR}/commands/`)
>
> If a commands directory exists:
>
> 1. Each `.md` file has valid YAML frontmatter
> 2. Frontmatter has a `description` field
>
> ### G. Other Plugin Files
>
> 1. If `.mcp.json` exists at plugin root, it's valid JSON
> 2. If `.lsp.json` exists at plugin root, it's valid JSON
> 3. If `settings.json` exists at plugin root, it's valid JSON
>
> ### H. README.md
>
> 1. `README.md` exists
> 2. Every skill directory under `skills/` is mentioned in the README
> 3. Every skill mentioned in the README actually exists as a directory under `skills/`
> 4. The README's opening description is consistent with `plugin.json` description
> 5. If the plugin has hooks, the README documents them
> 6. If the plugin has agents, the README documents them
>
> ---
>
> **Report format**: Respond with EXACTLY this format:
>
> ```
> PLUGIN: {PLUGIN_NAME}
> STATUS: pass|fail
> ISSUES:
> - [CATEGORY] description of issue (e.g., [SKILL:commit] description missing from frontmatter)
> - [CATEGORY] ...
> NOTES:
> - Any observations that aren't failures but worth flagging (e.g., optional fields missing)
> ```
>
> If no issues found, set STATUS to `pass` and ISSUES to `none`.
> Categories: MANIFEST, SKILL:{name}, HOOKS, RESOURCES, AGENTS, COMMANDS, MCP, LSP, SETTINGS, README

## Phase 3 — Marketplace Registry Validation

After all plugin agents complete, validate the marketplace registry yourself:

### marketplace.json cross-checks

1. **Orphan directories**: Every directory under `plugins/` has a corresponding entry in `marketplace.json`
2. **Phantom entries**: Every entry in `marketplace.json` has a corresponding directory under `plugins/` (resolving `source` relative to the repo root)
3. **Name consistency**: Each marketplace entry's `name` matches the corresponding `plugin.json` `name`
4. **Description consistency**: Each marketplace entry's `description` matches the corresponding `plugin.json` `description` (exact match)
5. **Keyword consistency**: Each marketplace entry's `keywords` match the corresponding `plugin.json` `keywords` (same items, order-independent)
6. **Author consistency**: Each marketplace entry's `author` matches the corresponding `plugin.json` `author`
7. **Marketplace metadata**: `metadata.description` accurately summarizes the set of plugins (check it mentions the major categories/capabilities)

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

Do NOT commit changes — leave them staged for the user to review.
