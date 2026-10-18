# Keeping state and handing over files

Researched 2026-10-11, with live findings to 2026-10-18 and doc claims rechecked 2026-10-18. Marks are defined in [SKILL.md](../SKILL.md#freshness).

Default in Cowork: a file in a local folder project. Fallback: Claude's
memory. Last resort: past-chat search. In Claude Code, the default is a file
under `${CLAUDE_PLUGIN_DATA}`, so a plugin for both picks its store per
surface.

| Store                         | Persists across chats?                        | Exact text?                 | Where the data sits                                                                  | Notes                                                              |
| ----------------------------- | --------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| **Local folder project**      | Yes, in chats started in that project **[V]** | Yes                         | The user's computer; content Claude reads passes through Anthropic's servers **[V]** | Desktop only, and Desktop must be open **[V]**                     |
| **Claude memory**             | Yes **[V]**                                   | No; Claude words it **[I]** | Anthropic servers; visible in Settings > Memory **[V]**                              | On by default for Free, Pro, Max; the user can turn it off **[V]** |
| **Past-chat search**          | Yes, paid plans **[V]**                       | Retrieval is fuzzy **[I]**  | The user's chat history **[V]**                                                      | Needs no extra step; deleting a chat loses it                      |
| **Claude Docs**               | Yes **[V]**                                   | Yes                         | The user's Claude account; private unless shared **[V]**                             | A new chat cannot find a doc by name without its link **[I]**      |
| claude.ai project knowledge   | Read-only to Claude **[V]**                   | n/a                         | Anthropic servers                                                                    | Ruled out                                                          |
| Cowork outputs, session files | One session only **[V/I]**                    | n/a                         | n/a                                                                                  | Ruled out; cloud sandboxes are destroyed at session end            |
| Plugin data directory         | In Claude Code only **[V]**                   | Yes                         | `~/.claude/plugins/data/<id>/` on the user's computer **[V]**                        | Kept across updates, deleted on uninstall **[V]**                  |
| The skill's own folder        | No; copied fresh into each sandbox **[V]**    | n/a                         | n/a                                                                                  | Ruled out                                                          |
| Artifact storage              | Per artifact **[V]**                          | Yes                         | Anthropic servers; 20 MB, text only **[V]**                                          | Only the artifact's own page code reads it **[I]**                 |
| Device folder (`device_*`)    | The folder is on the Mac **[I]**              | Yes                         | A Mac folder the user grants, mounted in a Linux VM **[V, live 2026-10-17]**         | Observed, not documented; often missing. See below                 |

Sources for table claims not cited further down:
memory on by default, https://support.claude.com/en/articles/11817273;
Claude Docs, https://support.claude.com/en/articles/16923645-get-started-with-claude-docs;
artifact storage, https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them **[V]**;
plugin data directory, https://code.claude.com/docs/en/plugins/manifest-reference#environment-variables **[V]**

## Within one run

- `sessionStorage` holds a run's progress across page scripts. A page script
  wrote to it, then the run navigated, reloaded, went to another site and came
  back, and passed through a sign-in redirect. The value survived all of it,
  with either browser, in web and Desktop chats. Variables on `window` did not
  survive a navigation. **[V, live 2026-10-17]**
- Each site has its own `sessionStorage`. Its size limit, about 5 MB in
  browsers generally, was not tested. **[I]**
- So a skill that drives a long job through many page scripts can keep its
  progress there and resume after a timeout or a page change. The state never
  passes through Claude. The long-work steps in [reach.md](reach.md) use it to
  guard against a double start.

## Handing the user a file

A page script that builds a `.csv` or `.xlsx` and clicks a download link put
the file in `~/Downloads`, with either browser, in web and Desktop chats. The
test built the `.xlsx` with SheetJS 0.18.5 loaded from jsDelivr.
**[V, live 2026-10-17]** Confirming the download differs by browser:

- **Built-in browser.** macOS shows a save dialog for every download. Until
  the user clicks Save, the file is a hidden temporary file named
  `.<random>.com.anthropic.claudefordesktop.*`. Claude looked too early and
  reported the file missing. Have the skill tell the user to click Save, and
  Claude to check only after they say so.
- **Claude in Chrome.** No dialog appears. Claude cannot see
  `chrome://downloads` or `file://`, so it can confirm the file only through
  the device tools below. In Claude Code, Claude can list `~/Downloads` with
  Bash instead. **[I]**

## Device folders from a web chat

A claude.ai web chat linked to the Mac through Devices offered
`get_device_info`, `device_request_folder_access`, `device_bash` and
`device_list_dir`. No doc lists them. **[V, live 2026-10-17]**

- `device_request_folder_access({paths: ["~/Downloads"]})` asks the user. The
  folder then mounts at `$HOME/mnt/Downloads` in a Linux VM, not on the Mac
  itself.
- Without a granted folder, `device_bash` fails with "No folders are connected
  to this device…".
- Tool search found these tools in only one of three Claude in Chrome runs. A
  design can use them when they appear, but cannot depend on them. Public bug
  reports describe sessions that start without them.
  https://github.com/anthropics/claude-code/issues/94819 **[V, user report]**

## Local folder project

- A user gives Claude a folder on their computer, listed under Settings >
  Trusted folders. Picking it authorizes read and write.
  https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude,
  https://academy.claude.com/courses/introduction-to-claude-cowork/getting-set-up **[V]**
- A project made from an existing folder stays on that computer and mounts the
  folder in every new session it starts. Files Claude creates land there.
  https://support.claude.com/en/articles/14116274-organize-your-tasks-with-projects-in-claude-cowork,
  https://claude.com/docs/cowork/guide/projects **[V]**
- A cloud session reads and writes the folder only while Desktop is open on
  that computer, and only if the session started on Desktop or is a scheduled
  task. https://support.claude.com/en/articles/15520349-use-claude-cowork-on-web-desktop-and-mobile **[V]**
- Claude reads files up to 50 MB.
  https://claude.com/docs/cowork/guide/projects **[V]**
- A skill cannot attach a folder itself, so the design needs a one-time step
  where the user creates the folder project. If no folder is attached, the
  skill says so and offers the fallback.
- Manual mode ("Claude asks before it takes actions") may ask before each
  write; Auto mode does not. Deleting files always asks. Live, Claude wrote a
  file to a folder project in Manual mode with no prompt. That is one write in
  one chat. **[V, live 2026-10-11]**
- Safety guidance suggests a dedicated working folder for Claude.
  https://support.claude.com/en/articles/13364135-use-claude-cowork-safely **[V]**

## Claude memory

- "Memory is shared between Chat and Claude Cowork when Cowork runs in the
  cloud; Cowork sessions that run locally on your computer don't use memory."
  Each project has its own memory space. A "remember this" request saves
  directly and applies from the next conversation.
  https://support.claude.com/en/articles/11817273 **[V]**
- Memory is stored as topics Claude writes in its own words, so exact numbers
  may be merged or shortened. **[I]**
- Health, race and religion are skipped by default. Government IDs, criminal
  history, financial account numbers and immigration status are never saved.
  **[V]** No size limit is stated. **[V: absence]**
- No doc says a skill may write memory, and none forbids it. **[I]**
- Claude Code's memory is separate: auto memory is files on the user's
  computer, "not shared across machines or cloud environments".
  https://code.claude.com/docs/en/memory **[V]** Its docs never mention
  claude.ai memory, so a skill cannot count on that memory in Claude Code.
  **[I]**

## Past-chat search

Paid plans only, RAG-based, shown as a tool call. Inside a project it searches
that project's chats; outside, all chats outside projects. It does not cover
pre-merge Cowork tasks. https://support.claude.com/en/articles/11817273,
https://support.claude.com/en/articles/16761823 **[V]**

## Artifacts in Claude Desktop

Asked for a report "as an artifact", Claude wrote an HTML file in its sandbox
and opened it in a file viewer beside the chat. It did not appear in the
Artifacts list. The viewer's "More options" menu has "Publish artifact",
"Add to project" and "Download as HTML", so publishing a page with personal
data is one click away for the user. **[V, live 2026-10-11]**

## Watch list

A projects Library that "collects the files you add and the files Claude
produces" was rolling out to Claude Code first, with Chat and Cowork to
follow. It could replace the folder project as the default.
https://support.claude.com/en/articles/9517075-what-are-projects **[V]**
