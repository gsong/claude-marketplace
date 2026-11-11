import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { test } from "node:test";

import { GOOD, REF, SAVE_TOKEN, world } from "./helpers.mjs";

const VERIFY = "GET https://api.cloudflare.com/client/v4/user/tokens/verify";

function activeToken() {
  const w = world();
  w.acceptsTokens(GOOD);
  w.replies(VERIFY, 200, { success: true, result: { status: "active" } });
  return w;
}

function keyValues(stdout) {
  return Object.fromEntries(
    stdout
      .trim()
      .split("\n")
      .map((l) => l.split(/=(.*)/s).slice(0, 2)),
  );
}

test("saves an active token to 1Password and points cf-api at it", () => {
  const w = activeToken();
  const r = w.run(SAVE_TOKEN, ["--vault", "Private"], { input: `${GOOD}\n` });
  assert.equal(r.status, 0, r.stderr);
  const out = keyValues(r.stdout);
  assert.equal(out.token_ref, "op://Private/newitem456/credential");
  assert.equal(out.vault, "Private");
  assert.equal(out.replaced, undefined);
  assert.equal(w.readConfig(), `token_ref=${out.token_ref}\n`);

  const created = w.opCreated();
  assert.equal(created.vault, "Private");
  assert.equal(created.category, "API_CREDENTIAL");
  assert.equal(created.fields[0].value, GOOD);
});

test("keeps the token out of output and command lines", () => {
  const w = activeToken();
  const r = w.run(SAVE_TOKEN, ["--vault", "Private"], { input: GOOD });
  assert.equal(r.status, 0, r.stderr);
  assert.ok(!r.stdout.includes(GOOD) && !r.stderr.includes(GOOD));
  for (const call of w.opCalls()) assert.ok(!call.includes(GOOD), call);
});

test("writes the template only the user can read, and deletes it", () => {
  const w = activeToken();
  w.run(SAVE_TOKEN, ["--vault", "Private"], { input: GOOD });
  assert.equal(w.opTemplateMode(), "600");
  assert.equal(existsSync(w.opTemplatePath()), false);
});

test("reports the token it replaced and drops the Keychain cache", () => {
  const w = activeToken();
  w.config(`token_ref=${REF}\n`);
  w.cache("old_cached_token");
  const r = w.run(SAVE_TOKEN, ["--vault", "Private"], { input: GOOD });
  assert.equal(r.status, 0, r.stderr);
  assert.equal(keyValues(r.stdout).replaced, REF);
  assert.equal(w.cached(), null);
});

test("exits 4 and saves nothing when the token is not active", () => {
  const w = world(); // Cloudflare rejects every token.
  const r = w.run(SAVE_TOKEN, ["--vault", "Private"], { input: GOOD });
  assert.equal(r.status, 4);
  assert.equal(w.opCreated(), null);
  assert.equal(w.readConfig(), "");
});

test("exits 3 on stdin that is not a token", () => {
  const w = activeToken();
  const r = w.run(SAVE_TOKEN, ["--vault", "Private"], { input: "nope" });
  assert.equal(r.status, 3);
  assert.deepEqual(w.curlCalls(), []);
});

test("exits 5 and leaves the config alone when 1Password fails", () => {
  const w = activeToken();
  w.config(`token_ref=${REF}\n`);
  w.opCreateFails();
  const r = w.run(SAVE_TOKEN, ["--vault", "Nope"], { input: GOOD });
  assert.equal(r.status, 5);
  assert.equal(w.readConfig(), `token_ref=${REF}\n`);
  assert.equal(existsSync(w.opTemplatePath() || "/nonexistent"), false);
});

test("exits 2 without --vault", () => {
  const w = activeToken();
  assert.equal(w.run(SAVE_TOKEN, [], { input: GOOD }).status, 2);
});
