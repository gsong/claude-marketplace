# Reaching websites, running code, holding credentials

Researched 2026-10-11. Marks: **[V]** verified, **[I]** inference.

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

## Routes to a signed-in site

| Route                                  | Plans                                                                                     | Notes                                                                                                                                                                                                                                                                         |
| -------------------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Built-in browser** (pane in Desktop) | Pro, Max, Team; Enterprise when an Owner enables it; rolling out since 2026-08-26 **[V]** | Separate from the user's own browser. The user signs in once, or imports logins site by site from Chrome, Edge or Firefox on macOS. "Claude remembers logins across Cowork sessions." Desktop must be open and online. It is the default when Claude in Chrome is not set up. |
| **Claude in Chrome** (extension)       | All paid plans **[V]**                                                                    | Uses the user's real Google Chrome and its sign-ins. A Desktop chat drives it once Settings > Connectors > Claude in Chrome is on, toggled per chat. A 1Password integration (beta, macOS) fills passwords Claude never sees.                                                 |
| **Computer use**                       | Pro, Max; research preview; macOS 14+ and Windows **[V]**                                 | Settings > General > Computer use. Claude tries connectors, then the browser, then the screen.                                                                                                                                                                                |
| **Local MCP server** (.mcpb)           | Any plan with Desktop **[I]**                                                             | Full control, but you ship code, store passwords and fix it whenever the site changes.                                                                                                                                                                                        |
| **Remote connector**                   | Free (one), paid plans **[V]**                                                            | A public server holds the user's credentials. Works on mobile, at a real security and hosting cost.                                                                                                                                                                           |

Sources: https://support.claude.com/en/articles/16607400-use-the-built-in-browser-in-claude-cowork,
https://support.claude.com/en/articles/12012173-claude-in-chrome,
https://support.claude.com/en/articles/14128542-let-claude-use-your-computer-in-cowork. The
preferred browser is set at Settings > Cowork > Preferred browser. **[V]**

Safety: Claude asks before acting on a site the first time, and some high-risk
sites are blocked; the categories are not listed.
https://support.claude.com/en/articles/13364135-use-claude-cowork-safely **[V]**

**A skill can direct either browser.** The browser tools are ordinary tools in
the same session, and skills load where those tools live. No doc says so
outright. **[I]** Write the skill browser-agnostic ("use the browser available
to you").

## Browser tools in detail

Source: the Claude Desktop app bundle, version 2.31226.1 built 2026-10-09,
read statically. No public doc lists these tools. **[V for that build; I for
other builds and rollouts]**

- **Tool names.** `read_page`, `computer`, `form_input`, `navigate`, `find`,
  `get_page_text`, `javascript_tool`, `read_console_messages`,
  `read_network_requests`, `resize_window`, `tabs_context`, `tabs_create`,
  `tabs_select`, `tabs_close`, `browser_batch`. Prefixes differ by host:
  `mcp__Claude_Browser__`, `mcp__remote-devices__Claude_Browser__` (cloud
  session linked to the Mac), `mcp__claude-in-chrome__`.
- **`javascript_tool`** runs code in the page's main world through CDP
  `Runtime.evaluate`, with REPL semantics: top-level `await` works and the last
  expression is returned as JSON. A same-origin `fetch` therefore sends the
  page's cookies, so it can call the site's own JSON endpoints, GET or POST.
  Timeout 45 s. It is paused while a page-opened popup (often a sign-in window)
  is open. It passes the same per-site approval as other page tools. Claude in
  Chrome has the same tool, plus a `tabId`.
- **Trim inside the page.** Have the script reduce the response to the fields
  you need before it returns. Raw responses run 18 to 40 times larger than the
  trimmed data (see [usage.md](usage.md)), and small returns keep personal
  data out of the transcript.
- **`navigate`** puts `https://` in front of anything without `http(s)://`, so
  a `javascript:` URL never runs.
- **`get_page_text`** returns the `innerText` of the longest `article`,
  `main`, `[role="main"]` or `#content`, else `body`, capped at 50,000
  characters by default. A GET to a JSON URL probably shows the raw JSON this
  way. **[I]**
- **`read_network_requests`** in the built-in browser returns a response body
  when given a `requestId`, but only for the tab's own origin, cut at 10,000
  characters. It never records request bodies. Claude in Chrome's copy has no
  body option in that build. **[I that bodies are unavailable there]**
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
- A page that shows neither the login title nor the expected signed-in title is
  a site change or an outage. Report it and stop, rather than signing in again.
- Login cookies are often session cookies, and server idle timers can be as
  short as 10 minutes. Whether the built-in browser keeps session cookies
  across an app quit is undocumented. **[I: test it]**

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
  browser once.
