# cloudflare

`/cloudflare:api` lets Claude change and read a Cloudflare account on its own. It uses wrangler for what wrangler covers, and the Cloudflare API for the rest. wrangler's login can't grant Access, Zero Trust or DNS permissions. Without the API, those jobs fall back to clicking through the dashboard.

## Skills

| Skill               | Trigger                                       | Description                                                                       |
| ------------------- | --------------------------------------------- | --------------------------------------------------------------------------------- |
| `/cloudflare:api`   | any task that reads or changes Cloudflare     | Pick wrangler, then `cf-api`, then the MCP server, then the dashboard             |
| `/cloudflare:setup` | "set up Cloudflare API access", cf-api exit 3 | Create a full-access API token in the dashboard and save it straight to 1Password |

## How the token is kept

`/cloudflare:setup` creates one user API token with every Read & Write account and zone permission. Claude reads it off the dashboard page and pipes it to `save-token`, so it never enters the conversation. `save-token` checks it with Cloudflare's API at `api.cloudflare.com`, stores it as a 1Password API Credential item, and writes the item's reference to `~/.config/cloudflare-api/config`:

```
token_ref=op://<vault>/<item id>/credential
```

`cf-api` sends every request to `https://api.cloudflare.com/client/v4`, and no other host. It takes the token from the first of these that has one:

1. `CLOUDFLARE_API_TOKEN`, when set.
2. The macOS Keychain, under the service `cloudflare-api-token`.
3. 1Password, at `token_ref`. A token read from 1Password goes into the Keychain, so 1Password prompts once, not on every call.

When Cloudflare rejects a cached token, `cf-api` drops it, reads 1Password again and retries once. `cf-api --forget` clears the cache.

The token stays off every command line, where `ps` would show it:

- curl reads the Authorization header on stdin.
- `security` reads the Keychain command on stdin.
- 1Password reads a template file that only you can read. `save-token` deletes it once the item exists.

The Keychain copy is the price of not being prompted. Any process running as you can read it back with `security find-generic-password`.

## The account ID

`{account}` in a path becomes the account ID, from the first of:

1. `CF_ACCOUNT_ID`.
2. The `account_id` in the nearest `wrangler.jsonc`, `wrangler.json` or `wrangler.toml`, from the current directory up.
3. The only account the token reaches. When it reaches several, `cf-api` exits 5 and asks for `CF_ACCOUNT_ID`.

## Tests

`tests/` runs both scripts against stand-ins for curl, op and security. The suites check:

- The token never reaches a command line or the output.
- The cache, and its retry after a rejected token.
- The account lookup.
- Every exit status.

Run them with `mise run test`.

## Prerequisites

- macOS, for the Keychain cache. Without `security`, set `CLOUDFLARE_API_TOKEN` instead.
- curl and jq. macOS 15 and later ship jq as `/usr/bin/jq`.
- The 1Password CLI, `op`, signed in.
- The `browser` plugin, for `/cloudflare:setup`'s dashboard steps.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install cloudflare@gsong-marketplace
```
