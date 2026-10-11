---
name: setup
description: Set up a repo for /browser:chrome. Writes agent-browser.json with a CDP port no other repo uses, the browser:start mise task, and the plugin entries in .claude/settings.json. Use when the user asks to set a repo up for the browser, or when /browser:chrome says the repo needs agent-browser.json.
---

# Setup

Give a repo its own persistent Chrome. It gets a CDP port (Chrome's remote debugging port) and a profile directory that no other repo uses. Two repos on one port drive the same Chrome, so one repo's session acts with the other repo's logins.

Setup writes three files at the repo root. It merges into a file that already exists and keeps every entry already there.

## 1. Check where the session runs

The session is in the **container** when `AGENT_BROWSER_CDP` is set or `uname` is not `Darwin`. In the container, stop and write nothing. Tell the user to run `/browser:setup` in a Claude session on the Mac. The container cannot see the Mac's port registry or Chrome processes.

On the Mac, `cd` to the root of the current checkout, `git rev-parse --show-toplevel`. Setup writes the files there.

## 2. agent-browser.json

When `agent-browser.json` exists, leave it as it is. Read its `cdp` and `chromeProfile` for the report.

When it is absent:

1. Pick the profile name from the main checkout's directory, so every worktree of the repo gets the same name. That directory is the parent of `git rev-parse --path-format=absolute --git-common-dir`. Lowercase its name. Turn each run of characters other than letters, digits, `.`, `_` and `-` into one `-`.
2. Check whether another repo owns the name. It does when `~/.agent-browser/profiles/<name>` exists, or when `~/.agent-browser/ports` lists the name. Then ask the user whether this repo shares that profile or takes another name. Sharing means both repos use one Chrome, one port, and one set of logins.
3. Claim the port:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/skills/chrome/scripts/ports" claim "<name>"
   ```

   It prints the port and records it in `~/.agent-browser/ports`. A profile the registry already lists gets its own port back. When it exits 1, show the user its message and stop.

4. Write `agent-browser.json`, one key per line, because `browser-start` reads it line by line:

   ```json
   {
     "cdp": "<port>",
     "contentBoundary": true,
     "chromeProfile": "<name>"
   }
   ```

The step is done when `agent-browser.json` names a `cdp` port and a `chromeProfile`.

## 3. mise.toml

The `browser:start` task lets the user start Chrome from a terminal on the Mac. The plugin cache path holds the version, so the task runs the newest installed copy.

When `mise.toml` already defines a `browser:start` task, under any quoting of the table name, leave the file as it is. Otherwise append this block, creating the file when it is absent:

```toml
[tasks."browser:start"]
description = "Open this repo's Chrome for agent-browser"
run = '''
dir=$(ls -d "$HOME"/.claude/plugins/cache/gsong-marketplace/browser/*/ 2>/dev/null | sort -V | tail -1)
[ -n "$dir" ] || { echo "Install browser@gsong-marketplace first" >&2; exit 1; }
exec "$dir/skills/chrome/scripts/browser-start"
'''
```

## 4. .claude/settings.json

These entries enable the plugin for each teammate who trusts the repo. Merge them into `.claude/settings.json`, creating the file when it is absent:

```json
{
  "extraKnownMarketplaces": {
    "gsong-marketplace": {
      "source": { "source": "github", "repo": "gsong/claude-marketplace" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": { "browser@gsong-marketplace": true }
}
```

Add each key inside the existing `extraKnownMarketplaces` and `enabledPlugins` objects, beside their other entries. When `gsong-marketplace` is already a known marketplace, keep its entry as it is. Read the file back and confirm it parses as JSON.

## 5. Report

Tell the user:

- for each of the three files, whether setup wrote it, merged into it, or left it as it was;
- the port and the profile name;
- the next step: `/browser:chrome` starts Chrome on the profile, as does `mise run browser:start` on the Mac. The profile starts signed out. The user signs in once in that Chrome window, and the profile keeps the logins;
- to commit the three files, so teammates and the container get the same setup.
