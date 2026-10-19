// Drives skills/chrome/scripts/connect as a subprocess, the way the chrome
// skill runs it with the session scratchpad. connect picks the mode, starts or
// reaches Chrome, and prints key=value lines: mode=, root=, prefix=, and in
// scratch mode port= and profile=.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { CHROME, world } from "./helpers.mjs";

const SIDECAR =
  '{\n  "cdp": "10082",\n  "chromeProfile": "people-matcher"\n}\n';

function scratchpad(w) {
  const dir = join(w.home, "session", "scratchpad");
  mkdirSync(dir, { recursive: true });
  return dir;
}

// Makes the directory, and its parents.
function dir(...parts) {
  const path = join(...parts);
  mkdirSync(path, { recursive: true });
  return path;
}

function gitInit(path) {
  spawnSync("git", ["init", "-q", path]);
}

// The key=value lines connect printed, as an object.
function output(r) {
  return Object.fromEntries(
    r.stdout
      .split("\n")
      .filter(Boolean)
      .map((line) => {
        const at = line.indexOf("=");
        return [line.slice(0, at), line.slice(at + 1)];
      }),
  );
}

test("on the Mac with agent-browser.json, starts the repo's persistent Chrome", () => {
  const w = world();
  w.sidecar(SIDECAR);
  w.chromeStartsOnOpen();
  const r = w.run("connect", [scratchpad(w)]);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(output(r), {
    mode: "persistent",
    root: w.cwd,
    prefix: `agent-browser --config ${w.cwd}/agent-browser.json`,
  });
  assert.ok(w.isUp(10082));
});

test("on the Mac without agent-browser.json, starts a scratch Chrome", () => {
  const w = world();
  const pad = scratchpad(w);
  w.chromeStartsOnOpen();
  const r = w.run("connect", [pad]);
  assert.equal(r.status, 0, r.stderr);
  const out = output(r);
  assert.match(out.profile, new RegExp(`^${RegExp.escape(pad)}/chrome-`));
  assert.deepEqual(out, {
    mode: "scratch",
    root: w.cwd,
    prefix: "agent-browser --cdp 9300",
    port: "9300",
    profile: out.profile,
  });
  assert.ok(w.isUp(9300));
});

test("finds agent-browser.json above a nested clone's git root", () => {
  const w = world();
  w.sidecar(SIDECAR);
  const clone = dir(w.cwd, "clones", "api");
  gitInit(clone);
  w.chromeStartsOnOpen();
  const r = w.run("connect", [scratchpad(w)], {}, { cwd: dir(clone, "src") });
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).mode, "persistent");
  assert.equal(output(r).root, w.cwd);
});

test("without agent-browser.json, takes the git root as the repo root", () => {
  const w = world();
  gitInit(w.cwd);
  w.chromeStartsOnOpen();
  const r = w.run("connect", [scratchpad(w)], {}, { cwd: dir(w.cwd, "src") });
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).mode, "scratch");
  assert.equal(output(r).root, w.cwd);
});

for (const [what, packageJson, binary] of [
  [
    "dependencies",
    { dependencies: { "agent-browser": "0.39.0" } },
    "pnpm exec agent-browser",
  ],
  [
    "devDependencies",
    { devDependencies: { "agent-browser": "^0.39.0" } },
    "pnpm exec agent-browser",
  ],
  [
    "only peerDependencies",
    { peerDependencies: { "agent-browser": "*" } },
    "agent-browser",
  ],
  [
    "only a script of that name",
    { scripts: { "agent-browser": "agent-browser open" } },
    "agent-browser",
  ],
  ["no agent-browser", { dependencies: { react: "19.0.0" } }, "agent-browser"],
]) {
  test(`runs ${binary} when package.json lists ${what}`, () => {
    const w = world();
    w.sidecar(SIDECAR);
    writeFileSync(join(w.cwd, "package.json"), JSON.stringify(packageJson));
    w.chromeStartsOnOpen();
    const r = w.run("connect", [scratchpad(w)]);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(
      output(r).prefix,
      `${binary} --config ${w.cwd}/agent-browser.json`,
    );
  });
}

// The two ways a session counts as the container.
const CONTAINERS = [
  ["in the container", { STUB_UNAME: "Linux" }],
  [
    "on the Mac with AGENT_BROWSER_CDP set",
    { AGENT_BROWSER_CDP: "http://host.docker.internal:10082" },
  ],
];

for (const [where, env] of CONTAINERS) {
  test(`${where} without agent-browser.json, stops and asks for /browser:setup on the Mac`, () => {
    const w = world();
    w.chromeStartsOnOpen();
    const r = w.run("connect", [scratchpad(w)], env);
    assert.equal(r.status, 3);
    assert.match(r.stderr, /\/browser:setup/);
    assert.match(r.stderr, /Mac/);
    assert.equal(r.stdout, "");
    assert.deepEqual(w.openCalls(), []);
  });
}

for (const [where, env] of CONTAINERS) {
  test(`${where} with agent-browser.json, reaches the Mac's Chrome`, () => {
    const w = world();
    w.sidecar(SIDECAR);
    w.macChromeAnswers();
    const r = w.run("connect", [scratchpad(w)], {
      AGENT_BROWSER_CDP: "http://host.docker.internal:10082",
      ...env,
    });
    assert.equal(r.status, 0, r.stderr);
    // AGENT_BROWSER_CDP overrides the port in agent-browser.json.
    assert.deepEqual(output(r), {
      mode: "remote",
      root: w.cwd,
      prefix: `agent-browser --config ${w.cwd}/agent-browser.json`,
    });
    assert.deepEqual(w.curlCalls(), [
      "-sf --max-time 1 http://host.docker.internal:10082/json/version",
    ]);
    assert.deepEqual(w.openCalls(), []);
  });
}

for (const [what, env] of [
  ["empty", { AGENT_BROWSER_CDP: "" }],
  ["unset", {}],
]) {
  test(`in the container with AGENT_BROWSER_CDP ${what}, stops: the Mac's address is unknown`, () => {
    const w = world();
    w.sidecar(SIDECAR);
    const r = w.run("connect", [scratchpad(w)], {
      STUB_UNAME: "Linux",
      ...env,
    });
    assert.equal(r.status, 4);
    assert.match(r.stderr, /AGENT_BROWSER_CDP/);
    assert.match(r.stderr, /address/);
    assert.equal(r.stdout, "");
    assert.deepEqual(w.curlCalls(), []);
  });
}

test("in the container when the Mac's Chrome does not answer, stops and asks for mise run browser:start", () => {
  const w = world();
  w.sidecar(SIDECAR);
  const r = w.run("connect", [scratchpad(w)], {
    STUB_UNAME: "Linux",
    AGENT_BROWSER_CDP: "http://host.docker.internal:10082",
  });
  assert.equal(r.status, 5);
  assert.match(r.stderr, /mise run browser:start/);
  assert.match(r.stderr, /http:\/\/host\.docker\.internal:10082/);
  assert.equal(r.stdout, "");
  assert.deepEqual(w.openCalls(), []);
});

test("on the Mac when another profile holds the port, stops with browser-start's message", () => {
  const w = world();
  w.sidecar(SIDECAR);
  w.portUp(10082);
  w.psLists(
    `${CHROME} --remote-debugging-port=10082 --user-data-dir=${w.home}/.agent-browser/profiles/givingpath`,
  );
  const r = w.run("connect", [scratchpad(w)]);
  assert.equal(r.status, 6);
  assert.match(r.stderr, /profiles\/givingpath/);
  assert.match(r.stderr, /profiles\/people-matcher/);
  assert.equal(r.stdout, "");
  assert.deepEqual(w.openCalls(), []);
});

test("on the Mac when the scratch Chrome does not start, stops with scratch-chrome's message", () => {
  const w = world();
  const r = w.run("connect", [scratchpad(w)], { CHROME_WAIT_SECONDS: "1" });
  assert.equal(r.status, 7);
  assert.match(r.stderr, /did not answer on port 9300/);
  assert.equal(r.stdout, "");
});

test("quotes a repo root with a space for the shell", () => {
  const w = world();
  const root = dir(w.cwd, "my repo");
  writeFileSync(join(root, "agent-browser.json"), SIDECAR);
  w.chromeStartsOnOpen();
  const r = w.run("connect", [scratchpad(w)], {}, { cwd: root });
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).root, root);
  assert.equal(
    output(r).prefix,
    `agent-browser --config ${w.cwd}/my\\ repo/agent-browser.json`,
  );
});

test("takes exactly one argument, the scratchpad", () => {
  const w = world();
  const r = w.run("connect");
  assert.equal(r.status, 2);
  assert.match(r.stderr, /usage/);
  assert.deepEqual(w.openCalls(), []);
});
