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
- **[V, live <date>]** observed in our own live test on that date or date
  range. The 2026-10-11 test used Claude Desktop 2.31226.1 on a personal Pro
  account. Tests from 2026-10-14 to 2026-10-18 used claude.ai web chats,
  Claude Desktop and Claude Code on an organization account on the Team plan,
  with Sonnet 5.5. The test notes are
  private.
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
   web, mobile). Ask when unknown. Free gets no plugins and no browser tools,
   and likely no Cowork **[I]**, so a Free design differs from the rest.
2. **Pick the packaging.** Read [packaging.md](references/packaging.md): plugin,
   Agent Skill, Desktop Extension, custom connector or project. It also says
   which plugin parts load in Chat, Cowork and cloud sessions, and how a skill
   finds the scripts it bundles.
3. **Pick the route out.** For anything that reads a website, runs code or
   holds a credential, read [reach.md](references/reach.md). The short answer:
   on Free, Pro and Max, sandbox code reaches only a fixed list of package
   hosts, so browsers and MCP servers are the routes to other sites. Team and
   Enterprise owners can add domains to that list.
4. **Pick where state lives.** For anything that must remember a result
   between chats, carry progress through one long run, or hand the user a
   file, read [state.md](references/state.md).
5. **Budget the work.** For anything that browses, fetches or runs on a
   schedule, read [usage.md](references/usage.md). Context windows are rarely
   the limit; the plan's opaque usage meter is.
6. **List the live tests.** Collect every claim the design depends on that is
   marked **[I]** in any form, **[V/I]** or **[V, conflicting]**. Write each as
   a prompt the user pastes into a fresh chat, with a "Pass if" line. Ask the
   user to record the surface (Desktop, web chat or Claude Code), the browser,
   and their Claude Desktop version (Claude > About), because a transcript
   does not show which app ran. Write each test with these rules
   **[V, live 2026-10-16 to 2026-10-18]**:
   - **Base "Pass if" on what the page computed.** Claude misreports what it
     read. Given a result cut at 1,000 characters, it reported the length the
     script meant to return. Given a cut page read, it quoted the total from
     the truncation note. Once, it retyped a 4,000-character script with an
     edit, though a later run of 21 sends kept it intact. So have the page
     script measure its own input, or hash its own source and return
     `stopped` on a mismatch, and check that value.
   - **Time Desktop tests from the chat's timestamps,** or tell the user to
     answer every card and prompt at once. On Desktop, a prompt waiting on
     the user looks the same as Claude working. One timed run sat 8 minutes
     on an unclicked prompt.
   - **Keep each prompt short enough to paste as a message.** A long prompt
     pasted into Desktop becomes an attachment.

   The step is done when every such dependency has a test or the user has
   accepted the risk.

## Defaults

| Need                                | Default on Pro or Max                                                                                                                                                  |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Teach Claude a procedure            | A plugin that holds only a skill, from a Git marketplace with **Sync automatically**                                                                                   |
| Read a site the user signs in to    | The skill tells Claude to use the browser it has, and the user signs in when asked. The built-in browser needs Claude Desktop open; Claude in Chrome needs only Chrome |
| Pull JSON from a signed-in site     | `javascript_tool` runs `fetch` in the page and trims the result there, under 1,000 characters for Claude in Chrome                                                     |
| Keep a record between chats         | A file in a local folder project; Desktop only, and Desktop must be open                                                                                               |
| Run code that needs a stored secret | A standalone Desktop Extension with `sensitive` `user_config` **[I]**                                                                                                  |
| Anything on Free                    | A Desktop Extension **[I]**, or one custom connector                                                                                                                   |

The **[I]** cells rest on untested claims: whether a standalone .mcpb loads in a
unified Pro or Max chat, and whether .mcpb works on Free. Cover them in the
step 6 tests before a design depends on them.

## Questions the skill asks

Claude asks the user through question cards. A card is a prompt, not a gate.
Write each asking step with these rules **[V, live 2026-10-15 to 2026-10-18]**:

- **State the constraints in the step that asks.** Claude builds the options
  from that text. Without it, Claude once marked as (Recommended) an option
  the skill could not carry out, then took it back in its next turn.
- **Ask for exactly one (Recommended) option** on each question, when the
  skill or a test relies on a default. Without that, Claude marked none in
  one run.
- **Say what `[No preference]` means.** A skipped card reaches Claude as
  `[No preference]`. The skill says whether that means stop or go on with the
  default. For a destructive or long step, that rule is the gate.
- **Leave Claude free to ask** when a tool requires a question, as Claude in
  Chrome does when two Chromes are connected (see
  [reach.md](references/reach.md)).

With the first two rules in place, a test that stops Claude after its
questions passed on claude.ai with either browser, on Desktop with the
built-in browser, and on Claude Code with agent-browser. It failed on Claude
Code and claude.ai before them.
