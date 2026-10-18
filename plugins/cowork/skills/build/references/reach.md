# Reaching websites, running code, holding credentials

Researched 2026-10-11, with live findings to 2026-10-18. Marks are defined in [SKILL.md](../SKILL.md#freshness).

## Code sandbox egress

Sandbox code cannot log in to an arbitrary site on a personal plan.

- On Free, Pro and Max, the sandbox reaches only approved package sources:
  api.anthropic.com, github.com, registry.npmjs.org, pypi.org, crates.io,
  archive.ubuntu.com and registry.yarnpkg.com. Custom domains and "All domains"
  are documented only for Team and Enterprise owners.
  https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude **[V]**
  That individuals get no allowlist control is inferred from the article's
  silence. **[I, strong]**
- Cowork cloud sandboxes send all traffic through a proxy they cannot bypass.
  https://support.claude.com/en/articles/14479288-claude-cowork-architecture-overview **[V]**
- Egress settings "don't apply to web fetch, web search, or MCPs, including
  Claude in Chrome."
  https://support.claude.com/en/articles/13345190-get-started-with-cowork **[V]**
  So browsers and MCP servers are the routes out. Web fetch carries no login
  cookies. **[I]**
- Users report custom-domain allowlists failing even on plans that have them:
  https://github.com/anthropics/claude-code/issues/51400 **[V, user report]**
- Live, a `curl` from the sandbox to a site off the list returned
  `CONNECT tunnel failed, response 403`, in both a web chat and a Desktop
  chat. The sandbox had Python 3.13, Node 22, Bun 1.4 and uv 0.11.
  **[V, live 2026-10-11]**

## Routes to a signed-in site

| Route                                  | Plans                                                                                     | Notes                                                                                                                                                                                                                                                                                     |
| -------------------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Built-in browser** (pane in Desktop) | Pro, Max, Team; Enterprise when an Owner enables it; rolling out since 2026-08-26 **[V]** | Separate from the user's own browser. The user signs in, or imports logins site by site from Chrome, Edge or Firefox on macOS. "Claude remembers logins across Cowork sessions." Desktop must be open and online. It is the default when Claude in Chrome is not set up.                  |
| **Claude in Chrome** (extension)       | All paid plans **[V]**                                                                    | Uses the user's real Google Chrome and its sign-ins. A Desktop chat drives it once Settings > Connectors > Claude in Chrome is on, toggled per chat; live, Desktop still chose the built-in browser (see below). A 1Password integration (beta, macOS) fills passwords Claude never sees. |
| **Computer use**                       | Pro, Max; research preview; macOS 14+ and Windows **[V]**                                 | Settings > General > Computer use. Claude tries connectors, then the browser, then the screen.                                                                                                                                                                                            |
| **Local MCP server** (.mcpb)           | Any plan with Desktop **[I]**                                                             | Full control, but you ship code, store passwords and fix it whenever the site changes.                                                                                                                                                                                                    |
| **Remote connector**                   | Free (one), paid plans **[V]**                                                            | A public server holds the user's credentials. Works on mobile, at a real security and hosting cost.                                                                                                                                                                                       |

Sources: https://support.claude.com/en/articles/16607400-use-the-built-in-browser-in-claude-cowork,
https://support.claude.com/en/articles/12012173-claude-in-chrome,
https://support.claude.com/en/articles/14128542-let-claude-use-your-computer-in-cowork. The
preferred browser is set at Settings > Cowork > Preferred browser. **[V]**

### Which browser a chat gets

- **Desktop chat.** It used the built-in browser in two runs with Claude in
  Chrome turned on, even when told "Use Claude in Chrome, not the built-in
  browser". A skill cannot count on picking the browser from Desktop.
  **[V, live 2026-10-16 to 2026-10-18]**
- **Web chat, built-in browser.** It works while Claude Desktop runs on the
  same Mac. The chat shows the Mac as a connected device, and the tools carry
  `Claude_Browser` in their names. With Desktop quit, the device shows "Asleep
  or app closed", and the chat falls back to Claude in Chrome.
  **[V, live 2026-10-15]** On 2026-10-11 a web chat got only an
  `enable__mcp__remote-devices__Claude_Browser` stub that loaded no tools.
  **[V, live 2026-10-11]**
- **Web chat, Claude in Chrome.** It needs Chrome with the extension, not
  Desktop. The connector sits under "+" > Connectors > Claude in Chrome. It is
  on by default and needs no Devices link. **[V, live 2026-10-16]** In earlier
  runs its first call asked for "the Claude desktop app and the Claude in
  Chrome extension" instead. **[V, live 2026-10-11 to 2026-10-15]** What
  brings up that prompt is untested. **[I]**
- **Claude in Chrome's side panel.** It is a third surface. It loads
  `claude.ai/cic/new?surface=cic_sidepanel`, titled "Claude Cowork". It asked
  for approval before every browser step, so opening and reading one page took
  eight prompts. Run multi-step skills from a chat tab.
  **[V, live 2026-10-16]**

### The built-in browser pane

Observed **[V, live 2026-10-11]**:

- The pane did not offer to save a password after a manual sign-in.
- After quitting and reopening Claude Desktop, both test sites were signed
  out.
- The pane shows one page at a time. Asking for two sign-ins in one message
  failed, because only the site left in the pane could be signed in to. Ask
  for one site at a time, with that site's login page showing.

Safety: Claude asks before acting on a site the first time, and some high-risk
sites are blocked; the categories are not listed.
https://support.claude.com/en/articles/13364135-use-claude-cowork-safely **[V]**

**A skill can direct either browser.** The browser tools are ordinary tools in
the same session, and skills load where those tools live. No doc says so
outright. **[I]** Write the skill browser-agnostic ("use the browser available
to you"), because the user's surface, not the skill, decides which browser
Claude gets.

## Browser tools in detail

Source: the Claude Desktop app bundle, version 2.31226.1 built 2026-10-09,
read statically. No public doc lists these tools. **[V for that build; I for
other builds and rollouts]** A live test on the same build confirmed the tool
names, deferred loading, site approval and `javascript_tool` behaviour below.
**[V, live 2026-10-11]**

- **Tool names.** `read_page`, `computer`, `form_input`, `navigate`, `find`,
  `get_page_text`, `javascript_tool`, `read_console_messages`,
  `read_network_requests`, `resize_window`, `tabs_context`, `tabs_create`,
  `tabs_select`, `tabs_close`, `browser_batch`, `preview_start`,
  `request_access`. Prefixes differ by host:
  `mcp__Claude_Browser__`, `mcp__remote-devices__Claude_Browser__` (cloud
  session linked to the Mac), `mcp__claude-in-chrome__`.
- **Reading a transcript.** The tool prefix tells which browser ran, but
  nothing tells which app ran. A Desktop chat and a web chat linked through
  Devices both use `mcp__remote-devices__`, and `platform` read `CLAUDE_AI` in
  every chat tested. A share link drops tool results, thinking timestamps and
  `platform`. **[V, live 2026-10-16]**
- **Deferred loading.** In a Desktop chat the browser tools start deferred.
  Only `enable__mcp__remote-devices__Claude_Browser` is listed until Claude
  calls it and a tool search loads the rest. Have the skill load the tools
  before it uses them.
- **Site approval.** The dialog offers "once" or "always". "Once" asks again
  on the next page load. "Always" held across fresh chats, granted "on this
  computer, until the person removes it in Settings". Have the skill tell the
  user to choose "always".
  - In a web chat, the built-in browser refused a site it had not been
    granted. The error said "The person hasn't allowed the browser pane to use
    <url> yet" and told Claude to call `Claude_Browser__request_access`, with
    scope "once" or "site". A Desktop chat on the same build opened the same
    site without asking.
    **[V, live 2026-10-16 to 2026-10-18]**
  - Claude in Chrome offers "Always allow for <host>" when it opens a site,
    but only "Allow once" when it creates its browser window, in every chat.
    **[V, live 2026-10-16]**
- **`javascript_tool`** runs code in the page's main world through CDP
  `Runtime.evaluate`, with REPL semantics: the last expression is returned as
  JSON. A same-origin `fetch` therefore sends the page's cookies, so it can
  call the site's own JSON endpoints, GET or POST. Timeout 45 s. It is paused
  while a page-opened popup (often a sign-in window) is open. It passes the
  same per-site approval as other page tools. Claude in Chrome has the same
  tool, plus a `tabId`.
- **Live, `javascript_tool`** returned JSON from a same-origin `fetch` under a
  real login, and ran a `.js` file bundled in the skill unchanged. A top-level
  `const` survives between calls in the same page, so wrap each script in a
  function to avoid a redeclaration error. Make it a synchronous function
  when the script must return a value; see the async forms below.
- **Result size.** Claude in Chrome cuts a `javascript_tool` result at about
  1,000 characters and ends it with `[TRUNCATED]`. A result that looks like
  cookie or query-string data comes back as only
  `[BLOCKED: Cookie/query string data]`. The built-in browser and
  agent-browser returned 25,000 characters whole; their ceiling is unmeasured.
  **[V, live 2026-10-16 to 2026-10-18]** On Claude in Chrome, moving 15,000
  characters out through script results took 17 reads, about 3.5 minutes. So
  keep each result short. To move bulk data, have the script write it into
  the page body, then read it with `get_page_text`.
- **Async forms.** No async form returns a value in every browser
  **[V, live 2026-10-16 to 2026-10-18]**:
  - `(async () => { … })()` returns `{}` at once on Claude in Chrome. The work
    keeps running in the page, but its value never comes back.
  - Top-level `await` works on Claude in Chrome and the built-in browser.
    agent-browser, in Claude Code, rejects it with `await is not defined`.
  - A synchronous script returns its value everywhere.
- **Long work.** A timed-out script keeps running; only its return value is
  lost. A 60-second task finished at about 60 s with either browser, in web
  and Desktop chats. Claude in Chrome's error reads
  `CDP sendCommand "Runtime.evaluate" timed out after 45000ms`, and the
  built-in browser's says the script "may still be running". So a retry after
  a timeout can start the work twice. **[V, live 2026-10-16 to 2026-10-18]**
  For work that may pass 45 s, have the skill tell Claude to:
  1. Start the work in the background from a synchronous script that returns
     a short status. Guard the start with a flag in `sessionStorage`, so a
     retry does not start it again.
  2. Wait in the code sandbox with `sleep 20`, one wait at a time. The page
     kept working through each sleep. On Desktop, Claude ran five `sleep 30`
     calls in parallel, so all five ended together, until the prompt said
     "one at a time".
  3. Poll for the result with another short synchronous script.
- **Trim inside the page.** Have the script reduce the response to the fields
  you need before it returns. A raw record runs 18 to 40 times larger than its
  trimmed form, and a whole task about 90 times (see [usage.md](usage.md)).
  Small returns also keep personal data out of the transcript.
- **`navigate`** puts `https://` in front of anything without `http(s)://`, so
  a `javascript:` URL never runs.
- **Claude in Chrome's first call after `navigate`** can fail with
  `Can't interact with browser-internal or unparseable URLs. Navigate to a web page first.`,
  because the tab is still `chrome://newtab/`. A retry passed, so have the
  skill retry once. `get_page_text` gives the same error on a `blob:` page.
  In the built-in browser, navigating to a `blob:` URL left the tab where it
  was. **[V, live 2026-10-16 to 2026-10-18]**
- **`get_page_text`** returns the `innerText` of the longest `article`,
  `main`, `[role="main"]` or `#content`, else `body`. A GET to a JSON URL
  probably shows the raw JSON this way. **[I]**
  - Claude in Chrome cuts it at 50,000 characters by default, with a note:
    `[output truncated at 50000 of 104231 characters. Pass a larger max_chars (default 50000)…]`.
    `max_chars: 200000` returned 118,000 characters whole. Claude passed
    `max_chars` only when the prompt named the parameter outright; "pass a
    larger limit if it takes one" was ignored. So name `max_chars` in the
    skill. The text starts with `Title:`, `URL:` and `Source element:` lines.
    **[V, live 2026-10-16 to 2026-10-18]**
- **`read_network_requests`** in the built-in browser returns a response body
  when given a `requestId`, but only for the tab's own origin, cut at 10,000
  characters. It never records request bodies. Claude in Chrome's copy has no
  body option in that build. **[I that bodies are unavailable there]** Live, a
  body of about 8,400 characters came back whole, but the listing said 151
  earlier requests had been dropped from the tab's buffer. Read a body soon
  after the page loads.
- **Check the tool exists.** Anthropic's own built-in-browser skill omits
  `javascript_tool`, so treat it as undocumented. A skill that relies on it
  should name a fallback, such as reading pages as text.

Live test for the tool list, pasted into a fresh Desktop chat:
`List the exact names of every browser tool you have. Do not call any of them.`
Pass if `javascript_tool` is listed.

## Signed-out pages

A skill that reads a signed-in site must detect the signed-out state before it
reads anything, or the model reads a login form as data.

- Check `document.title` or the final URL in the first script, and return a
  short marker such as `signed out: <site>`.
- For JSON routes, check `response.redirected` and `content-type` before
  `JSON.parse`. Many sites answer a signed-out JSON call with HTTP 200 and an
  HTML login page, so the status code alone misleads. **[V on two sites]**
- That check misses a sign-in on another origin, such as Auth0. The browser
  blocks the cross-origin redirect, so `fetch` throws
  `TypeError: Failed to fetch`, the same error as a network blip. **[I]** A
  blip was seen live: 8 fetches failed, then loaded again seconds later, with
  no sign-in. **[V, live 2026-10-16 to 2026-10-18]** So a page script cannot
  tell a sign-out from an outage. Have it retry each failed item once. After
  several failures in a row, have it stop and hand back to Claude, which
  checks the sign-in before going on.
- A page that shows neither the login title nor the expected signed-in title is
  a site change or an outage. Report it and stop, rather than signing in again.
- Expect sign-ins often. One test site signed out after about 10 minutes
  idle, and both test sites were signed out after Claude Desktop quit.
  **[V, live 2026-10-11]**

## Credentials

- Desktop Extension `user_config` fields marked `"sensitive": true` are
  encrypted in the OS secure store (Keychain, Credential Manager, keyring).
  https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop **[V]**
  Values reach the server as `${user_config.KEY}` in `env` or `args`; prefer
  `env` for secrets. https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md **[V]**
- Keep `${user_config.*}` out of a plugin's MCP config; Cowork skips such
  servers (see [packaging.md](packaging.md)).
- Remote connectors prefer OAuth. API-key request headers are beta, limited to
  some organizations, and stored server-side.
  https://claude.com/docs/connectors/custom/add-unlisted **[V]**
- Browser routes need no stored secret: the user types the password into the
  browser, again after each app quit or site timeout.
