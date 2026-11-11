---
name: api
description: Cloudflare account work, done without handing steps to the user. Picks wrangler first, then the Cloudflare API through cf-api for what wrangler lacks, such as Access and Zero Trust apps, policies and identity providers, DNS, and API tokens. Use for any task that reads or changes a Cloudflare account.
---

# Cloudflare

Do the Cloudflare work yourself, through the first tool on this list that can do it:

1. **wrangler**, for everything it covers: Workers, D1, KV, R2, Queues, Pages, secrets, deploys. Run it the way the repo does, such as `pnpm exec wrangler` when `package.json` lists it.
2. **cf-api**, the Cloudflare API at `https://api.cloudflare.com/client/v4` with a full-access token, for everything else. wrangler's login grants no Access, Zero Trust or DNS scopes, so those go here.
3. **The Cloudflare MCP server**, only when the API cannot do the job.
4. **The dashboard**, through `/browser:chrome`, only when no API exists, such as checking out a paid plan.

## cf-api

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/api/scripts/cf-api" METHOD PATH [JSON_BODY]
```

PATH starts with `/`, as in [Cloudflare's API reference](https://developers.cloudflare.com/api/). `{account}` in PATH becomes the account ID: `CF_ACCOUNT_ID` when set, else the `account_id` in the nearest `wrangler.jsonc`, `wrangler.json` or `wrangler.toml`, else the only account the token reaches.

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/api/scripts/cf-api" GET /accounts/{account}/access/apps
"${CLAUDE_PLUGIN_ROOT}/skills/api/scripts/cf-api" PUT /accounts/{account}/access/organizations '{"name": "team.cloudflareaccess.com", "auth_domain": "team.cloudflareaccess.com"}'
```

It prints Cloudflare's JSON response. Read `success` and `errors` from it. The exit status:

- **0:** a 2xx answer.
- **1:** an error answer, still printed. Fix the request from Cloudflare's `errors`.
- **2:** the arguments were wrong.
- **3:** no token is set up. Run `/cloudflare:setup`.
- **4:** 1Password could not read the token. Ask the user to unlock 1Password, then retry.
- **5:** PATH holds `{account}` and the token reaches several accounts. Set `CF_ACCOUNT_ID`, after asking the user which account when the task does not say.
- **6:** a command it needs is missing. The message names it.
- **7:** curl could not reach `api.cloudflare.com`. Check the network, then retry.

The token stays secret. cf-api passes it to curl on stdin and caches it in the macOS Keychain, so 1Password prompts once, not on every call. A cached token Cloudflare rejects is dropped and read again from 1Password. `cf-api --forget` clears the cache.

Before a change that is hard to undo, such as deleting a resource or changing a team domain, read the current state with a GET and confirm with the user.
