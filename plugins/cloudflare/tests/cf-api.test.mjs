import assert from "node:assert/strict";
import { join } from "node:path";
import { test } from "node:test";

import { ACCOUNT, CF_API, GOOD, REF, STALE, world } from "./helpers.mjs";

const API = "https://api.cloudflare.com/client/v4";

// A world where 1Password holds the good token and the config points at it.
function setUp() {
  const w = world();
  w.acceptsTokens(GOOD);
  w.opHolds(REF, GOOD);
  w.config(`token_ref=${REF}\n`);
  return w;
}

// The token must never reach a command line, where ps could show it.
function assertNoTokenInArgs(w, ...tokens) {
  for (const call of [...w.opCalls(), ...w.securityCalls()]) {
    for (const t of tokens) assert.ok(!call.includes(t), `token in: ${call}`);
  }
}

test("prints the body and exits 0 on a 2xx answer", () => {
  const w = setUp();
  w.replies(`GET ${API}/zones`, 200, { success: true, result: [{ id: "z" }] });
  const r = w.run(CF_API, ["GET", "/zones"]);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(JSON.parse(r.stdout).result, [{ id: "z" }]);
  assert.ok(!r.stdout.includes(GOOD) && !r.stderr.includes(GOOD));
});

test("reads 1Password once, then answers from the Keychain cache", () => {
  const w = setUp();
  assert.equal(w.run(CF_API, ["GET", "/zones"]).status, 0);
  assert.equal(w.cached(), GOOD);
  assert.equal(w.run(CF_API, ["GET", "/zones"]).status, 0);
  assert.equal(w.opCalls().filter((c) => c.startsWith("read ")).length, 1);
  assertNoTokenInArgs(w, GOOD);
});

test("drops a rejected cached token, rereads 1Password and retries once", () => {
  const w = setUp();
  w.cache(STALE);
  const r = w.run(CF_API, ["GET", "/zones"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(w.cached(), GOOD);
  const tokensSent = w.curlCalls().map((c) => c.split(" ")[2]);
  assert.deepEqual(tokensSent, [STALE, GOOD]);
  assertNoTokenInArgs(w, GOOD, STALE);
});

test("does not retry a token fresh from 1Password", () => {
  const w = setUp();
  w.acceptsTokens(); // Cloudflare rejects every token.
  const r = w.run(CF_API, ["GET", "/zones"]);
  assert.equal(r.status, 1);
  assert.equal(w.curlCalls().length, 1);
  assert.match(JSON.parse(r.stdout).errors[0].message, /Authentication/);
});

test("keeps the cache on an error that is not about the token", () => {
  const w = setUp();
  w.cache(GOOD);
  w.replies(`GET ${API}/zones/missing`, 404, {
    success: false,
    errors: [{ code: 7003, message: "Could not route" }],
  });
  const r = w.run(CF_API, ["GET", "/zones/missing"]);
  assert.equal(r.status, 1);
  assert.equal(w.curlCalls().length, 1);
  assert.equal(w.cached(), GOOD);
});

test("uses CLOUDFLARE_API_TOKEN without 1Password or the Keychain", () => {
  const w = world();
  w.acceptsTokens(GOOD);
  const r = w.run(CF_API, ["GET", "/zones"], {
    env: { CLOUDFLARE_API_TOKEN: GOOD },
  });
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(w.opCalls(), []);
  assert.deepEqual(w.securityCalls(), []);
});

test("exits 3 and names /cloudflare:setup when no token is set up", () => {
  const w = world();
  const r = w.run(CF_API, ["GET", "/zones"]);
  assert.equal(r.status, 3);
  assert.match(r.stderr, /\/cloudflare:setup/);
});

test("exits 4 when 1Password cannot read the token", () => {
  const w = world();
  w.config(`token_ref=${REF}\n`);
  const r = w.run(CF_API, ["GET", "/zones"]);
  assert.equal(r.status, 4);
  assert.match(r.stderr, /1Password could not read/);
});

test("sends the method and body it was given", () => {
  const w = setUp();
  const r = w.run(CF_API, ["PUT", "/zones/z", '{"a":1}']);
  assert.equal(r.status, 0, r.stderr);
  assert.match(w.curlCalls()[0], new RegExp(`^PUT ${API}/zones/z `));
  assert.deepEqual(w.curlBodies(), ['{"a":1}']);
});

// curl --data reads the file a leading @ names. --data-raw sends it as text.
test("sends a body starting with @ as text, not as a file", () => {
  const w = setUp();
  const r = w.run(CF_API, ["POST", "/zones", "@/etc/passwd"]);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(w.curlBodies(), ["@/etc/passwd"]);
});

test("exits 2 on wrong arguments", () => {
  const w = setUp();
  assert.equal(w.run(CF_API, ["GET"]).status, 2);
});

test("--forget clears the cache", () => {
  const w = setUp();
  w.cache(GOOD);
  const r = w.run(CF_API, ["--forget"]);
  assert.equal(r.status, 0);
  assert.equal(w.cached(), null);
});

test("{account} comes from CF_ACCOUNT_ID first", () => {
  const w = setUp();
  const r = w.run(CF_API, ["GET", "/accounts/{account}/workers/scripts"], {
    env: { CF_ACCOUNT_ID: ACCOUNT },
  });
  assert.equal(r.status, 0, r.stderr);
  assert.match(w.curlCalls()[0], new RegExp(`/accounts/${ACCOUNT}/workers/`));
});

test("{account} comes from the nearest Wrangler config", () => {
  const w = setUp();
  w.file(
    join(w.cwd, "wrangler.jsonc"),
    `{\n  // comment\n  "account_id": "${ACCOUNT}",\n  "name": "x"\n}\n`,
  );
  const sub = join(w.cwd, "src", "deep");
  w.file(join(sub, ".keep"), "");
  const r = w.run(CF_API, ["GET", "/accounts/{account}/d1/database"], {
    cwd: sub,
  });
  assert.equal(r.status, 0, r.stderr);
  assert.match(w.curlCalls()[0], new RegExp(`/accounts/${ACCOUNT}/d1/`));
});

test("{account} reads account_id from wrangler.toml", () => {
  const w = setUp();
  w.file(join(w.cwd, "wrangler.toml"), `account_id = "${ACCOUNT}"\n`);
  const r = w.run(CF_API, ["GET", "/accounts/{account}/d1/database"]);
  assert.equal(r.status, 0, r.stderr);
  assert.match(w.curlCalls()[0], new RegExp(`/accounts/${ACCOUNT}/d1/`));
});

test("{account} falls back to the only account the token reaches", () => {
  const w = setUp();
  w.replies(`GET ${API}/accounts`, 200, {
    success: true,
    result: [{ id: ACCOUNT }],
  });
  const r = w.run(CF_API, ["GET", "/accounts/{account}/access/apps"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(w.curlCalls().length, 2);
  assert.match(w.curlCalls()[1], new RegExp(`/accounts/${ACCOUNT}/access/`));
});

test("retries a rejected cached token when it looks up {account}", () => {
  const w = setUp();
  w.cache(STALE);
  w.replies(`GET ${API}/accounts`, 200, {
    success: true,
    result: [{ id: ACCOUNT }],
  });
  const r = w.run(CF_API, ["GET", "/accounts/{account}/access/apps"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(w.cached(), GOOD);
  assert.deepEqual(
    w.curlCalls().map((c) => c.split(" ").slice(1).join(" ")),
    [
      `${API}/accounts ${STALE}`,
      `${API}/accounts ${GOOD}`,
      `${API}/accounts/${ACCOUNT}/access/apps ${GOOD}`,
    ],
  );
});

test("prints Cloudflare's answer when a fresh token cannot look up {account}", () => {
  const w = setUp();
  w.acceptsTokens(); // Cloudflare rejects every token.
  const r = w.run(CF_API, ["GET", "/accounts/{account}/access/apps"]);
  assert.equal(r.status, 1);
  assert.equal(w.curlCalls().length, 1);
  assert.match(JSON.parse(r.stdout).errors[0].message, /Authentication/);
});

test("exits 7 when curl cannot reach Cloudflare", () => {
  const w = setUp();
  w.curlFails();
  const r = w.run(CF_API, ["GET", "/zones"]);
  assert.equal(r.status, 7);
  assert.match(r.stderr, /could not reach api\.cloudflare\.com/);
});

test("exits 5 when the token reaches several accounts", () => {
  const w = setUp();
  w.replies(`GET ${API}/accounts`, 200, {
    success: true,
    result: [{ id: ACCOUNT }, { id: "f".repeat(32) }],
  });
  const r = w.run(CF_API, ["GET", "/accounts/{account}/access/apps"]);
  assert.equal(r.status, 5);
  assert.match(r.stderr, /reaches 2 accounts.*CF_ACCOUNT_ID/);
});
