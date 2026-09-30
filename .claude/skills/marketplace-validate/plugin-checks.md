# Per-plugin validation checks

Run every check below against the plugin named in your prompt. `{PLUGIN_NAME}` is the plugin name and `{PLUGIN_DIR}` its directory. You are done when every check has a verdict: pass, an issue, or not applicable because the directory or file does not exist.

Each check ends with its **Fix**: the source of truth and the edit that resolves the issue. The orchestrator applies these fixes, so copy the fix into the issue line. A check marked **Fix: ask** has no safe automatic edit; the orchestrator asks the user.

Lists copied from the Claude Code docs carry their source and the date they were last checked. When a plugin uses a key or event missing from a list, open the source URL before you flag it: the list may be stale.

---

### A. Plugin Manifest (`{PLUGIN_DIR}/.claude-plugin/plugin.json`)

1. File exists and is valid JSON. **Fix: ask.**
2. Required fields present: `name`, `description`, `version`. Claude Code itself requires only `name`; this repo requires the other two because the marketplace registry copies `description` and `/version-check` bumps `version`. **Fix:** add the field. Take `description` from the plugin README's opening line; ask for a missing `version`.
3. `name` matches the plugin directory name (`{PLUGIN_NAME}`). **Fix: ask** — a rename changes every install command.
4. `version` is valid semver (e.g., `1.0.0`, `2.1.3`). **Fix: ask.**
5. If `keywords` present, it's a non-empty array of strings. **Fix:** remove non-strings or an empty array.
6. If `hooks` field present, the referenced file exists and is valid JSON. **Fix: ask.**
7. If `author` present, it has a `name` field. **Fix:** set `name` to the marketplace entry's `author.name`.

### B. Skills (`{PLUGIN_DIR}/skills/`)

For each subdirectory under `skills/`:

1. Contains a `SKILL.md` file. **Fix: ask.**
2. `SKILL.md` has valid YAML frontmatter (between `---` delimiters at the top). **Fix:** repair the YAML syntax without changing values.
3. Frontmatter has a `description` field (required). **Fix:** write one from the skill body.
4. Frontmatter has a `name` field equal to the skill directory name (`a-z0-9-`), as the Agent Skills spec requires. Flag a missing `name`, a mismatch, or any prefix such as `gs:` or `{PLUGIN_NAME}:`. In a plugin, `name` sets the last segment of the command, so a mismatch makes `/{PLUGIN_NAME}:{name}` differ from the directory every other doc names. **Fix:** set `name` to the directory name.
5. **Frontmatter key spelling**: every key is one Claude Code documents. Claude Code silently ignores unknown keys, so a misspelled key means its behavior never takes effect. Flag lookalikes such as `allowed_tools`, `allowedTools`, `tools`, or `when-to-use` (the real key is `when_to_use`). **Fix:** rename the key to its documented spelling.

   Documented keys (source: https://code.claude.com/docs/en/skills, checked 2026-09-30): `name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`, `compatibility`.

6. **Model pins**: a `model` field belongs alongside `context: fork`, where it sets the spawned subagent's model. On an inline skill it switches the session model for the rest of the turn, and a smaller context window than the session already holds has caused failures here. Flag any `model` without `context: fork`. **Fix: ask** — either add `context: fork` or remove `model`.
7. **Invocation reference**: flag any description line that says the skill is used when the user invokes a slash command (e.g. "Also use when the user invokes /…"). Typing the command loads the skill directly, so the line only spends description space. When a description names another skill, it uses the bare Skill tool name `{plugin}:{skill}`. **Fix:** delete the invocation line; rewrite other skill references as `{plugin}:{skill}`.
8. **Preamble accuracy**: read the FULL skill body (everything after the frontmatter). The `description` is an accurate summary of what the skill does. Flag a description that is misleading, outdated, or missing key functionality, and say specifically what is wrong. **Fix:** rewrite the description from the skill body.

### C. Hooks (`{PLUGIN_DIR}/hooks/`)

If a hooks directory exists:

1. `hooks.json` exists and is valid JSON. **Fix: ask.**
2. Has a top-level `hooks` object. **Fix: ask.**
3. Each hook event key is a documented event. **Fix: ask.**

   Documented events (source: https://code.claude.com/docs/en/hooks, checked 2026-09-30): `SessionStart`, `SessionEnd`, `Setup`, `UserPromptSubmit`, `UserPromptExpansion`, `Stop`, `StopFailure`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`, `PostToolBatch`, `Notification`, `MessageDisplay`, `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `TeammateIdle`, `FileChanged`, `DirectoryAdded`, `CwdChanged`, `WorktreeCreate`, `WorktreeRemove`, `ConfigChange`, `InstructionsLoaded`, `PreCompact`, `PostCompact`, `PreModelSwitch`, `PostModelSwitch`, `Elicitation`, `ElicitationResult`.

4. Each hook entry has a `hooks` array of objects with `type` and `command`. **Fix: ask.**
5. Every script a command references exists on disk (resolve `${CLAUDE_PLUGIN_ROOT}` to `{PLUGIN_DIR}`). **Fix: ask.**
6. If plugin.json has a `hooks` field, the referenced file exists and is valid JSON. Claude Code auto-loads `hooks/hooks.json` and merges the `hooks` field into it (source: https://code.claude.com/docs/en/plugins/manifest-reference, checked 2026-09-30). A `hooks` field that resolves to `hooks/hooks.json` is redundant: report it as a NOTE, not an issue. **Fix:** remove the redundant field.

### D. Supporting Files

Covers every non-component directory at the plugin root: `resources/`, `scripts/`, `references/`, `defaults/`, `tests/`, and `bin/`. Claude Code puts `bin/` on the Bash tool's `PATH` while the plugin is enabled.

1. Every file in these directories is non-empty. **Fix: ask.**
2. Every supporting file referenced from a SKILL.md, reference doc, or hook (via `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_SKILL_DIR}`, a script-relative path, or a relative path) exists on disk. **Fix: ask.**
3. Every file in `bin/`, and every script invoked directly (not through an interpreter like `bash script.sh`), has the executable bit set. **Fix:** `chmod +x` the file.
4. A symlink resolves to an existing file. **Fix: ask.**
5. Report as a NOTE any file that no SKILL.md, reference doc, hook, script, or other supporting file references — it may be dead weight. Test files (`tests/*`, `test_*`) and their helpers are exempt; D.6 covers them.
6. Every test file is run by `.github/workflows/test.yml`. A glob such as `plugins/writing/tests/*.test.mjs` counts. **Fix:** add a step that runs it, matching the existing jobs.

### E. Agents (`{PLUGIN_DIR}/agents/`)

If an agents directory exists:

1. Each agent is a `.md` file under `agents/`. Subfolders load too, and their names become part of the agent name (`agents/review/security.md` → `{PLUGIN_NAME}:review:security`). **Fix: ask.**
2. Each `.md` file has valid YAML frontmatter with at minimum a `description` field. **Fix:** write the description from the agent body.
3. If frontmatter has a `name` field, it matches the file name (without `.md`). **Fix:** set `name` to the file name.

### F. Commands (`{PLUGIN_DIR}/commands/`)

If a commands directory exists:

1. Each `.md` file has valid YAML frontmatter. **Fix:** repair the YAML syntax without changing values.
2. Frontmatter has a `description` field. **Fix:** write it from the command body.

### G. Other Plugin Files

1. `.mcp.json`, `.lsp.json`, `settings.json`, and `monitors/monitors.json` at the plugin root are valid JSON when present. **Fix: ask.**
2. `settings.json` holds only `agent` and `subagentStatusLine`; Claude Code drops every other key. **Fix: ask.**
3. `output-styles/`, `themes/`, and `workflows/` are recognized component directories: note their presence and check that each file in them is non-empty. **Fix: ask.**

### H. README.md

1. `README.md` exists. **Fix: ask.**
2. Every skill directory under `skills/` is mentioned in the README. **Fix:** add the skill, following the README's existing format for its other skills.
3. Every skill mentioned in the README exists as a directory under `skills/`. **Fix:** remove the orphan entry.
4. The README's opening description is consistent with the `plugin.json` description. **Fix:** rewrite the README line from `plugin.json`.
5. If the plugin has hooks, the README documents each hook event. **Fix:** add the missing event to the README's hooks section.
6. If the plugin has agents, the README documents them. **Fix:** add them, following the README's existing format.

---

**Report format**: Respond with EXACTLY this format:

```
PLUGIN: {PLUGIN_NAME}
STATUS: pass|fail
ISSUES:
- [CATEGORY] description of issue — Fix: the edit, or "ask"
- [CATEGORY] ...
NOTES:
- Observations that aren't failures but worth flagging (e.g., optional fields missing)
```

If no issues are found, set STATUS to `pass` and ISSUES to `none`.
Categories: MANIFEST, SKILL:{name}, HOOKS, RESOURCES, AGENTS, COMMANDS, MCP, LSP, SETTINGS, README
