---
name: marketplace-validate
description: "Validate every plugin, the marketplace registry, and the root README for internal consistency, and fix what can be fixed."
disable-model-invocation: true
---

# Marketplace Consistency Validation

Validate that every plugin, the marketplace registry, and the root `README.md` are internally consistent, then fix the issues. Runs bottom-up: validate each plugin in parallel, then cross-validate the registry and the root README against the plugins.

## Phase 1 — Discovery

1. Read `.claude-plugin/marketplace.json` to get the plugin list.
2. Run `/bin/ls plugins/` to enumerate actual plugin directories on disk.
3. Build a working list of all plugins (union of marketplace entries and disk directories).

Done when the working list names every plugin from both sources.

## Phase 2 — Per-Plugin Validation (Parallel Agents)

Spawn **one Agent per plugin** in a single message, so they run in parallel. Use `subagent_type: "general-purpose"` and name each agent `validate-{PLUGIN_NAME}`. Each agent receives this prompt (fill in `{PLUGIN_NAME}` and `{PLUGIN_DIR}`):

> Validate the plugin `{PLUGIN_NAME}` at `{PLUGIN_DIR}`. Read `.claude/skills/marketplace-validate/plugin-checks.md` and perform every check in it. Respond in exactly the report format it gives.

Done when every plugin in the working list has returned a report.

## Phase 3 — Registry, Root README, and Security Scan

Run these checks yourself. Each ends with its **Fix**, as in `plugin-checks.md`.

### marketplace.json

1. **Orphan directories**: every directory under `plugins/` has an entry in `marketplace.json`. **Fix:** add the entry, copying `name`, `description`, `author`, and `keywords` from its `plugin.json`; ask for `category`.
2. **Phantom entries**: every entry has a directory under `plugins/` (resolve `source` relative to the repo root). **Fix: ask.**
3. **Name consistency**: each entry's `name` matches its `plugin.json` `name`. **Fix: ask.**
4. **Description consistency**: each entry's `description` matches its `plugin.json` `description` exactly. **Fix:** copy the `plugin.json` value.
5. **Keyword consistency**: each entry's `keywords` match its `plugin.json` `keywords` (same items, any order). **Fix:** copy the `plugin.json` value.
6. **Author consistency**: each entry's `author` matches its `plugin.json` `author`. **Fix:** copy the `plugin.json` value.
7. **Marketplace metadata**: `metadata.description` names every plugin's domain, with one word or phrase per entry. Flag each plugin it leaves out. **Fix:** add the missing domain to the list.

### Root README.md

The `## Plugins` section is a table with one row per plugin: the plugin name, linked to `plugins/{PLUGIN_NAME}/README.md`, and what it does. Skills, hooks, and prerequisites live only in each plugin's README, which `plugin-checks.md` section H covers.

8. **Row coverage**: every marketplace entry has a row, and every row has an entry. **Fix:** add a missing row in the existing format, in alphabetical order; remove a row with no entry.
9. **Link**: each row links to `plugins/{PLUGIN_NAME}/README.md`. **Fix:** rewrite the link.
10. **Description**: the "What it does" cell matches the `plugin.json` `description`, with a trailing period. **Fix:** copy the `plugin.json` value.

### Security scan

11. **Skill scan**: run `mise run scan:skills` once for the whole repo. The task installs the scanner on first run. Skip this check when mise is not installed or the scanner install fails, and say so in the report. Report each high or critical finding with its rule, skill, and file. **Fix: ask.** The user decides whether to fix the skill or add a suppression with a reason to `skill-scanner-policy.yaml`.

Done when checks 1–10 have a verdict for every plugin and check 11 has a verdict for the repo.

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

Root README
───────────
[ ] Description mismatch: writing — README says "X", plugin.json says "Y"
[✓] Every plugin has a row
...

Security Scan
─────────────
[ ] High PIPELINE_TAINT_FLOW: example-plugin/example-skill — scripts/install.sh:12
[✓] No high or critical findings

Summary: X issues found across Y plugins
```

## Phase 5 — Fix

Apply the **Fix** that each issue carries, using the Edit tool. Collect every issue marked **Fix: ask** and put them to the user in one `AskUserQuestion` call, then apply their answers. Hold any fix that builds on an ask issue — such as documenting a hook event whose name is in question — until that answer is in, and apply it from the answer.

Leave the fixes uncommitted in the working tree for the user to review, and finish with a summary of the edits made.

Done when every issue in the Phase 4 report is fixed, answered by the user, or listed as open in the summary.
