// Drives skills/chrome/scripts/ports as a subprocess. The setup skill runs
// `ports claim <name>` on the Mac for a new repo. It prints a port no other
// repo uses, and records it in the registry, ~/.agent-browser/ports.

import assert from "node:assert/strict";
import { existsSync, rmdirSync } from "node:fs";
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

test("claim skips a port where the probe times out", () => {
  const w = world();
  // A program that holds the port but never replies.
  w.portTimesOut(10100);
  const r = w.run("ports", ["claim", "people-matcher"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout, "10101\n");
});

test("claim probes the port's root, which any program on it answers", () => {
  const w = world();
  w.portUp(10100);
  const r = w.run("ports", ["claim", "people-matcher"]);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(w.curlCalls(), [
    "-s --max-time 1 http://127.0.0.1:10100/",
    "-s --max-time 1 http://127.0.0.1:10101/",
  ]);
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

test("two claims at once get different ports, and both are recorded", async () => {
  const w = world();
  // Both runs read the empty registry before either probe ends, unless one
  // waits for the other.
  w.probesTake(0.5);
  const [a, b] = await w.runTogether(
    ["ports", ["claim", "people-matcher"]],
    ["ports", ["claim", "givingpath"]],
  );
  assert.equal(a.status, 0, a.stderr);
  assert.equal(b.status, 0, b.stderr);
  assert.deepEqual([a.stdout, b.stdout].sort(), ["10100\n", "10101\n"]);
  assert.deepEqual(
    w.registry().sort(),
    [
      `${a.stdout.trim()} people-matcher`,
      `${b.stdout.trim()} givingpath`,
    ].sort(),
  );
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

test("claim refuses to run on the Mac when AGENT_BROWSER_CDP is set", () => {
  const w = world();
  const r = w.run("ports", ["claim", "people-matcher"], {
    AGENT_BROWSER_CDP: "http://host.docker.internal:10082",
  });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /AGENT_BROWSER_CDP/);
  assert.deepEqual(w.registry(), []);
});

test("records made at once all reach the registry", async () => {
  const w = world();
  w.registryHolds("10100 givingpath");
  // record calls no stand-in, so nothing can slow it down. Enough runs at
  // once overlap without a lock.
  const names = Array.from({ length: 10 }, (_, i) => `repo-${i}`);
  const results = await w.runTogether(
    ...names.map((name, i) => ["ports", ["record", String(10101 + i), name]]),
  );
  for (const r of results) assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(
    w.registry().sort(),
    [
      "10100 givingpath",
      ...names.map((name, i) => `${10101 + i} ${name}`),
    ].sort(),
  );
});

for (const args of [
  ["claim", "people-matcher"],
  ["record", "10101", "people-matcher"],
]) {
  test(`${args[0]} gives up on a left-over lock, and says how to remove it`, () => {
    const w = world();
    w.registryHolds("10100 givingpath");
    w.leftOverLock();
    const r = w.run("ports", args, { PORTS_LOCK_WAIT_SECONDS: "1" });
    assert.equal(r.status, 1);
    assert.equal(r.stdout, "");
    assert.match(r.stderr, /stale/);
    assert.ok(r.stderr.includes(`rmdir ${w.lockDir}`), r.stderr);
    assert.deepEqual(w.registry(), ["10100 givingpath"]);
    // The lock may belong to a live run, so this run leaves it alone.
    assert.ok(existsSync(w.lockDir));
  });
}

test("a run leaves no lock behind, whether it succeeds or fails", () => {
  const w = world();
  const taken = [];
  for (let port = 10100; port <= 10199; port++) taken.push(`${port} r${port}`);
  const runs = [
    [["claim", "people-matcher"], 0],
    [["record", "10082", "dlcc"], 0],
    // Fails while it holds the lock: every port is taken.
    [["claim", "givingpath"], 1, () => w.registryHolds(...taken)],
    [["claim", "two words"], 1],
    [["record", "10083", "a/b"], 1],
  ];
  for (const [args, status, before] of runs) {
    before?.();
    const r = w.run("ports", args);
    assert.equal(r.status, status, `${args.join(" ")}: ${r.stderr}`);
    assert.ok(!existsSync(w.lockDir), `${args.join(" ")} left ${w.lockDir}`);
  }
});

test("a run waits for another run's lock, then goes ahead", async () => {
  const w = world();
  w.leftOverLock();
  const running = w.runTogether(["ports", ["record", "10100", "givingpath"]]);
  setTimeout(() => rmdirSync(w.lockDir), 500);
  const [r] = await running;
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(w.registry(), ["10100 givingpath"]);
});
