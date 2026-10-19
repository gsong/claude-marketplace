---
name: setup
description: Set up a repo for browser:chrome. Writes agent-browser.json with a CDP port no other repo uses, the browser:start mise task, and the plugin entries in .claude/settings.json. Use when the user asks to set a repo up for the browser, or when browser:chrome says the repo needs agent-browser.json.
---

# Setup

Give a repo its own persistent Chrome. It gets a CDP port (Chrome's remote debugging port) and a profile directory that no other repo uses. Two repos on one port drive the same Chrome, so one repo's session acts with the other repo's logins.

## 1. Run setup

Run the script from inside the checkout to set up:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/chrome/scripts/setup"
```

Setup finds the repo root itself. It runs every check before it writes anything, so a run that exits non-zero has changed no file and claimed no port.

## 2. Answer its questions

Three exit statuses are questions for the user. Show the user the script's message, ask with the wording below, and run setup again with the answer's flag added. Keep the flags from earlier answers, so a second question means a third run.

- **8, the profile name is in use.** Ask: "Another checkout holds the profile name in the message. It may be this repo's other worktree, an earlier setup of this repo, or another repo with the same directory name. Share that profile, with its port and its logins, or give this repo another name?" Sharing means `--share`. Another name means `--name <name>`, with a name the user picks of lowercase letters, digits, `.`, `_` and `-`.
- **10, git ignores `agent-browser.json`.** Ask: "Git ignores `agent-browser.json`, by the rule in the message. An ignored file never reaches teammates or the container, and `git add -A` skips it without a word. Change the rule, or keep the setup on this Mac?" Change means `--unignore`: setup deletes a `.gitignore` line that names only `agent-browser.json`, or else appends `!/agent-browser.json` to the root `.gitignore`. Keep means `--keep-ignored`.
- **11, a file task defines `browser:start`.** Ask: "The file in the message already defines the `browser:start` mise task. Replace it with the plugin's task, or keep it?" Replace means `--replace-task`: setup deletes the file and appends the task to `mise.toml`. Keep means `--keep-task`.

The other non-zero statuses stop setup. Show the user the message, and add what to do:

- **2:** the flags were wrong. Fix the command and run it again.
- **3:** the session runs in the container. Tell the user to run `/browser:setup` in a Claude session on the Mac. The container cannot see the Mac's port registry or Chrome processes.
- **4:** the session is not inside a git repo. Ask which checkout to set up.
- **5:** jq is missing. The user installs it, such as with `brew install jq`.
- **6:** mise is missing, or it failed. An untrusted `mise.toml` is the usual failure: the user runs `mise trust` in the repo after reading the file.
- **7:** the `--name` the user picked breaks the name rule. Ask for another name.
- **9:** the existing `agent-browser.json` needs a fix that the message names. Setup never rewrites the file, so the user fixes it.
- **12:** `.claude/settings.json` does not parse, or holds the wrong shape. The user fixes it.
- **13:** no port could be claimed or recorded. The message says why.

## 3. Report

On exit 0, setup prints `key=value` lines. Tell the user:

- the port and the profile name, from `port=` and `profile=`;
- for each of the three files, whether setup wrote it, merged into it, or kept it as it was, from `agent_browser_json=`, `mise_toml=` and `settings_json=`;
- whether git ignores `agent-browser.json`, from `ignored=`. When it is `yes`, say that the setup stays on this Mac. When `unignored=` is present, say how setup changed the ignore rule;
- when `deleted_task=` is present, that setup deleted that file task;
- the next step: `/browser:chrome` starts Chrome on the profile, as does `mise run browser:start` on the Mac. The profile starts signed out. The user signs in once in that Chrome window, and the profile keeps the logins;
- to commit `agent-browser.json`, `mise.toml` and `.claude/settings.json`, so teammates and the container get the same setup. The commit also takes a changed `.gitignore` and a deleted file task.
