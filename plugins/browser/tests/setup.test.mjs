// Drives skills/chrome/scripts/setup as a subprocess, the way the setup skill
// runs it from inside a checkout. Setup checks everything first, then claims
// a port and writes agent-browser.json, the browser:start task in mise.toml,
// and the plugin entries in .claude/settings.json. It prints key=value lines,
// and stops with its own exit status for each case the skill handles.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { world } from "./helpers.mjs";

// A world whose repo directory is a git repo. Git reads no config from the
// machine running the tests, so their ignore rules stay out.
function repo() {
  const w = world();
  const env = {
    XDG_CONFIG_HOME: join(w.home, ".config"),
    GIT_CONFIG_NOSYSTEM: "1",
  };
  spawnSync("git", ["init", "-q", w.cwd], { env: { ...process.env, ...env } });
  const run = w.run;
  w.run = (script, args, more = {}, opts) =>
    run(script, args, { ...env, ...more }, opts);
  return w;
}

function setup(w, args = [], env = {}) {
  return w.run("setup", args, env);
}

// The key=value lines setup printed, as an object.
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

function read(w, file) {
  return readFileSync(join(w.cwd, file), "utf8");
}

function json(w, file) {
  return JSON.parse(read(w, file));
}

function write(w, file, text) {
  mkdirSync(join(w.cwd, file, ".."), { recursive: true });
  writeFileSync(join(w.cwd, file), text);
}

// Every file in the repo but .git, and the registry, as one object.
function snapshot(w) {
  const files = {};
  for (const entry of readdirSync(w.cwd, { recursive: true })) {
    if (entry === ".git" || entry.startsWith(".git/")) continue;
    const path = join(w.cwd, entry);
    try {
      files[entry] = readFileSync(path, "utf8");
    } catch {
      files[entry] = "<dir>";
    }
  }
  return { files, registry: w.registry() };
}

// Runs setup, and checks that it stopped with the status, said why, and
// changed no file and claimed no port.
function stops(w, status, message, args = [], env = {}) {
  const before = snapshot(w);
  const r = setup(w, args, env);
  assert.equal(r.status, status, r.stderr);
  assert.equal(r.stdout, "");
  assert.match(r.stderr, message);
  assert.deepEqual(snapshot(w), before);
  return r;
}

test("sets up a fresh repo", () => {
  const w = repo();
  const r = setup(w);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(output(r), {
    port: "10100",
    profile: "repo",
    agent_browser_json: "wrote",
    ignored: "no",
    mise_toml: "wrote",
    settings_json: "wrote",
  });
  assert.deepEqual(json(w, "agent-browser.json"), {
    cdp: "10100",
    contentBoundary: true,
    chromeProfile: "repo",
  });
  assert.deepEqual(w.registry(), ["10100 repo"]);
  assert.match(read(w, "mise.toml"), /^\[tasks\."browser:start"\]$/m);
  assert.match(read(w, "mise.toml"), /skills\/chrome\/scripts\/browser-start/);
  assert.deepEqual(json(w, ".claude/settings.json"), {
    extraKnownMarketplaces: {
      "gsong-marketplace": {
        source: { source: "github", repo: "gsong/claude-marketplace" },
        autoUpdate: true,
      },
    },
    enabledPlugins: { "browser@gsong-marketplace": true },
  });
  assert.ok(!existsSync(join(w.cwd, ".gitignore")));
});

test("stops anywhere but macOS", () => {
  const w = repo();
  stops(w, 3, /Mac/, [], { STUB_UNAME: "Linux" });
});

test("stops on the Mac when AGENT_BROWSER_CDP is set", () => {
  const w = repo();
  stops(w, 3, /AGENT_BROWSER_CDP/, [], {
    AGENT_BROWSER_CDP: "http://host.docker.internal:10082",
  });
});

test("stops outside a git repo", () => {
  const w = world();
  stops(w, 4, /git repo/);
});

test("stops when jq is missing", () => {
  const w = repo();
  stops(w, 5, /jq/, [], { PATH: w.pathWithout("jq") });
});

test("stops when mise is missing", () => {
  const w = repo();
  stops(w, 6, /mise is missing/, [], { PATH: w.pathWithout("mise") });
});

test("stops with mise's message when mise fails", () => {
  const w = repo();
  write(w, "mise.toml", '[env]\nFOO = "bar"\n');
  w.miseFails("mise ERROR Config files in mise.toml are not trusted.");
  stops(w, 6, /not trusted/);
});

for (const name of ["People-Matcher", "a/b", "..", "two words", ""]) {
  test(`stops on --name ${JSON.stringify(name)}`, () => {
    const w = repo();
    stops(w, 7, /lowercase/, ["--name", name]);
  });
}

test("asks when the registry lists the name", () => {
  const w = repo();
  w.registryHolds("10100 repo");
  stops(w, 8, /--share/);
});

test("asks when the profile directory exists", () => {
  const w = repo();
  mkdirSync(join(w.home, ".agent-browser", "profiles", "repo"), {
    recursive: true,
  });
  const r = stops(w, 8, /worktree/);
  assert.match(r.stderr, /--name/);
});

test("--share takes the name in use and its port", () => {
  const w = repo();
  w.registryHolds("10100 givingpath", "10101 repo");
  const r = setup(w, ["--share"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).port, "10101");
  assert.equal(output(r).profile, "repo");
  assert.deepEqual(w.registry(), ["10100 givingpath", "10101 repo"]);
});

test("--name takes another name", () => {
  const w = repo();
  w.registryHolds("10100 repo");
  const r = setup(w, ["--name", "repo-2"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).port, "10101");
  assert.equal(json(w, "agent-browser.json").chromeProfile, "repo-2");
  assert.deepEqual(w.registry(), ["10100 repo", "10101 repo-2"]);
});

test("--name asks again when that name is in use too", () => {
  const w = repo();
  w.registryHolds("10100 repo", "10101 repo-2");
  stops(w, 8, /"repo-2" is in use/, ["--name", "repo-2"]);
});

test("keeps an existing agent-browser.json, and records its port", () => {
  const w = repo();
  const sidecar = '{"cdp":10082,"chromeProfile":"people-matcher"}\n';
  write(w, "agent-browser.json", sidecar);
  // Its own name in use is no question: the file already holds it.
  w.registryHolds("10100 givingpath");
  mkdirSync(join(w.home, ".agent-browser", "profiles", "people-matcher"), {
    recursive: true,
  });
  const r = setup(w, ["--name", "ignored-name"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).port, "10082");
  assert.equal(output(r).profile, "people-matcher");
  assert.equal(output(r).agent_browser_json, "kept");
  assert.equal(read(w, "agent-browser.json"), sidecar);
  assert.deepEqual(w.registry(), ["10100 givingpath", "10082 people-matcher"]);
});

for (const [what, sidecar, message] of [
  ["no cdp port", '{ "chromeProfile": "repo" }', /cdp/],
  [
    "a chromeProfile with capitals",
    '{ "cdp": "10082", "chromeProfile": "Repo" }',
    /chromeProfile/,
  ],
  [
    "a chromeProfile path",
    '{ "cdp": "10082", "chromeProfile": "../x" }',
    /chromeProfile/,
  ],
  ["text that is not JSON", "cdp=10082\n", /JSON/],
]) {
  test(`stops when agent-browser.json has ${what}`, () => {
    const w = repo();
    write(w, "agent-browser.json", sidecar);
    stops(w, 9, message);
  });
}

test("stops when the registry gives agent-browser.json's port to another profile", () => {
  const w = repo();
  write(w, "agent-browser.json", '{ "cdp": "10082", "chromeProfile": "repo" }');
  w.registryHolds("10082 givingpath");
  stops(w, 9, /givingpath/);
});

test("asks when git ignores agent-browser.json, and names the rule", () => {
  const w = repo();
  write(w, ".gitignore", "node_modules\nagent-browser.json\n");
  stops(w, 10, /\.gitignore:2:agent-browser\.json/);
});

test("--unignore deletes a .gitignore line that names only agent-browser.json", () => {
  const w = repo();
  write(w, ".gitignore", "node_modules\n/agent-browser.json\ndist\n");
  const r = setup(w, ["--unignore"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).ignored, "no");
  assert.match(output(r).unignored, /deleted/);
  assert.equal(read(w, ".gitignore"), "node_modules\ndist\n");
});

test("--unignore appends a negation for a wider rule", () => {
  const w = repo();
  write(w, ".gitignore", "*.json");
  const r = setup(w, ["--unignore"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).ignored, "no");
  assert.match(output(r).unignored, /appended/);
  assert.equal(read(w, ".gitignore"), "*.json\n!/agent-browser.json\n");
  const check = spawnSync("git", ["check-ignore", "-q", "agent-browser.json"], {
    cwd: w.cwd,
  });
  assert.equal(check.status, 1);
});

test("--unignore appends a negation for a rule outside the repo", () => {
  const w = repo();
  write(w, "../home/.config/git/ignore", "agent-browser.json\n");
  const r = setup(w, ["--unignore"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(read(w, ".gitignore"), "!/agent-browser.json\n");
  assert.equal(read(w, "../home/.config/git/ignore"), "agent-browser.json\n");
});

test("--keep-ignored keeps the rule, and says so", () => {
  const w = repo();
  write(w, ".gitignore", "agent-browser.json\n");
  const r = setup(w, ["--keep-ignored"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).ignored, "yes");
  assert.equal(read(w, ".gitignore"), "agent-browser.json\n");
  assert.ok(existsSync(join(w.cwd, "agent-browser.json")));
});

test("keeps a browser:start task that a .toml in the repo defines", () => {
  const w = repo();
  const toml = '[tasks."browser:start"]\nrun = "echo hi"\n';
  write(w, "mise.toml", toml);
  w.miseHasTask(join(w.cwd, "mise.toml"));
  const r = setup(w);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).mise_toml, "kept");
  assert.equal(read(w, "mise.toml"), toml);
});

test("appends the task when only a file outside the repo defines it", () => {
  const w = repo();
  write(w, "mise.toml", '[tools]\nnode = "24"');
  w.miseHasTask(join(w.home, ".config", "mise", "config.toml"));
  const r = setup(w);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).mise_toml, "merged");
  assert.match(
    read(w, "mise.toml"),
    /^\[tools\]\nnode = "24"\n\n\[tasks\."browser:start"\]\n/,
  );
});

test("asks when a file task defines browser:start", () => {
  const w = repo();
  write(w, "mise-tasks/browser/start", "#!/bin/sh\necho hi\n");
  w.miseHasTask(join(w.cwd, "mise-tasks", "browser", "start"), {
    fileTask: true,
  });
  stops(w, 11, /mise-tasks\/browser\/start/);
});

test("--replace-task deletes the file task and appends the block", () => {
  const w = repo();
  write(w, "mise-tasks/browser/start", "#!/bin/sh\necho hi\n");
  w.miseHasTask(join(w.cwd, "mise-tasks", "browser", "start"), {
    fileTask: true,
  });
  const r = setup(w, ["--replace-task"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).mise_toml, "wrote");
  assert.equal(output(r).deleted_task, "mise-tasks/browser/start");
  assert.ok(!existsSync(join(w.cwd, "mise-tasks", "browser", "start")));
  assert.match(read(w, "mise.toml"), /^\[tasks\."browser:start"\]$/m);
});

test("--keep-task keeps the file task, and appends nothing", () => {
  const w = repo();
  write(w, "mise-tasks/browser/start", "#!/bin/sh\necho hi\n");
  w.miseHasTask(join(w.cwd, "mise-tasks", "browser", "start"), {
    fileTask: true,
  });
  const r = setup(w, ["--keep-task"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).mise_toml, "kept");
  assert.ok(existsSync(join(w.cwd, "mise-tasks", "browser", "start")));
  assert.ok(!existsSync(join(w.cwd, "mise.toml")));
});

test("merges into .claude/settings.json, and keeps its other entries", () => {
  const w = repo();
  write(
    w,
    ".claude/settings.json",
    JSON.stringify({
      permissions: { allow: ["Bash(ls)"] },
      extraKnownMarketplaces: {
        other: { source: { source: "github", repo: "o/m" } },
        "gsong-marketplace": { source: { source: "directory", path: "/x" } },
      },
      enabledPlugins: { "x@other": true },
    }),
  );
  const r = setup(w);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).settings_json, "merged");
  assert.deepEqual(json(w, ".claude/settings.json"), {
    permissions: { allow: ["Bash(ls)"] },
    extraKnownMarketplaces: {
      other: { source: { source: "github", repo: "o/m" } },
      "gsong-marketplace": { source: { source: "directory", path: "/x" } },
    },
    enabledPlugins: { "x@other": true, "browser@gsong-marketplace": true },
  });
});

test("keeps a .claude/settings.json that already has the entries", () => {
  const w = repo();
  const settings =
    '{"extraKnownMarketplaces":{"gsong-marketplace":{"source":{"source":"github","repo":"gsong/claude-marketplace"}}},"enabledPlugins":{"browser@gsong-marketplace":true}}';
  write(w, ".claude/settings.json", settings);
  const r = setup(w);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).settings_json, "kept");
  assert.equal(read(w, ".claude/settings.json"), settings);
});

for (const [what, settings] of [
  ["text that is not JSON", "{"],
  ["an array", "[]"],
  ["a list of plugins", '{ "enabledPlugins": ["browser"] }'],
]) {
  test(`stops when .claude/settings.json is ${what}`, () => {
    const w = repo();
    write(w, ".claude/settings.json", settings);
    stops(w, 12, /settings\.json/);
  });
}

test("stops with ports' message when no port is free", () => {
  const w = repo();
  const taken = [];
  for (let port = 10100; port <= 10199; port++) taken.push(`${port} r${port}`);
  w.registryHolds(...taken);
  stops(w, 13, /10100-10199/);
});

test("names the profile after the main checkout, from a worktree", () => {
  const w = repo();
  const git = (...args) =>
    spawnSync("git", ["-c", "user.name=t", "-c", "user.email=t@t", ...args], {
      cwd: w.cwd,
    });
  git("commit", "-q", "--allow-empty", "-m", "first");
  const tree = join(w.cwd, "..", "Other Tree");
  git("worktree", "add", "-q", "-b", "other", tree);
  const r = w.run("setup", [], {}, { cwd: tree });
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).profile, "repo");
  assert.ok(existsSync(join(tree, "agent-browser.json")));
});

test("makes a valid name from any directory name", () => {
  const w = world();
  const dir = join(w.cwd, "..", "My Repo!! v2");
  spawnSync("git", ["init", "-q", dir]);
  const r = w.run("setup", [], {}, { cwd: dir });
  assert.equal(r.status, 0, r.stderr);
  assert.equal(output(r).profile, "my-repo-v2");
});

test("works from a subdirectory, at the repo root", () => {
  const w = repo();
  mkdirSync(join(w.cwd, "src"));
  const r = w.run("setup", [], {}, { cwd: join(w.cwd, "src") });
  assert.equal(r.status, 0, r.stderr);
  assert.ok(existsSync(join(w.cwd, "agent-browser.json")));
});

for (const args of [
  ["--share", "--name", "x"],
  ["--name"],
  ["--unignore", "--keep-ignored"],
  ["--replace-task", "--keep-task"],
  ["--force"],
]) {
  test(`refuses the arguments ${args.join(" ")}`, () => {
    const w = repo();
    stops(w, 2, /usage/, args);
  });
}

test("asks about a file task even when its name ends in .toml", () => {
  const w = repo();
  write(w, "mise-tasks/browser/start.toml", "#!/bin/sh\necho hi\n");
  w.miseHasTask(join(w.cwd, "mise-tasks", "browser", "start.toml"), {
    fileTask: true,
  });
  stops(w, 11, /mise-tasks\/browser\/start\.toml/);
});

test("--unignore also appends a negation when another rule still ignores the file", () => {
  const w = repo();
  // The repo's rule wins, so git names it first. The global rule shows only
  // once the repo's line is gone.
  write(w, "../home/.config/git/ignore", "agent-browser.json\n");
  write(w, ".gitignore", "agent-browser.json\n");
  const r = setup(w, ["--unignore"]);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(read(w, ".gitignore"), "!/agent-browser.json\n");
  const check = spawnSync("git", ["check-ignore", "-q", "agent-browser.json"], {
    cwd: w.cwd,
    env: { ...process.env, XDG_CONFIG_HOME: join(w.home, ".config") },
  });
  assert.equal(check.status, 1);
});

test("stops on a bad --name even when agent-browser.json exists", () => {
  const w = repo();
  write(w, "agent-browser.json", '{ "cdp": "10082", "chromeProfile": "repo" }');
  stops(w, 7, /lowercase/, ["--name", "Repo"]);
});

test("stops on a broken .claude/settings.json before it asks anything", () => {
  const w = repo();
  w.registryHolds("10100 repo");
  write(w, ".gitignore", "agent-browser.json\n");
  write(w, ".claude/settings.json", "{");
  stops(w, 12, /settings\.json/);
});
