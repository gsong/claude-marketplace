---
name: chrome
description: Browser work through agent-browser and a real Google Chrome. Use when a task needs a browser, such as a page WebFetch refuses, a web app's UI, or a service behind a sign-in, or when the user asks for the browser. Prefer it over other browser tools.
---

# Chrome

Drive a real Google Chrome with the `agent-browser` CLI, attached over CDP (Chrome's remote debugging port). Chrome launched this way reports `navigator.webdriver=false`, so Google and other sign-ins accept it. A Chrome that agent-browser launches by itself does not.

This skill owns the setup and the habits. For command syntax, load the `agent-browser:agent-browser` skill, or run `agent-browser skills get core --full`.

## 1. Pick the mode

First find the **repo root**: the nearest directory, from the current one upward, that holds `agent-browser.json`.

```bash
dir=$PWD
while [ "$dir" != / ] && [ ! -f "$dir/agent-browser.json" ]; do dir=$(dirname "$dir"); done
```

When the loop stops at `/`, no directory holds one, and the repo root is `git rev-parse --show-toplevel`. Search upward even inside a git repo: a workspace of nested clones keeps one `agent-browser.json` at its top, above each clone's own git root. Every later step means this directory by "repo root".

Two facts pick the mode:

- **Where:** the session is in the **container** when `AGENT_BROWSER_CDP` is set or `uname` is not `Darwin`. Otherwise it is on the **Mac**.
- **Sidecar:** the repo root holds `agent-browser.json`, which names the CDP port (`cdp`) and the persistent profile (`chromeProfile`).

| Where     | Sidecar | Mode                                                                 |
| --------- | ------- | -------------------------------------------------------------------- |
| Mac       | yes     | **Persistent**: start Chrome on the repo's profile                   |
| Mac       | no      | **Scratch**: start Chrome on a throwaway profile                     |
| Container | yes     | **Remote**: reach the Chrome a human runs on the Mac                 |
| Container | no      | Stop. Tell the user to run `/browser:setup` in a session on the Mac. |

The container never launches Chrome.

## 2. Start or reach Chrome

The step is done when a CDP endpoint answers.

**Persistent.** From the repo root, run:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/chrome/scripts/browser-start"
```

It opens Chrome on `~/.agent-browser/profiles/<chromeProfile>`, or reports that Chrome is already open there. When it exits 1 because another profile holds the port, show the user its message and stop. That Chrome may belong to another repo's session, so leave it running.

`agent-browser` reads `./agent-browser.json` from the current directory only. Run commands from the repo root, or pass `--config <repo root>/agent-browser.json`. Pass no `--port`: `screenshot` reads it as a path.

**Scratch.** Pass the session scratchpad named in your system prompt:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/chrome/scripts/scratch-chrome" start "<scratchpad>"
```

It prints `port=<port>` and `profile=<dir>`. Pass `--cdp <port>` to every `agent-browser` command. The profile starts signed out of everything. For logins that outlive the session, `/browser:setup` gives the repo a persistent profile.

**Remote.** Probe the Mac's Chrome:

```bash
curl -sf --max-time 2 "$AGENT_BROWSER_CDP/json/version"
```

If it fails, ask the user to run `mise run browser:start` in a host terminal on the Mac, then probe again. If `AGENT_BROWSER_CDP` is empty, the container could not resolve the Mac's address; tell the user. `AGENT_BROWSER_CDP` overrides `agent-browser.json`, so commands need no flag.

## 3. Pick the binary

When the repo's `package.json` lists `agent-browser`, run `pnpm exec agent-browser`, so the repo's pinned version runs. Otherwise run the global `agent-browser`. Every `agent-browser` below means that choice.

## 4. Load the repo's notes

When the repo has a `browser-notes` skill, load it now. It holds the repo's services, pages, and browser-only jobs.

## 5. The loop

1. `agent-browser open <url>`. Slow pages take `--timeout 30000`.
2. `agent-browser wait --load networkidle`. Most apps are single-page apps that keep loading after `open` returns.
3. `agent-browser snapshot -i`: the accessibility tree as text, with an `@eN` ref per interactive element.
4. Act on a ref: `click`, `fill`, `select`, `press`. Read with `get text @eN`.
5. Snapshot again. Refs go stale whenever the page changes.

When the task is done, run `agent-browser close`. In scratch mode, then run `scratch-chrome stop "<profile>"` with the `profile=` path that `start` printed. It quits that Chrome and deletes the profile.

## Parallel agents

Several subagents can drive one Chrome at once when each runs its **own session**. A session holds one active tab, so two agents sharing a session switch that tab under each other and read the wrong page.

The main agent runs steps 1 and 2 once, then hands each subagent:

- **A fresh session name**, unique to this run, such as `checkout-1-k3f9`. A name from an earlier run comes back pinned to its old tab, and fails with `tab_gone` once that tab is closed.
- **The connection**: `--cdp <port>` in scratch mode, or the repo root in persistent mode.

The subagent passes `--session <name> --pin-tab` on every command. Its first `open` opens a new tab and binds the session to it. `--pin-tab` turns a lost tab into a `tab_gone` error, so the session stays off other agents' tabs.

A subagent's `agent-browser close` ends its own session; Chrome and the other tabs keep running. In scratch mode, the main agent runs `scratch-chrome stop` after every subagent has returned.

All sessions share the profile's cookies and storage, so a sign-in or sign-out in one tab reaches every tab on that site.

## Snapshot first

`snapshot -i` answers "is X on the page", "did the form submit", and "what does this list hold". For details the tree omits, use `get text`, `get value`, `get html` or `eval`, which all return text.

Take a screenshot only to check layout or styling, to debug a click that the tree says should land, or because the user asked. Each image stays in context, and one over 2000px on a side breaks later requests that carry several images. So scope it to an element, `agent-browser screenshot @eN <path>`, and fall back to `--full` with `--screenshot-format jpeg --screenshot-quality 80` only when the whole page matters. Put the path before any flag. Read the file with the `Read` tool.

## Act like a user

Click, type, and use the app's keyboard shortcuts, the way a person would. Fall back to `open <url>` only when a click fails to navigate, such as a link that skips client-side routing. Fall back to `eval` only when `click @eN` fails, such as on an element outside the viewport.

When an element resists, read the app's source if you have it. `onKeyDown` handlers show the keyboard shortcuts, `onClick` handlers show which element a click expects, and the component tree shows when focus depends on context.

## Signed out

A signed-out page may not look like a login form. Linear, for one, shows a "Link opened in the Linear app" stub; `snapshot -i` shows almost nothing, and a plain `snapshot` shows the login form underneath. Check the sign-in state before you call a page broken.

When a persistent profile is signed out of a service, ask the user to sign in once in that Chrome window. The profile keeps the session.

## Safety

- **Read first.** Read and extract by default.
- **Confirm mutations.** Ask the user before you delete, submit a form that changes state, or post through a web UI.
- **Keep credentials out of output.** Never echo a token, a password, or session data, and never type a password on a command line.
- **Keep persistent profiles intact.** A profile under `~/.agent-browser/profiles/` holds the user's logins, and losing it means signing in again. Leave every file there as it is, and leave a Chrome on that profile running. The only profile you delete is a scratch one, through `scratch-chrome stop`, which refuses every other path.
