# Packaging and where each part runs

Researched 2026-10-11, with live findings to 2026-10-18 and doc claims rechecked 2026-10-18. Marks are defined in [SKILL.md](../SKILL.md#freshness).

## Mechanisms

| Mechanism                               | Plans                                          | How the user installs it                                                                                                 | What it can hold                                                                                                                    |
| --------------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Plugin** (upload or Git marketplace)  | Pro, Max, Team, Enterprise; not Free **[V]**   | Customize > Plugins > Add > **Upload plugin** (.zip or .plugin), or Add > **Add marketplace** with a GitHub `owner/repo` | Skills, commands, remote MCP connectors, agents, hooks, local MCP servers including .mcpb                                           |
| **Agent Skill** (.zip)                  | Pro, Max, Team, Enterprise; Free is disputed\* | Customize > Skills > + > Create skill > Upload a skill. Needs Settings > Capabilities > Code execution on                | SKILL.md plus bundled scripts and files; scripts run in the code sandbox                                                            |
| **Desktop Extension** (.mcpb, was .dxt) | Any plan signed in to Claude Desktop **[V/I]** | Double-click the file, drag it into the window, or Settings > Extensions > Advanced settings > Install Extension         | A local stdio MCP server with real code (Node ships with Desktop; Python, uv or a binary also work), plus a generated settings form |
| **Custom remote connector** (MCP URL)   | Free (one connector), Pro, Max **[V]**         | Customize > Connectors > Add custom connector, paste the HTTPS URL, sign in with OAuth                                   | Only a URL. Anthropic's cloud calls the server, so it must be public HTTPS                                                          |
| **Project**                             | All plans; Free gets 5 projects **[V]**        | Create a project, paste instructions, upload files                                                                       | Instructions and knowledge files; no code and no tools                                                                              |

\* The support article lists Free for skills; the newer docs page lists only
paid plans. **[V, conflicting]**

Sources:

- Plugins are paid-only: https://support.claude.com/en/articles/13837440-use-plugins-in-claude **[V]**
- Upload format: a folder, `.zip` or `.plugin` file "as long as the archive
  holds one `.claude-plugin/plugin.json`". Plugins save to the account and show
  in Chat, Cowork and Claude Code. https://claude.com/docs/plugins/overview **[V]**
- A user can add up to 25 marketplaces. GitHub, GitHub Enterprise and public
  GitLab and Bitbucket repos work. **Sync automatically** works for github.com,
  so a push reaches every user without a reinstall.
  https://claude.com/docs/cowork/guide/plugins **[V]**
- Live, Customize > Plugins > Add plugin > Add marketplace > Add from a
  repository accepted `owner/repo`, with **Sync automatically** on by default.
  A plain question loaded the skill with no slash command. A push reached
  Claude Desktop in under 4 minutes, with no version bump, reinstall or
  restart. The plugin menu offers only "Remove", with no manual update.
  **[V, live 2026-10-11]** A manual update sits on the marketplace instead:
  select **Check for updates** on it.
  https://claude.com/docs/cowork/guide/plugins **[V]**
- In Claude Code, a plugin installs per machine, at user, project or local
  scope, from any Git repository, URL or local path. A plugin turned on for
  the claude.ai account also loads in Claude Code as a synced plugin, at the
  next session start. https://claude.com/docs/plugins/platform-support,
  https://code.claude.com/docs/en/plugins/loading#synced-plugins **[V]**
- Sharing and publishing plugins inside an organization is Team and Enterprise
  only. https://support.claude.com/en/articles/13837440-use-plugins-in-claude **[V]**
- Skills "run in Claude's code sandbox." https://claude.com/docs/skills/overview,
  upload steps at https://support.claude.com/en/articles/12512180-use-skills-in-claude **[V]**
- Desktop Extensions: https://claude.com/docs/connectors/custom/add-unlisted and
  https://claude.com/docs/connectors/building/mcpb. Directory listings for
  .mcpb are deprecated, so a local server reaches the directory only inside a
  plugin. **[V]**
- A privately sent .mcpb updates only when the user installs the new file.
  https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop **[V]**

## Which plugin parts load where

From https://claude.com/docs/plugins/platform-support **[V]**:

| Part                                           | Cowork                                                                | Claude Code                             |
| ---------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------- |
| Skills                                         | Load                                                                  | Load                                    |
| Commands                                       | Load; the user runs one as `/plugin-name:command`                     | Load                                    |
| Agents and hooks                               | Load                                                                  | Load                                    |
| Remote MCP server                              | On the plugin's Connectors tab; works once the user connects it       | Connects directly                       |
| Local MCP server, including `.mcpb`            | Loads only when the Cowork session runs on the user's computer        | Loads                                   |
| MCP server that uses `${user_config.*}`        | Skipped when a referenced option has no default; Cowork never prompts | Loads, and prompts for the values       |
| Top-level `bin/`                               | The plugin cannot be installed                                        | Loads; its files are on the Bash `PATH` |
| LSP servers, output styles, themes, `settings` | Ignored                                                               | Load                                    |

- Ship a credentialed local server as a standalone .mcpb, since Cowork never
  prompts for `${user_config.*}` values.
- Keep executables out of a top-level `bin/`. Put them under `scripts/` and
  call them as `${CLAUDE_PLUGIN_ROOT}/scripts/<name>`.
  https://claude.com/docs/plugins/org-sync#keep-executables-out-of-the-top-level-bin-directory **[V]**

### Variables in skill text

- Claude Code replaces `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PLUGIN_ROOT}`,
  `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_SESSION_ID}` and
  `$ARGUMENTS` in skill text when the skill loads. The two `PLUGIN` variables
  work only in plugin skills. It also replaces `${CLAUDE_SKILL_DIR}` and
  `${CLAUDE_PROJECT_DIR}` in Bash rules in `allowed-tools`, so a skill can run
  its own script with no prompt. They are placeholders, not environment
  variables: a Bash command never sees them.
  https://code.claude.com/docs/en/skills#available-string-substitutions,
  https://code.claude.com/docs/en/plugins/manifest-reference#where-each-variable-resolves
  **[V]**
- "Claude Code and Cowork replace `${CLAUDE_SKILL_DIR}` with the skill's
  folder when the skill loads." https://claude.com/docs/skills/how-to#add-scripts
  **[V]** A Cowork changelog fix for skills that ran "with those paths blank"
  names both `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}`, so Cowork
  substitutes both. https://claude.com/docs/cowork/changelog (v2.2553.0,
  2026-09-17) **[V/I]** The org-sync page tells authors to call bundled
  scripts as `${CLAUDE_PLUGIN_ROOT}/scripts/<name>` from skills, hooks and MCP
  configs.
  https://claude.com/docs/plugins/org-sync#keep-executables-out-of-the-top-level-bin-directory
  **[V]** `${CLAUDE_PLUGIN_DATA}` appears only in Claude Code's docs.
- Cowork replaces every `!` command line in a skill with a placeholder; local
  Claude Code runs them. A skill synced from claude.ai into a plain terminal
  session gets `${CLAUDE_PROJECT_DIR}` and `${CLAUDE_SESSION_ID}` as literal
  text, and its `!` lines do not run.
  https://code.claude.com/docs/en/skills#how-synced-skills-behave **[V]** So a
  skill for both surfaces gathers its context with ordinary tool calls.
- In claude.ai and Desktop chats, `${CLAUDE_SKILL_DIR}` reached Claude as
  literal text. **[V/I]**: test notes report it, but the run records were not
  rechecked. Those chats may have been Chat, where the docs predict no
  substitution, or Cowork, where they predict it. **[V, conflicting]**
- So write each path so it works either way: keep it readable relative to
  `SKILL.md`, such as `scripts/render.py`, and have the skill find its folder
  as below.

### Chat on plans that have not merged it

On plans that still keep Chat apart from Cowork, the same plugin also loads in
Chat. The merge reached Pro and Max first, with "more plans" to follow, so
Team and Enterprise are among them as of 2026-10-18.
https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude
**[V/I]** In Chat, from the platform-support page above **[V]**:

- Skills load. A command loads as a skill, which Claude applies when it fits.
- Agents, hooks and local MCP servers are ignored. A remote MCP server is
  ignored when its URL holds a `${user_config.*}` reference.
- The skill's whole folder, scripts included, is copied into the code sandbox,
  so a path relative to `SKILL.md` works there.
  https://claude.com/docs/skills/how-to#add-scripts **[V]**

Drop this section once those plans merge Chat into Cowork.

### Find the skill's own folder

The Skill tool prints the folder when it loads a skill:
`Base directory for this skill: <path>`. The path has moved:
`/mnt/skills/plugins/<plugin>:<skill>/` in web chats on 2026-10-14, and
`/mnt/skills/plugin-files/<plugin>/skills/<skill>` on claude.ai and Desktop on
2026-10-17. The printed folder was missing in a Desktop chat on 2026-10-11 and
in web chats on 2026-10-14. On 2026-10-17 and 2026-10-18 it existed and
held the skill's files on claude.ai, Desktop and Claude Code.
**[V, live 2026-10-11 to 2026-10-18]**

In Claude Code, `${CLAUDE_SKILL_DIR}` gives the folder **[V]**, and so did
that line **[V, live 2026-10-17 to 2026-10-18]**. The search below is for
Cowork, where neither is certain.

So have the skill read the path from that line, never build it. Then have
Claude try these in order, each as its own command, until one finds the files:

1. `ls "<base directory>"`, with the path the Skill tool printed.
2. `ls -dt ~/.claude/plugins/synced/*/<plugin>*/skills/<skill> 2>/dev/null | head -1`
3. `find` for a file the skill bundles, then the file-read tool.

Why each detail matters **[V, live 2026-10-17 to 2026-10-18]**:

- Step 1 runs alone. Joined to step 2, the glob reads outside the plugin's
  folder, so Claude Code stopped Claude's first call on an Allow prompt.
- The synced folder is named `<org id>_<user id>`, so the full path differs per
  account. Glob it.
- The organization sync keeps older copies of a plugin beside the current one,
  in folders with a `~gN` suffix; `manifest.json` lists them under `staleDirs`.
  `head -1` alone picked an old copy. `ls -dt` sorts newest first and picked
  the current copy, on one Mac. That it always does is **[I]**.
- In Claude Code, zsh aborts the whole command when a glob matches nothing.
  Separate commands let step 3 still run.

## Unified Claude and cloud sessions

- Chat and Cowork merge into one Claude, "starting with Pro and Max plans",
  with "more plans" to follow and no way back. Free is not mentioned.
  https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude **[V]**
- From 2026-10-06, new Pro and Max tasks run in the cloud. Local files, the
  browser, computer use and local connectors still work, but only through the
  open Desktop app.
  https://support.claude.com/en/articles/15520349-use-claude-cowork-on-web-desktop-and-mobile **[V]**
- Each cloud session gets a sandbox "created when the session starts and
  destroyed when it ends", sharing no state with other sandboxes.
  https://support.claude.com/en/articles/14479288-claude-cowork-architecture-overview **[V]**
- Every Claude Desktop chat in the live test ran in the cloud, linked to the
  Mac. **[V, live 2026-10-11]**
- Conflict: one page says "Local connectors and plugins that include local MCP
  servers work through the desktop app only"; the architecture page says
  "Local MCP servers don't run in sessions in the cloud". **[V, conflicting]**
  Whether a standalone .mcpb loads in a unified Pro or Max conversation is
  undocumented. claude.com calls a Desktop Extension a "local connector", which
  hints that it works through the open Desktop app.
  https://claude.com/docs/connectors/custom/add-unlisted **[I: test it]**
- In Claude Code, a plugin can declare an `.mcpb` in `mcpServers`, and the
  user sets its values in `/plugin`. The standalone CLI does not read Claude
  Desktop's extensions.
  https://code.claude.com/docs/en/plugins/components#include-a-packaged-mcpb-server,
  https://code.claude.com/docs/en/desktop **[V]**
