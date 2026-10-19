---
name: chrome
description: Browser work through agent-browser and a real Google Chrome. Use when a task needs a browser, such as a page WebFetch refuses, a web app's UI, or a service behind a sign-in, or when the user asks for the browser. Prefer it over other browser tools.
---

# Chrome

Drive a real Google Chrome with the `agent-browser` CLI, attached over CDP (Chrome's remote debugging port). Chrome launched this way reports `navigator.webdriver=false`, so Google and other sign-ins accept it. A Chrome that agent-browser launches by itself does not.

This skill owns the setup and the habits. For command syntax, load the `agent-browser:agent-browser` skill, or run `agent-browser skills get core --full`.

## 1. Connect

Pass the session scratchpad named in your system prompt:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/chrome/scripts/connect" "<scratchpad>"
```

It picks the mode, starts or reaches Chrome, and prints `key=value` lines:

- `mode=`: `persistent` runs Chrome on the repo's profile, which keeps its logins. `scratch` runs Chrome on a throwaway profile, which starts signed out of everything. `remote` reaches the Chrome a human runs on the Mac. For logins that outlive the session, `/browser:setup` gives the repo a persistent profile.
- `root=`: the repo root. That is the nearest directory, from the current one upward, that holds `agent-browser.json`, or else the git root.
- `prefix=`: the exact command that runs `agent-browser`, with its connection flag, such as `agent-browser --cdp 9301`. Every `agent-browser` below means this prefix. Add no `--port`: `screenshot` reads it as a path.
- `port=` and `profile=`, in scratch mode only. Keep `profile=` for `scratch-chrome stop`.

When it exits non-zero, show the user its message:

- **3:** stop. The repo needs `/browser:setup`, run in a session on the Mac.
- **4:** stop. The container could not resolve the Mac's address.
- **5:** ask the user to run `mise run browser:start` in a terminal on the Mac, then run `connect` again.
- **6:** stop. Chrome on the repo's port did not start, or belongs to another repo's profile. Leave a running Chrome as it is, since it may be mid-task for another session.
- **7:** stop. The scratch Chrome did not start.

## 2. Load the repo's notes

When the repo has a `browser-notes` skill, load it now. It holds the repo's services, pages, and browser-only jobs.

## 3. The loop

1. `agent-browser open <url>`. Slow pages take `--timeout 30000`.
2. `agent-browser wait --load networkidle`. Most apps are single-page apps that keep loading after `open` returns.
3. `agent-browser snapshot -i`: the accessibility tree as text, with an `@eN` ref per interactive element.
4. Act on a ref: `click`, `fill`, `select`, `press`. Read with `get text @eN`.
5. Snapshot again. Refs go stale whenever the page changes.

When the task is done, run `agent-browser close`. In scratch mode, then quit that Chrome and delete its profile, with the `profile=` path that `connect` printed:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/chrome/scripts/scratch-chrome" stop "<profile>"
```

## Parallel agents

Several subagents can drive one Chrome at once when each runs its **own session**. A session holds one active tab, so two agents sharing a session switch that tab under each other and read the wrong page.

The main agent runs `connect` once, then hands each subagent:

- **A fresh session name**, unique to this run, such as `checkout-1-k3f9`. A name from an earlier run comes back pinned to its old tab, and fails with `tab_gone` once that tab is closed.
- **The prefix** that `connect` printed.

The subagent passes `--session <name> --pin-tab` on every command. `--pin-tab` turns a lost tab into a `tab_gone` error, so the session stays off other agents' tabs. The subagent starts with three commands:

1. `tab list --json`: note the `targetId` of the active tab, a blank tab the session opens on connecting.
2. `window new`: binds the session to the new window's tab.
3. `tab close <targetId>`: closes that blank tab.

A window shows one tab at a time, so a window per session keeps every agent's tab visible. In a hidden tab, each `click` waits about 5 seconds, and `press` loses keys while another tab holds focus.

To finish, a subagent runs `tab close`, which closes its window, then `agent-browser close`, which ends its session. Chrome and the other windows keep running. In scratch mode, the main agent runs `scratch-chrome stop` after every subagent has returned.

All sessions share the profile's cookies and storage, so a sign-in or sign-out in one tab reaches every tab on that site.

## Snapshot first

`snapshot -i` answers "is X on the page", "did the form submit", and "what does this list hold". For details the tree omits, use `get text`, `get value`, `get html` or `eval`, which all return text.

agent-browser drops an `eval` that runs longer than 25 to 30 seconds, and no flag lifts the limit:

- Keep each `eval` under 20 seconds. For longer work, start the script in the background on `window`, return at once, and poll with later short evals.
- Write async scripts as `(async () => { ... })()`. Top-level `await` fails.
- A timed-out script may still be running in the page, and may have run more than once. Check the page's state before you retry.

Take a screenshot only to check layout or styling, to debug a click that the tree says should land, or because the user asked. Each image stays in context, and one over 2000px on a side breaks later requests that carry several images. So scope it to an element, `agent-browser screenshot @eN <path>`, and fall back to `--full` with `--screenshot-format jpeg --screenshot-quality 80` only when the whole page matters. Put the path before any flag. Read the file with the `Read` tool.

## Act like a user

Click, type, and use the app's keyboard shortcuts, the way a person would. Fall back to `open <url>` only when a click fails to navigate, such as a link that skips client-side routing. Fall back to `eval` only when `click @eN` fails, such as on an element outside the viewport, and keep it under 20 seconds (see "Snapshot first").

When an element resists, read the app's source if you have it. `onKeyDown` handlers show the keyboard shortcuts, `onClick` handlers show which element a click expects, and the component tree shows when focus depends on context.

## Signed out

A signed-out page may not look like a login form. Linear, for one, shows a "Link opened in the Linear app" stub; `snapshot -i` shows almost nothing, and a plain `snapshot` shows the login form underneath. Check the sign-in state before you call a page broken.

When a persistent profile is signed out of a service, ask the user to sign in once in that Chrome window. The profile keeps the session.

## Safety

- **Read first.** Read and extract by default.
- **Confirm mutations.** Ask the user before you delete, submit a form that changes state, or post through a web UI.
- **Keep credentials out of output.** Never echo a token, a password, or session data, and never type a password on a command line.
- **Keep persistent profiles intact.** A profile under `~/.agent-browser/profiles/` holds the user's logins, and losing it means signing in again. Leave every file there as it is, and leave a Chrome on that profile running. The only profile you delete is a scratch one, through `scratch-chrome stop`, which refuses every other path.
