# Keeping state between chats

Researched 2026-10-11. Marks are defined in [SKILL.md](../SKILL.md#freshness).

Default: a file in a local folder project. Fallback: Claude's memory. Last
resort: past-chat search.

| Store                         | Persists across chats?                        | Exact text?                 | Where the data sits                                                                  | Notes                                                              |
| ----------------------------- | --------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| **Local folder project**      | Yes, in chats started in that project **[V]** | Yes                         | The user's computer; content Claude reads passes through Anthropic's servers **[V]** | Desktop only, and Desktop must be open **[V]**                     |
| **Claude memory**             | Yes **[V]**                                   | No; Claude words it **[I]** | Anthropic servers; visible in Settings > Memory **[V]**                              | On by default for Free, Pro, Max; the user can turn it off **[V]** |
| **Past-chat search**          | Yes, paid plans **[V]**                       | Retrieval is fuzzy **[I]**  | The user's chat history **[V]**                                                      | Needs no extra step; deleting a chat loses it                      |
| **Claude Docs**               | Yes **[V]**                                   | Yes                         | The user's Claude account; private unless shared **[V]**                             | A new chat cannot find a doc by name without its link **[I]**      |
| claude.ai project knowledge   | Read-only to Claude **[V]**                   | n/a                         | Anthropic servers                                                                    | Ruled out                                                          |
| Cowork outputs, session files | One session only **[V/I]**                    | n/a                         | n/a                                                                                  | Ruled out; cloud sandboxes are destroyed at session end            |
| Plugin data directory         | Claude Code only **[V]**                      | n/a                         | n/a                                                                                  | Ruled out                                                          |
| The skill's own folder        | No; copied fresh into each sandbox **[V]**    | n/a                         | n/a                                                                                  | Ruled out                                                          |
| Artifact storage              | Per artifact **[V]**                          | Yes                         | Anthropic servers; 20 MB, text only **[V]**                                          | Only the artifact's own page code reads it **[I]**                 |

Sources for table claims not cited further down:
memory on by default, https://support.claude.com/en/articles/11817273;
Claude Docs, https://support.claude.com/en/articles/16923645-get-started-with-claude-docs;
artifact storage, https://support.claude.com/en/articles/9487310 **[V]**

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
  one chat. **[V, live]**
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
data is one click away for the user. **[V, live]**

## Watch list

A projects Library that "collects the files you add and the files Claude
produces" was rolling out to Claude Code first, with Chat and Cowork to
follow. It could replace the folder project as the default.
https://support.claude.com/en/articles/9517075-what-are-projects **[V]**
