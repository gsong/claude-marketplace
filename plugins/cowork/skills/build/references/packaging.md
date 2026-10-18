# Packaging and where each part runs

Researched 2026-10-11, with live findings to 2026-10-18. Marks are defined in [SKILL.md](../SKILL.md#freshness).

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
  **[V, live 2026-10-11]**
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

- Skills and remote MCP servers load in Chat and Cowork.
- Agents and hooks load in Cowork and Claude Code only.
- A local MCP server, including a `.mcpb` bundle, is ignored in Chat. It loads
  only when the Cowork session runs on the user's computer.
- Cowork skips an MCP server whose config uses `${user_config.*}`, because
  Cowork never prompts for values. Ship a credentialed local server as a
  standalone .mcpb instead.
- A top-level `bin/` directory makes Chat and Cowork refuse the plugin.
- In Chat on claude.ai, the skill's whole folder, scripts included, is copied
  into the code sandbox. Only `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PLUGIN_ROOT}`
  are documented for Cowork; `${CLAUDE_PLUGIN_DATA}` is Claude Code only.
  https://claude.com/docs/skills/how-to **[V]**
- Documented is not the same as expanded. In claude.ai and Desktop chats,
  `${CLAUDE_SKILL_DIR}` reached Claude as literal text; Claude Code substitutes
  it. **[V/I]**: probe notes report it, but the run records were not
  rechecked. `${CLAUDE_PLUGIN_ROOT}` probably
  stays literal too, and neither was tested in Cowork. **[I]**

### Find the skill's own folder

The Skill tool prints the folder when it loads a skill:
`Base directory for this skill: <path>`. The path has moved:
`/mnt/skills/plugins/<plugin>:<skill>/` in web chats on 2026-10-14, and
`/mnt/skills/plugin-files/<plugin>/skills/<skill>` on claude.ai and Desktop on
2026-10-17. The printed folder was missing in a Desktop chat on 2026-10-11 and
in web chats on 2026-10-14. On 2026-10-17 and 2026-10-18 it existed and
held the skill's files on claude.ai, Desktop and Claude Code.
**[V, live 2026-10-11 to 2026-10-18]**

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

- From 2026-09-16, Chat and Cowork merge into one Claude for Pro and Max, in a
  staged rollout with no way back. Free is not mentioned.
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
- Conflict: one page says plugin local MCP servers "work through the desktop
  app only"; the architecture page says they "don't run in cloud sessions".
  **[V, conflicting]** Whether a standalone .mcpb loads in a unified Pro or Max
  conversation is undocumented. **[I: test it]**
