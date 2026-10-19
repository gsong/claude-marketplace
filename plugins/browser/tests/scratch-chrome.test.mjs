// Drives skills/chrome/scripts/scratch-chrome as a subprocess. The chrome
// skill runs it on the Mac when the repo has no agent-browser.json: start
// opens Chrome on a throwaway profile inside the session scratchpad, and stop
// quits that Chrome and deletes the profile. stop must never delete anything
// else, above all a persistent profile under ~/.agent-browser/profiles.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readdirSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { join, resolve } from "node:path";
import { test } from "node:test";

import { CHROME, world } from "./helpers.mjs";

function scratchpad(w) {
  const dir = join(w.home, "session", "scratchpad");
  mkdirSync(dir, { recursive: true });
  return dir;
}

test("start refuses to run anywhere but macOS", () => {
  const w = world();
  const pad = scratchpad(w);
  const r = w.run("scratch-chrome", ["start", pad], { STUB_UNAME: "Linux" });
  assert.equal(r.status, 1);
  assert.deepEqual(readdirSync(pad), []);
  assert.deepEqual(w.openCalls(), []);
});

test("start refuses to run on the Mac when AGENT_BROWSER_CDP is set", () => {
  const w = world();
  const pad = scratchpad(w);
  w.chromeStartsOnOpen();
  const r = w.run("scratch-chrome", ["start", pad], {
    AGENT_BROWSER_CDP: "http://host.docker.internal:10082",
  });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /AGENT_BROWSER_CDP/);
  assert.deepEqual(readdirSync(pad), []);
  assert.deepEqual(w.openCalls(), []);
});

test("start opens Chrome on a new chrome-* profile in the scratchpad", () => {
  const w = world();
  const pad = scratchpad(w);
  w.chromeStartsOnOpen();
  w.portUp(9300); // taken, so start moves on to 9301
  const r = w.run("scratch-chrome", ["start", pad]);
  assert.equal(r.status, 0, r.stderr);
  const made = readdirSync(pad);
  assert.equal(made.length, 1);
  assert.match(made[0], /^chrome-/);
  const profile = join(pad, made[0]);
  assert.deepEqual(w.openCalls(), [
    [
      "-na",
      "Google Chrome",
      "--args",
      "--remote-debugging-port=9301",
      `--user-data-dir=${profile}`,
      "--no-first-run",
      "--no-default-browser-check",
      "about:blank",
    ],
  ]);
  assert.match(r.stdout, /^port=9301$/m);
  // A port is free unless Chrome's DevTools endpoint answers on it.
  assert.deepEqual(w.curlCalls(), [
    "-sf --max-time 1 http://127.0.0.1:9300/json/version",
    "-sf --max-time 1 http://127.0.0.1:9301/json/version",
    "-sf --max-time 1 http://127.0.0.1:9301/json/version",
  ]);
  assert.equal(r.stdout.match(/^profile=(.*)$/m)[1], profile);
});

test("start refuses a directory that is not a scratchpad", () => {
  const w = world();
  const r = w.run("scratch-chrome", ["start", w.cwd]);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /scratchpad/);
  assert.deepEqual(readdirSync(w.cwd), []);
  assert.deepEqual(w.openCalls(), []);
});

// A directory with a file in it, standing in for a profile full of logins.
function profileAt(dir) {
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "Cookies"), "logins");
  return dir;
}

function persistentProfile(w) {
  return profileAt(
    join(w.home, ".agent-browser", "profiles", "people-matcher"),
  );
}

// A real process for stop to quit, listed by ps as the scratch Chrome. The
// shell exits at once, so the OS reaps the orphaned sleep when it dies, as it
// would a Chrome. A child of this test would stay a zombie that kill -0 still
// finds, because spawnSync blocks the loop that reaps it.
function fakeChrome(w, profile) {
  const pid = Number(
    spawnSync("sh", ["-c", "sleep 60 >/dev/null 2>&1 & echo $!"], {
      encoding: "utf8",
    }).stdout,
  );
  w.psListsWithPids(
    `${pid} ${CHROME} --remote-debugging-port=9300 --user-data-dir=${profile} --no-first-run`,
  );
  return pid;
}

function alive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

test("stop quits the scratch Chrome and deletes its profile", () => {
  const w = world();
  const profile = profileAt(join(scratchpad(w), "chrome-abc123"));
  const chrome = fakeChrome(w, profile);
  const r = w.run("scratch-chrome", ["stop", profile]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(existsSync(profile), false);
  assert.equal(alive(chrome), false);
});

test("stop leaves a Chrome on another profile running", () => {
  const w = world();
  const pad = scratchpad(w);
  const profile = profileAt(join(pad, "chrome-abc123"));
  const other = fakeChrome(w, persistentProfile(w));
  const r = w.run("scratch-chrome", ["stop", profile]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(alive(other), true);
  process.kill(other);
});

for (const [what, target] of [
  ["a persistent profile", (w) => persistentProfile(w)],
  [
    "a chrome-* directory outside a scratchpad",
    (w) => profileAt(join(w.home, "elsewhere", "chrome-abc123")),
  ],
  [
    "a scratchpad directory not named chrome-*",
    (w) => profileAt(join(scratchpad(w), "notes")),
  ],
  ["the scratchpad itself", (w) => profileAt(scratchpad(w))],
  [
    "a scratchpad nested in the profiles directory",
    (w) =>
      profileAt(
        join(w.home, ".agent-browser", "profiles", "scratchpad", "chrome-x"),
      ),
  ],
  [
    "a relative path",
    (w) => {
      profileAt(join(w.cwd, "scratchpad", "chrome-x"));
      return "scratchpad/chrome-x";
    },
  ],
]) {
  test(`stop refuses ${what} and deletes nothing`, () => {
    const w = world();
    const path = target(w);
    const r = w.run("scratch-chrome", ["stop", path]);
    assert.equal(r.status, 1);
    assert.ok(existsSync(resolve(w.cwd, path, "Cookies")));
  });
}

test("stop refuses a chrome-* symlink to a persistent profile", () => {
  const w = world();
  const real = persistentProfile(w);
  const link = join(scratchpad(w), "chrome-link");
  symlinkSync(real, link);
  const r = w.run("scratch-chrome", ["stop", link]);
  assert.equal(r.status, 1);
  assert.ok(existsSync(join(real, "Cookies")));
});

test("stop refuses a path that climbs out of the scratchpad", () => {
  const w = world();
  const real = persistentProfile(w);
  const pad = scratchpad(w);
  profileAt(join(pad, "chrome-x"));
  const path = join(
    pad,
    "chrome-x",
    "..",
    "..",
    "..",
    ".agent-browser",
    "profiles",
    "people-matcher",
  );
  const r = w.run("scratch-chrome", ["stop", path]);
  assert.equal(r.status, 1);
  assert.ok(existsSync(join(real, "Cookies")));
});

test("start removes the profile when Chrome does not answer", () => {
  const w = world();
  const pad = scratchpad(w);
  const r = w.run("scratch-chrome", ["start", pad], {
    CHROME_WAIT_SECONDS: "1",
  });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /did not answer/);
  assert.deepEqual(readdirSync(pad), []);
});
