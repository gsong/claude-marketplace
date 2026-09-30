// Drives hooks/promote.sh as a subprocess. It is a Stop hook: it stays quiet
// almost always, and blocks the stop only when a correction pattern has
// recurred enough to be worth a rule.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const PLUGIN = join(dirname(fileURLToPath(import.meta.url)), "..");
const PROMOTE = join(PLUGIN, "hooks", "promote.sh");
const DEFAULT_RULES = join(PLUGIN, "defaults", "rules");
const FIXTURE_RULES = mkdtempSync(join(tmpdir(), "wl-prom-rules-"));

// A jq reached through a mise shim reads its trust list from HOME, so it
// fails under the stand-in HOME some tests use. Those runs get a directory
// first on PATH that holds only the first jq on PATH that is not a shim.
const JQ_DIR = (() => {
  for (const dir of (process.env.PATH ?? "").split(":")) {
    if (!dir || dir.includes("/mise/shims")) continue;
    const jq = join(dir, "jq");
    if (!existsSync(jq)) continue;
    const bin = mkdtempSync(join(tmpdir(), "wl-bin-"));
    symlinkSync(jq, join(bin, "jq"));
    return bin;
  }
  return null;
})();

// Any WRITING_LINE_* the caller has set is dropped, so the state directory is
// always the one the test made. Passing rules as null leaves
// WRITING_LINE_RULES unset, and the rules then resolve through HOME, which
// such a test points at a directory it controls.
function hookEnv(dir, { rules = FIXTURE_RULES, home } = {}) {
  const env = { ...process.env, CLAUDE_PLUGIN_ROOT: PLUGIN };
  for (const key of Object.keys(env)) {
    if (key.startsWith("WRITING_LINE_")) delete env[key];
  }
  env.WRITING_LINE_STATE = dir;
  if (rules !== null) env.WRITING_LINE_RULES = rules;
  if (home !== undefined) {
    env.HOME = home;
    if (JQ_DIR) env.PATH = `${JQ_DIR}:${env.PATH}`;
  }
  return env;
}

let turn = 0;
function correction(reason, { profile = "technical", promptId } = {}) {
  return {
    timestamp: "2026-08-27T10:00:00Z",
    session_id: "s1",
    prompt_id: promptId ?? `turn-${++turn}`,
    profile,
    file: `/w/ai-swap/drafts/${profile}/d.md`,
    reason,
    original: "before",
    rewrite: "after",
  };
}

function state(corrections) {
  const dir = mkdtempSync(join(tmpdir(), "wl-prom-"));
  writeFileSync(
    join(dir, "corrections.jsonl"),
    `${corrections.map((c) => JSON.stringify(c)).join("\n")}\n`,
  );
  return dir;
}

function promote(dir, { stopHookActive = false, rules, home } = {}) {
  const result = spawnSync(PROMOTE, {
    input: JSON.stringify({
      hook_event_name: "Stop",
      stop_hook_active: stopHookActive,
      session_id: "s1",
    }),
    encoding: "utf-8",
    env: hookEnv(dir, { rules, home }),
  });
  assert.equal(result.error, undefined, `could not run ${PROMOTE}`);
  assert.equal(
    result.status,
    0,
    `promote exited ${result.status}: ${result.stderr}`,
  );
  if (result.stdout.trim() === "") return null;
  return JSON.parse(result.stdout);
}

const HEDGING = [
  correction("stop hedging, say it plainly"),
  correction("stop hedging in the second paragraph"),
  correction("you are hedging again, drop it"),
];

// Silence is the normal case. A hook that speaks on every turn gets ignored.
test("an empty log says nothing", () => {
  assert.equal(promote(state([])), null);
});

test("two corrections are not yet a pattern", () => {
  assert.equal(promote(state(HEDGING.slice(0, 2))), null);
});

test("unrelated corrections never cluster", () => {
  const log = state([
    correction("the latency is 400ms, not 4 seconds"),
    correction("her title is staff engineer"),
    correction("the release shipped in June"),
  ]);
  assert.equal(promote(log), null);
});

test("three corrections on one pattern block the stop", () => {
  const out = promote(state(HEDGING));
  assert.ok(out, "expected the hook to speak");
  assert.equal(out.decision, "block");
  assert.match(out.reason, /hedging/i);
  assert.match(out.reason, /technical/);
  assert.match(out.reason, /AskUserQuestion/);
});

// Voice is per profile. A Slack habit is not a docs rule, and mixing them
// produces a cluster that means nothing.
test("a pattern split across profiles does not cluster", () => {
  const log = state([
    correction("stop hedging here", { profile: "technical" }),
    correction("stop hedging here", { profile: "mixed" }),
    correction("stop hedging here", { profile: "comms" }),
  ]);
  assert.equal(promote(log), null);
});

// Three edits answering one instruction are one correction, not three.
test("edits sharing a prompt id count once", () => {
  const log = state([
    correction("stop hedging", { promptId: "same-turn" }),
    correction("stop hedging", { promptId: "same-turn" }),
    correction("stop hedging", { promptId: "same-turn" }),
  ]);
  assert.equal(promote(log), null);
});

// A turn can carry two complaints. Marking the whole turn as spent means the
// second pattern can never be raised, however often it recurs.
test("a second pattern in the same turns can still surface", () => {
  const dir = state([
    correction("stop hedging, the dashes are everywhere"),
    correction("hedging again, and dashes in line two"),
    correction("no hedging, fewer dashes please"),
  ]);
  const first = promote(dir);
  assert.ok(first, "expected a first pattern");
  const second = promote(dir);
  assert.ok(second, "the second pattern was consumed with the first");

  const words = [first, second].map(
    (r) => (r.reason.match(/in common is "([^"]+)"/) ?? [])[1],
  );
  assert.deepEqual(words.slice().sort(), ["dash", "hedg"]);
  assert.equal(promote(dir), null, "a third run must be quiet");
});

// Asking twice about the same pattern is worse than never asking.
test("a surfaced pattern does not come back", () => {
  const dir = state(HEDGING);
  assert.ok(promote(dir), "expected the first run to speak");
  assert.equal(promote(dir), null, "the second run repeated itself");
  assert.equal(existsSync(join(dir, "surfaced.txt")), true);
});

// The Stop hook fires again after it blocks. Without this guard it loops.
test("stop_hook_active silences the hook", () => {
  assert.equal(promote(state(HEDGING), { stopHookActive: true }), null);
});

test("the reason quotes the corrections it is built from", () => {
  const out = promote(state(HEDGING));
  assert.match(out.reason, /say it plainly/);
});

// Corrections with no reason carry no pattern. They come from served sessions
// where the transcript was unavailable.
test("empty reasons never cluster", () => {
  const log = state([correction(""), correction(""), correction("")]);
  assert.equal(promote(log), null);
});

test("a missing log file says nothing", () => {
  const dir = mkdtempSync(join(tmpdir(), "wl-prom-empty-"));
  assert.equal(promote(dir), null);
});

// The routing choices are the whole point of the prompt. All three must be
// offered, or the user cannot answer.
test("the reason offers all three routes", () => {
  const { reason } = promote(state(HEDGING));
  assert.match(reason, /voice rule/i);
  assert.match(reason, /reference/i);
  assert.match(reason, /discard/i);
});

// The rule goes where the gate will read it: the resolved rules directory.
function mentions(reason, path) {
  assert.ok(reason.includes(path), `expected ${path} in: ${reason}`);
}

test("the reason names the resolved rules directory", () => {
  const { reason } = promote(state(HEDGING));
  mentions(reason, join(FIXTURE_RULES, "technical.md"));
  mentions(reason, join(FIXTURE_RULES, "common.md"));
  assert.doesNotMatch(reason, /skills\/writing-line/);
  assert.doesNotMatch(reason, /copying/);
});

test("the reason names the user directory when it exists", () => {
  const home = mkdtempSync(join(tmpdir(), "wl-prom-home-"));
  const user = join(home, ".claude", "writing-line", "rules");
  mkdirSync(user, { recursive: true });
  const { reason } = promote(state(HEDGING), { rules: null, home });
  mentions(reason, join(user, "technical.md"));
  assert.doesNotMatch(reason, /copying/);
});

// A plugin update replaces the shipped defaults, and a rule appended there
// with them. The user directory replaces the defaults whole, so it has to
// start as a full copy or every other rule drops out.
test("with only the defaults in use, the rule goes to a seeded user directory", () => {
  const home = mkdtempSync(join(tmpdir(), "wl-prom-home-"));
  const { reason } = promote(state(HEDGING), { rules: null, home });
  mentions(
    reason,
    join(home, ".claude", "writing-line", "rules", "technical.md"),
  );
  assert.match(reason, /copying every file from\n\s+/);
  mentions(reason, `${DEFAULT_RULES}\n`);
  assert.ok(
    !reason.includes(join(DEFAULT_RULES, "technical.md")),
    "the rule was pointed at the plugin defaults",
  );
});
