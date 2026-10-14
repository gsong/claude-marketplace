---
name: build
description: >
  Build for Claude Desktop and claude.ai (Chat and Cowork): plugins, Agent
  Skills, Desktop Extensions (.mcpb) and custom connectors. Use when designing
  or packaging something a claude.ai user runs, or when deciding whether it can
  browse a signed-in site, run code, reach the network, keep state between
  chats, or fit a plan's usage limits.
---

# Build for Claude Desktop and claude.ai

Claude Desktop and claude.ai run the same Claude for an end user. The user's
plan decides most of the architecture: what can be installed, which browser
tools exist, and where code can run. Claude Code is a different product with
different rules; its docs do not answer these questions.

## Freshness

These facts were researched in October 2026 and change monthly. Each claim
carries a mark:

- **[V]** verified on a primary source, with the URL or source given. A
  qualifier narrows it: **[V, measured]** and **[V on two sites]** are our own
  measurements, **[V, user report]** is a public bug report, and
  **[V: absence]** means no source states the thing.
- **[V, live]** observed in a live test on Claude Desktop 2.31226.1 with a
  personal Pro account, 2026-10-11. The test notes are private.
- **[I]** inference or unverified. Test it before a design depends on it.
  **[I, strong]**, **[I: test it]** and other qualified **[I]** marks are still
  inferences.
- **[V/I]** partly verified, and **[V, conflicting]** where two primary sources
  disagree. Treat both as **[I]**.

Before a decision rests on a claim, fetch its URL again. When the page
disagrees with the reference, trust the page for this decision. Do not edit
the reference file: an installed plugin is a synced copy, so the edit is lost.
Tell the user which claim is stale, with the URL and today's date, and suggest
they open an issue on gsong/claude-marketplace.

## Design steps

1. **Pin the plan and the surface.** Learn the user's plan (Free, Pro, Max,
   Team, Enterprise) and where they run Claude (Desktop on macOS or Windows,
   web, mobile). Ask when unknown. Free gets no plugins, no Cowork and no
   browser tools, so a Free design differs from the rest.
2. **Pick the packaging.** Read [packaging.md](references/packaging.md): plugin,
   Agent Skill, Desktop Extension, custom connector or project. It also says
   which plugin parts load in Chat, Cowork and cloud sessions.
3. **Pick the route out.** For anything that reads a website, runs code or
   holds a credential, read [reach.md](references/reach.md). The short answer:
   sandbox code reaches package registries only, so browsers and MCP servers
   are the routes to other sites.
4. **Pick where state lives.** For anything that must remember a result
   between chats, read [state.md](references/state.md).
5. **Budget the work.** For anything that browses, fetches or runs on a
   schedule, read [usage.md](references/usage.md). Context windows are rarely
   the limit; the plan's opaque usage meter is.
6. **List the live tests.** Collect every claim the design depends on that is
   marked **[I]** in any form, **[V/I]** or **[V, conflicting]**. Write each as
   a prompt the user pastes into a fresh chat, with a "Pass if" line, and ask
   them to record their Claude Desktop version (Claude > About). The step is
   done when every such dependency has a test or the user has accepted the
   risk.

## Defaults

| Need                                | Default on Pro or Max                                                                                       |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Teach Claude a procedure            | A plugin that holds only a skill, from a Git marketplace with **Sync automatically**                        |
| Read a site the user signs in to    | Run from Claude Desktop; the skill tells Claude to use the browser it has, and the user signs in when asked |
| Pull JSON from a signed-in site     | `javascript_tool` runs `fetch` in the page and trims the result there                                       |
| Keep a record between chats         | A file in a local folder project                                                                            |
| Run code that needs a stored secret | A standalone Desktop Extension with `sensitive` `user_config`                                               |
| Anything on Free                    | A Desktop Extension, or one custom connector                                                                |
