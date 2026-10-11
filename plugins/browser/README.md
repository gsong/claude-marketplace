# browser

One skill, `/browser:chrome`, drives a real Google Chrome with [agent-browser](https://github.com/vercel-labs/agent-browser). agent-browser attaches to Chrome over CDP, Chrome's remote debugging port. Google sign-ins accept a Chrome started this way. They reject a Chrome that agent-browser launches by itself, because that one reports `navigator.webdriver=true`.

## Skills

| Skill             | Trigger                                    | Description                                                          |
| ----------------- | ------------------------------------------ | -------------------------------------------------------------------- |
| `/browser:chrome` | "use the browser", a page WebFetch refuses | Start or reach Chrome, then read and act on pages with agent-browser |

## Modes

The skill picks a mode from two facts: where the session runs, and whether the repo has an `agent-browser.json`. The skill treats a session as the container when `AGENT_BROWSER_CDP` is set or the OS is not macOS.

| Where     | `agent-browser.json` | What the skill does                                                                                 |
| --------- | -------------------- | --------------------------------------------------------------------------------------------------- |
| Mac       | yes                  | Runs `browser-start`, then drives the repo's persistent profile                                     |
| Mac       | no                   | Starts Chrome on a throwaway profile in the session scratchpad, and deletes it when done            |
| Container | yes                  | Probes `$AGENT_BROWSER_CDP`. If Chrome is down, asks you to run `mise run browser:start` on the Mac |
| Container | no                   | Stops, and says the repo needs `agent-browser.json` with a `cdp` port                               |

## Set up a repo

Add `agent-browser.json` at the repo root:

```json
{
  "cdp": "10082",
  "contentBoundary": true,
  "chromeProfile": "people-matcher"
}
```

- `cdp` is the port Chrome listens on. Give each repo its own. Two repos on one port drive the same Chrome, so one repo's session acts with the other repo's logins.
- `chromeProfile` names the profile directory, `~/.agent-browser/profiles/<chromeProfile>`. Chrome keeps the profile's cookies there, so the logins outlive each session.

Add a `browser:start` task to `mise.toml`, so you can start Chrome from a terminal on the Mac. The plugin cache path holds the version, so the task runs the newest installed copy:

```toml
[tasks."browser:start"]
run = '''
dir=$(ls -d "$HOME"/.claude/plugins/cache/gsong-marketplace/browser/*/ 2>/dev/null | sort -V | tail -1)
[ -n "$dir" ] || { echo "Install browser@gsong-marketplace first" >&2; exit 1; }
exec "$dir/skills/chrome/scripts/browser-start"
'''
```

Enable the plugin in `.claude/settings.json`, so teammates get it when they trust the repo:

```json
{
  "extraKnownMarketplaces": {
    "gsong-marketplace": {
      "source": { "source": "github", "repo": "gsong/claude-marketplace" }
    }
  },
  "enabledPlugins": { "browser@gsong-marketplace": true }
}
```

Some repos have browser-only jobs, such as a consent screen or a menu item no API reaches. Put those in a `browser-notes` skill under `.claude/skills/`. Its body starts by loading `/browser:chrome`. In turn, `/browser:chrome` loads it once Chrome is up.

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
