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

## Phase 3 — Registry and Root README Validation

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

Each plugin has a `### {PLUGIN_NAME}` section with a blurb, an install block, and a **Skills:** line. It also has a **Hooks:** line when it ships hooks, and a **Requires:** line when it has requirements.

8. **Section coverage**: every marketplace entry has a section, and every section has an entry. **Fix:** add a missing section in the existing format, in alphabetical order; remove a section with no entry.
9. **Blurb**: the blurb matches the `plugin.json` `description`, with a trailing period. **Fix:** copy the `plugin.json` value.
10. **Skills line**: it lists `/{PLUGIN_NAME}:{skill}` for exactly the directories under `plugins/{PLUGIN_NAME}/skills/`. **Fix:** add or remove entries to match the directories.
11. **Hooks line**: present exactly when `plugins/{PLUGIN_NAME}/hooks/hooks.json` exists, and it names every event in that file. **Fix:** rewrite the line from `hooks.json` and the hooks section of the plugin README.
12. **Requires line**: it names the same tools and plugins as the requirements section of the plugin README (`Prerequisites` or `Requirements`). When the plugin README has no such section, use the skills' `compatibility` fields. A plugin with neither has no Requires line. The line lists names only and links to the plugin README section for details. **Fix:** rewrite the line from the plugin README.

### Security scan

13. **Skill scan**: run `mise run scan:skills`. Skip this check when mise or the scanner is not installed, and say so in the report. Report each high or critical finding with its rule, skill, and file. **Fix: ask.** The user decides whether to fix the skill or add a suppression with a reason to `skill-scanner-policy.yaml`.

Done when every check above has a verdict for every plugin.

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
[ ] Skills line: writing — lists /writing:foo, which has no skill directory
[✓] Every plugin has a section
...

Security Scan
─────────────
[ ] Critical DATA_EXFIL_SOCKET_CONNECT: clef/ask — scripts/clef.py:318
[✓] No high or critical findings

Summary: X issues found across Y plugins
```

## Phase 5 — Fix

Apply the **Fix** that each issue carries, using the Edit tool. Collect every issue marked **Fix: ask** and put them to the user in one `AskUserQuestion` call, then apply their answers. Hold any fix that builds on an ask issue — such as documenting a hook event whose name is in question — until that answer is in, and apply it from the answer.

Leave the fixes uncommitted in the working tree for the user to review, and finish with a summary of the edits made.

Done when every issue in the Phase 4 report is fixed, answered by the user, or listed as open in the summary.
