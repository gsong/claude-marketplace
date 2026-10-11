// Drives skills/chrome/scripts/browser-start as a subprocess, the way a
// human's mise task or the chrome skill runs it, from a repo directory that
// holds agent-browser.json.

import assert from "node:assert/strict";
import { test } from "node:test";

import { CHROME, world } from "./helpers.mjs";

const SIDECAR =
  '{\n  "cdp": "10082",\n  "chromeProfile": "people-matcher"\n}\n';

test("refuses to run anywhere but macOS, and opens nothing", () => {
  const w = world();
  w.sidecar(SIDECAR);
  const r = w.run("browser-start", [], { STUB_UNAME: "Linux" });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /Mac/);
  assert.deepEqual(w.openCalls(), []);
});

test("opens Chrome on the sidecar's port and profile, then waits for it", () => {
  const w = world();
  w.sidecar(SIDECAR);
  w.chromeStartsOnOpen();
  const r = w.run("browser-start");
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(w.openCalls(), [
    [
      "-na",
      "Google Chrome",
      "--args",
      "--remote-debugging-port=10082",
      `--user-data-dir=${w.home}/.agent-browser/profiles/people-matcher`,
    ],
  ]);
  assert.match(r.stdout, /10082/);
});

test("fails when Chrome does not answer within the wait", () => {
  const w = world();
  w.sidecar(SIDECAR);
  const r = w.run("browser-start", [], { CHROME_WAIT_SECONDS: "1" });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /did not answer on port 10082/);
});

test("opens nothing when Chrome with this profile already answers", () => {
  const w = world();
  w.sidecar(SIDECAR);
  w.portUp(10082);
  w.psLists(
    `${CHROME} --remote-debugging-port=10082 --user-data-dir=${w.home}/.agent-browser/profiles/people-matcher`,
  );
  const r = w.run("browser-start");
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /already open/);
  assert.deepEqual(w.openCalls(), []);
});

test("names both profiles when another profile holds the port", () => {
  const w = world();
  w.sidecar(SIDECAR);
  w.portUp(10082);
  w.psLists(
    `${CHROME} --remote-debugging-port=10082 --user-data-dir=${w.home}/.agent-browser/profiles/givingpath`,
    // A renderer of that Chrome carries the flags too. Only the browser
    // process says which profile holds the port.
    `${CHROME} Helper (Renderer) --type=renderer --remote-debugging-port=10082 --user-data-dir=${w.home}/.agent-browser/profiles/people-matcher`,
  );
  const r = w.run("browser-start");
  assert.equal(r.status, 1);
  assert.match(r.stderr, /profiles\/givingpath/);
  assert.match(r.stderr, /profiles\/people-matcher/);
  assert.deepEqual(w.openCalls(), []);
});

test("does not mistake port 100820 for port 10082", () => {
  const w = world();
  w.sidecar(SIDECAR);
  w.portUp(10082);
  w.psLists(
    `${CHROME} --remote-debugging-port=100820 --user-data-dir=${w.home}/.agent-browser/profiles/people-matcher`,
  );
  const r = w.run("browser-start");
  assert.equal(r.status, 1);
  assert.match(r.stderr, /no Chrome/);
  assert.deepEqual(w.openCalls(), []);
});

test("stops when the repo has no agent-browser.json", () => {
  const w = world();
  w.chromeStartsOnOpen();
  const r = w.run("browser-start");
  assert.equal(r.status, 1);
  assert.match(r.stderr, /agent-browser\.json/);
  assert.deepEqual(w.openCalls(), []);
});

for (const [what, json, key] of [
  ["no cdp port", '{ "chromeProfile": "people-matcher" }', /cdp/],
  ["no chromeProfile", '{ "cdp": "10082" }', /chromeProfile/],
  [
    "a profile path",
    '{ "cdp": 10082, "chromeProfile": "../x" }',
    /chromeProfile/,
  ],
  [
    "a nested profile",
    '{ "cdp": 10082, "chromeProfile": "a/b" }',
    /chromeProfile/,
  ],
]) {
  test(`stops when agent-browser.json has ${what}`, () => {
    const w = world();
    w.sidecar(json);
    w.chromeStartsOnOpen();
    const r = w.run("browser-start");
    assert.equal(r.status, 1);
    assert.match(r.stderr, key);
    assert.deepEqual(w.openCalls(), []);
  });
}

test("reads a cdp port written as a number", () => {
  const w = world();
  w.sidecar('{ "cdp": 10082, "chromeProfile": "people-matcher" }');
  w.chromeStartsOnOpen();
  const r = w.run("browser-start");
  assert.equal(r.status, 0, r.stderr);
  assert.ok(w.isUp(10082));
});

test("says so when the Chrome on the port runs the default profile", () => {
  const w = world();
  w.sidecar(SIDECAR);
  w.portUp(10082);
  w.psLists(`${CHROME} --remote-debugging-port=10082 --no-first-run`);
  const r = w.run("browser-start");
  assert.equal(r.status, 1);
  assert.match(r.stderr, /default profile/);
  assert.doesNotMatch(r.stderr, /Applications/);
});
