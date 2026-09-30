# Per-plugin validation checks

Perform every check below for the plugin named in your prompt and report findings. `{PLUGIN_NAME}` is the plugin name and `{PLUGIN_DIR}` its directory.

**Important**: Use the Read tool to read files, Glob to find files, and Grep to search content.

---

### A. Plugin Manifest (`{PLUGIN_DIR}/.claude-plugin/plugin.json`)

1. File exists and is valid JSON
2. Required fields present: `name`, `description`, `version`
3. `name` matches the plugin directory name (`{PLUGIN_NAME}`)
4. `version` is valid semver (e.g., `1.0.0`, `2.1.3`)
5. If `keywords` present, it's a non-empty array of strings
6. If `hooks` field present, the referenced file exists and is valid JSON
7. If `author` present, it has a `name` field

### B. Skills (`{PLUGIN_DIR}/skills/`)

For each subdirectory under `skills/`:

1. Contains a `SKILL.md` file
2. `SKILL.md` has valid YAML frontmatter (between `---` delimiters at the top)
3. Frontmatter has a `description` field (required)
4. Frontmatter has a `name` field equal to the skill directory name, as the Agent Skills spec requires (`a-z0-9-`, matching the parent directory). Flag a missing `name`, a mismatch, or any prefix such as `gs:` or `{PLUGIN_NAME}:`. Claude Code ignores `name` for this layout and always invokes the skill as `/{PLUGIN_NAME}:{skill-dir-name}`, so a prefixed `name` only misleads.
5. **Frontmatter key spelling**: The keys this marketplace uses are `name`, `description`, and `compatibility` (from the Agent Skills spec), plus the Claude Code extensions `argument-hint`, `allowed-tools`, `disable-model-invocation`, `context`, `agent`, and `model`. Flag lookalike keys such as `allowed_tools`, `allowedTools`, `tools`, or `when-to-use` — Claude Code silently ignores unknown keys, so a misspelled key means the behavior it was meant to apply never takes effect.
6. **Model pins**: A `model` field is only safe alongside `context: fork`, where it applies to the spawned subagent. On an inline skill it overrides the model for the whole conversation while the skill is active, which has already caused context-window failures here. Flag any `model` without `context: fork`.
7. **Invocation reference**: Flag any description line that says the skill is used when the user invokes a slash command (e.g. "Also use when the user invokes /…"). Typing the command loads the skill directly, so the line only spends description space. When a description names another skill, it uses the bare Skill tool name `{plugin}:{skill}`, not a slash command and not a `gs:` prefix.
8. **Preamble accuracy**: Read the FULL skill body (everything after the frontmatter). Check that the `description` field is an accurate summary of what the skill actually does. Flag if the description is misleading, outdated, or missing key functionality. Be specific about what's wrong.

### C. Hooks (`{PLUGIN_DIR}/hooks/`)

If a hooks directory exists:

1. `hooks.json` exists and is valid JSON
2. Has a top-level `hooks` object
3. Each hook event key is one the Claude Code hooks reference lists (https://code.claude.com/docs/en/hooks): `SessionStart`, `SessionEnd`, `Setup`, `UserPromptSubmit`, `UserPromptExpansion`, `Stop`, `StopFailure`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`, `PostToolBatch`, `Notification`, `MessageDisplay`, `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `TeammateIdle`, `FileChanged`, `DirectoryAdded`, `CwdChanged`, `WorktreeCreate`, `WorktreeRemove`, `ConfigChange`, `InstructionsLoaded`, `PreCompact`, `PostCompact`, `PreModelSwitch`, `PostModelSwitch`, `Elicitation`, `ElicitationResult`
4. Each hook entry has `hooks` array with objects containing `type` and `command`
5. Any script files referenced by commands exist on disk (resolve `${CLAUDE_PLUGIN_ROOT}` to `{PLUGIN_DIR}`)
6. If the plugin.json has a `hooks` field:
   - The referenced file must exist and be valid JSON
   - **Duplicate detection**: `hooks/hooks.json` is auto-loaded by Claude Code. If the `hooks` field resolves to `hooks/hooks.json` (e.g., `"./hooks/hooks.json"`), flag it as an error — the field should be removed to avoid duplicate loading. The `hooks` field should only reference _additional_ hook files beyond the standard `hooks/hooks.json`.

### D. Supporting Files (`{PLUGIN_DIR}/resources/`, `scripts/`, `references/`)

For each of these directories that exists:

1. Every file in the directory is non-empty
2. Every supporting file referenced from a SKILL.md or hook (via `${CLAUDE_PLUGIN_ROOT}`, `$CLAUDE_SKILL_DIR`, or relative paths) actually exists on disk
3. Scripts invoked directly (not through an interpreter like `bash script.sh`) have the executable bit set
4. Note (as a NOTE, not a failure) any file that no SKILL.md, hook, or command references — it may be dead weight

### E. Agents (`{PLUGIN_DIR}/agents/`)

If an agents directory exists:

1. Each agent is a `.md` file directly inside `agents/` — Claude Code does not load agents from subdirectories
2. Each `.md` file has valid YAML frontmatter with at minimum a `description` field
3. If frontmatter has a `name` field, it matches the file name (without `.md`)

### F. Commands (`{PLUGIN_DIR}/commands/`)

If a commands directory exists:

1. Each `.md` file has valid YAML frontmatter
2. Frontmatter has a `description` field

### G. Other Plugin Files

1. If `.mcp.json` exists at plugin root, it's valid JSON
2. If `.lsp.json` exists at plugin root, it's valid JSON
3. If `settings.json` exists at plugin root, it's valid JSON

### H. README.md

1. `README.md` exists
2. Every skill directory under `skills/` is mentioned in the README
3. Every skill mentioned in the README actually exists as a directory under `skills/`
4. The README's opening description is consistent with `plugin.json` description
5. If the plugin has hooks, the README documents them
6. If the plugin has agents, the README documents them

---

**Report format**: Respond with EXACTLY this format:

```
PLUGIN: {PLUGIN_NAME}
STATUS: pass|fail
ISSUES:
- [CATEGORY] description of issue (e.g., [SKILL:commit] description missing from frontmatter)
- [CATEGORY] ...
NOTES:
- Any observations that aren't failures but worth flagging (e.g., optional fields missing)
```

If no issues found, set STATUS to `pass` and ISSUES to `none`.
Categories: MANIFEST, SKILL:{name}, HOOKS, RESOURCES, AGENTS, COMMANDS, MCP, LSP, SETTINGS, README
