# browser

`/browser:chrome` drives a real Google Chrome with [agent-browser](https://github.com/vercel-labs/agent-browser). agent-browser attaches to Chrome over CDP, Chrome's remote debugging port. Google sign-ins accept a Chrome started this way. They reject a Chrome that agent-browser launches by itself, because that one reports `navigator.webdriver=true`.

## Skills

| Skill             | Trigger                                    | Description                                                          |
| ----------------- | ------------------------------------------ | -------------------------------------------------------------------- |
| `/browser:chrome` | "use the browser", a page WebFetch refuses | Start or reach Chrome, then read and act on pages with agent-browser |
| `/browser:setup`  | "set this repo up for the browser"         | Write a repo's browser config, with a CDP port no other repo uses    |

## Modes

`/browser:chrome` picks a mode from two facts: where the session runs, and whether the repo has an `agent-browser.json`. The skill treats a session as the container when `AGENT_BROWSER_CDP` is set or the OS is not macOS.

| Where     | `agent-browser.json` | What the skill does                                                                                 |
| --------- | -------------------- | --------------------------------------------------------------------------------------------------- |
| Mac       | yes                  | Runs `browser-start`, then drives the repo's persistent profile                                     |
| Mac       | no                   | Starts Chrome on a throwaway profile in the session scratchpad, and deletes it when done            |
| Container | yes                  | Probes `$AGENT_BROWSER_CDP`. If Chrome is down, asks you to run `mise run browser:start` on the Mac |
| Container | no                   | Stops, and asks you to run `/browser:setup` in a session on the Mac                                 |

## Set up a repo

Run `/browser:setup` in a Claude session on the Mac. It writes three files at the repo root, and merges into a file that already exists:

- `agent-browser.json` names the port Chrome listens on (`cdp`) and the profile directory (`chromeProfile`). Chrome keeps the profile's cookies in `~/.agent-browser/profiles/<chromeProfile>`, so the logins outlive each session. Setup leaves an existing `agent-browser.json` as it is.
- `mise.toml` gets a `browser:start` task, so you can start Chrome from a terminal on the Mac.
- `.claude/settings.json` gets the marketplace and enables the plugin, so teammates get it when they trust the repo.

Commit the three files. In the container, setup stops and asks for the Mac, because it cannot see the Mac's port registry or Chrome processes.

Some repos have browser-only jobs, such as a consent screen or a menu item no API reaches. Put those in a `browser-notes` skill under `.claude/skills/`. Its body starts by loading `/browser:chrome`. In turn, `/browser:chrome` loads it once Chrome is up.

### Ports

Each repo needs its own port. Two repos on one port drive the same Chrome, so one repo's session acts with the other repo's logins.

The port registry, `~/.agent-browser/ports`, holds one `<port> <profile>` line per repo. Setup picks the first port in 10100-10199 that the registry does not list, no running Chrome holds, and nothing answers on. `browser-start` records its port each time it runs, so a repo set up by hand joins the registry on its next start. When the registry gives that port to another profile, `browser-start` warns and opens Chrome anyway.

## Profile safety

Losing a persistent profile means signing in to every service again. The plugin guards it three ways:

- Nothing in the plugin deletes, moves, renames, or resets anything under `~/.agent-browser/profiles/`.
- `browser-start` never kills Chrome. When a Chrome on another profile holds the port, it exits 1 and names both profiles.
- `scratch-chrome stop` deletes only a `chrome-*` directory inside a directory named `scratchpad`. It resolves symlinks and `..` first, and it refuses every other path.

The tests in `tests/` check the last two, against stand-ins for `ps`, `curl`, and `open`.

## Prerequisites

- macOS with Google Chrome.
- agent-browser 0.38 or later, installed globally or pinned in the repo's `package.json`. When `package.json` lists it, the skill runs `pnpm exec agent-browser`. Older versions may spawn their own headless Chrome when nothing answers on the port.
- `curl`.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install browser@gsong-marketplace
```
