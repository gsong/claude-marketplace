---
name: setup
description: Set up cf-api's Cloudflare API token. Creates a full-access user API token in the Cloudflare dashboard, saves it straight to 1Password, and points cf-api at it. Use when the user asks to set up Cloudflare API access, or when cf-api exits 3.
---

# Setup

Create one Cloudflare API token for cf-api, and keep it in 1Password. The token never passes through the conversation: it goes from the dashboard page straight into `save-token`.

## 1. Agree the vault and the account

Ask the user which 1Password vault holds the token. List the vaults with `op vault list`, which prints names only.

The token covers every account the user's Cloudflare login reaches, so no account choice is needed here.

Done when the user has named a vault.

## 2. Create the token in the dashboard

Load `/browser:chrome`, and open `https://dash.cloudflare.com/profile/api-tokens`. The user must be signed in to Cloudflare in that Chrome. When the page shows a sign-in form, ask the user to sign in there.

1. Click **Create Token**, then **Start from scratch**, then **Start with an Account policy**.
2. Click **Bulk Select**, then **Add all Read & Write permissions**. Every group shows all of its permissions selected.
3. Close the editor. Click **Add new policy**, then **Add new Zone policy**, and bulk select the same way. Leave the resource as **All zones**.
4. Name the token for this machine, such as `Claude Code full access (<Mac name>)`. Leave expiration at **No expiration** unless the user asks for one.
5. Click **Continue to summary**, read the summary back to the user, and click **Create Token** once they agree.

The dashboard changes over time. When a control is missing, take one screenshot, find the nearest equivalent, and tell the user what differed.

Done when the page says the token was created and shows it once.

## 3. Save it

Pipe the token from the page into `save-token`. Never print it, echo it, or write it to a file of your own:

```bash
agent-browser eval '(() => { const t = document.body.innerText; const i = t.indexOf("will not be shown again"); const m = t.slice(i).match(/[A-Za-z0-9_-]{40,}/); return m ? m[0] : ""; })()' |
  jq -r . |
  "${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/save-token" --vault "<vault>" --title "<token name>"
```

Use the `agent-browser` prefix that `/browser:chrome` printed. When the page wording differs, adjust the anchor text in the `eval`, never the step that pipes.

`save-token` checks the token with Cloudflare at `https://api.cloudflare.com/client/v4/user/tokens/verify`, creates an API Credential item in the vault, and writes the reference to `~/.config/cloudflare-api/config`. On exit 0 it prints `key=value` lines. On any other exit, show the user its message:

- **2:** the flags were wrong.
- **3:** the `eval` found no token. Snapshot the page, fix the anchor, and pipe again while the page still shows the token.
- **4:** Cloudflare did not report the token as active. Nothing was saved.
- **5:** 1Password could not create the item. Check the vault name and that 1Password is unlocked.
- **6:** a command is missing. The message names it.

## 4. Check and report

Run `"${CLAUDE_PLUGIN_ROOT}/skills/api/scripts/cf-api" GET /user/tokens/verify` and confirm `result.status` is `active`.

Tell the user:

- the token's name and that it has every Read & Write account and zone permission, with no expiry;
- the 1Password item and vault, from `item=` and `vault=`;
- when `replaced=` is present, that the config pointed at that token before, and that the old token still exists in Cloudflare and 1Password until they delete it;
- that cf-api caches the token in the macOS Keychain after the first call, and `cf-api --forget` clears it.
