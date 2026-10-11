---
name: chrome
description: Browser work through agent-browser and a real Google Chrome. Use when a task needs a browser, such as a page WebFetch refuses, a web app's UI, or a service behind a sign-in, or when the user asks for the browser. Prefer it over other browser tools.
---

# Chrome

Drive a real Google Chrome with the `agent-browser` CLI, attached over CDP (Chrome's remote debugging port). Chrome launched this way reports `navigator.webdriver=false`, so Google and other sign-ins accept it. A Chrome that agent-browser launches by itself does not.

This skill owns the setup and the habits. For command syntax, load the `agent-browser:agent-browser` skill, or run `agent-browser skills get core --full`.

## 1. Pick the mode

Two facts pick the mode:

- **Where:** the session is in the **container** when `AGENT_BROWSER_CDP` is set or `uname` is not `Darwin`. Otherwise it is on the **Mac**.
- **Sidecar:** the repo root holds `agent-browser.json`, which names the CDP port (`cdp`) and the persistent profile (`chromeProfile`).

| Where     | Sidecar | Mode                                                                       |
| --------- | ------- | -------------------------------------------------------------------------- |
| Mac       | yes     | **Persistent**: start Chrome on the repo's profile                         |
| Mac       | no      | **Scratch**: start Chrome on a throwaway profile                           |
| Container | yes     | **Remote**: reach the Chrome a human runs on the Mac                       |
| Container | no      | Stop. Tell the user the repo needs `agent-browser.json` with a `cdp` port. |

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

It prints `port=<port>` and `profile=<dir>`. Pass `--cdp <port>` to every `agent-browser` command. The profile starts signed out of everything.

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
