// Drives skills/chrome/scripts/ports as a subprocess. The setup skill runs
// `ports claim <profile>` on the Mac to give a new repo a CDP port that no
// other repo uses, and records it in ~/.agent-browser/ports.

import assert from "node:assert/strict";
import { test } from "node:test";

import { CHROME, world } from "./helpers.mjs";

test("claim picks the first port in the range and records it", () => {
  const w = world();
  const r = w.run("ports", ["claim", "people-matcher"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout, "10100\n");
  assert.deepEqual(w.registry(), ["10100 people-matcher"]);
});

test("claim skips ports the registry gives to other repos", () => {
  const w = world();
  w.registryHolds("10100 givingpath", "10101 dlcc");
  const r = w.run("ports", ["claim", "people-matcher"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout, "10102\n");
  assert.deepEqual(w.registry(), [
    "10100 givingpath",
    "10101 dlcc",
    "10102 people-matcher",
  ]);
});

test("claim skips ports a running Chrome holds, even when closed to probes", () => {
  const w = world();
  // A repo set up before the registry existed: only ps shows its port.
  w.psLists(
    `${CHROME} --remote-debugging-port=10100 --user-data-dir=${w.home}/.agent-browser/profiles/givingpath`,
    `${CHROME} --remote-debugging-port=101010 --user-data-dir=/elsewhere`,
  );
  const r = w.run("ports", ["claim", "people-matcher"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout, "10101\n");
});

test("claim skips ports something else answers on", () => {
  const w = world();
  w.portUp(10100);
  const r = w.run("ports", ["claim", "people-matcher"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout, "10101\n");
});

test("claim gives a profile the port it already has, and records nothing", () => {
  const w = world();
  w.registryHolds("10082 people-matcher", "10100 givingpath");
  // Its Chrome may be running: that is this profile's own port.
  w.portUp(10082);
  const r = w.run("ports", ["claim", "people-matcher"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout, "10082\n");
  assert.deepEqual(w.registry(), ["10082 people-matcher", "10100 givingpath"]);
});

test("claim fails and records nothing when the whole range is taken", () => {
  const w = world();
  const taken = [];
  for (let port = 10100; port <= 10199; port++) taken.push(`${port} r${port}`);
  w.registryHolds(...taken);
  const r = w.run("ports", ["claim", "people-matcher"]);
  assert.equal(r.status, 1);
  assert.equal(r.stdout, "");
  assert.match(r.stderr, /10100-10199/);
  assert.deepEqual(w.registry(), taken);
});

for (const name of ["", ".", "..", "a/b", "../x", "two words"]) {
  test(`claim refuses the profile name ${JSON.stringify(name)}`, () => {
    const w = world();
    const r = w.run("ports", ["claim", name]);
    assert.equal(r.status, 1);
    assert.match(r.stderr, /profile/);
    assert.deepEqual(w.registry(), []);
  });
}

test("claim refuses to run anywhere but macOS", () => {
  const w = world();
  const r = w.run("ports", ["claim", "people-matcher"], {
    STUB_UNAME: "Linux",
  });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /Mac/);
  assert.deepEqual(w.registry(), []);
});
