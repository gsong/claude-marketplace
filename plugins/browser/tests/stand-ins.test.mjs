// Drives the stand-ins in helpers.mjs through a probe script. A script that
// calls curl or ps in a way no test set up must fail its test, and the
// failure must name the call.

import assert from "node:assert/strict";
import { chmodSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { world } from "./helpers.mjs";

// A script in the test's repo directory that runs one shell command.
function probe(w, command) {
  const path = join(w.cwd, "probe");
  writeFileSync(path, `#!/usr/bin/env bash\n${command}\n`);
  chmodSync(path, 0o755);
  return path;
}

for (const call of [
  "curl -s http://127.0.0.1:9300/",
  "curl -sf --max-time 1 http://127.0.0.1:9300/json/list",
  "curl -sf --max-time 5 http://127.0.0.1:9300/json/version",
  "curl -s --max-time 1 http://localhost:9300/",
]) {
  test(`fails the test on the unknown call ${call}`, () => {
    const w = world();
    assert.throws(() => w.run(probe(w, call)), {
      message: new RegExp(`unexpected call: ${RegExp.escape(call)}`),
    });
  });
}

test("accepts the probes the scripts make", () => {
  const w = world();
  const r = w.run(
    probe(
      w,
      [
        "curl -sf --max-time 1 http://127.0.0.1:9300/json/version",
        "curl -s --max-time 1 http://127.0.0.1:9300/",
      ].join(" || "),
    ),
  );
  assert.equal(r.status, 7);
});

for (const [what, setUp, call] of [
  [
    "PIDs from a list without them",
    (w) => w.psLists("Chrome"),
    "ps -axo pid=,command=",
  ],
  [
    "no PIDs from a list with them",
    (w) => w.psListsWithPids("1 Chrome"),
    "ps -axo command=",
  ],
  ["other flags", (w) => w.psLists("Chrome"), "ps -ax"],
  ["other flags of an empty list", () => {}, "ps aux"],
]) {
  test(`fails the test when ps asks for ${what}`, () => {
    const w = world();
    setUp(w);
    assert.throws(() => w.run(probe(w, call)), {
      message: new RegExp(`unexpected call: ${RegExp.escape(call)}`),
    });
  });
}

test("lists the processes in the columns the test set up", () => {
  const w = world();
  w.psListsWithPids("1 Chrome");
  const r = w.run(probe(w, "ps -axo pid=,command="));
  assert.equal(r.stdout, "1 Chrome\n");
});

test("lists no processes in any columns", () => {
  const w = world();
  const r = w.run(probe(w, "ps -axo pid=,command=; ps -axo command="));
  assert.equal(r.status, 0);
  assert.equal(r.stdout, "");
});
