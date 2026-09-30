// Drives hooks/capture.sh as a subprocess. The hook has no stdout contract:
// it writes a JSONL line and a snapshot as a side effect. These tests read
// those files back.
//
// Each test gets its own state directory and its own fake transcript, so the
// real log at ~/.claude/state/writing-line/ is never touched.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  utimesSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { hookEnv } from "./helpers.mjs";

const PLUGIN = join(dirname(fileURLToPath(import.meta.url)), "..");
const CAPTURE = join(PLUGIN, "hooks", "capture.sh");

// A workspace holds one state directory, one draft and one transcript.
function workspace(profile = "technical") {
  const root = mkdtempSync(join(tmpdir(), "wl-cap-"));
  const state = join(root, "state");
  const dir = join(root, "ai-swap", "drafts", profile);
  mkdirSync(dir, { recursive: true });
  mkdirSync(state, { recursive: true });
  return {
    root,
    state,
    draft: join(dir, "draft.md"),
    transcript: join(root, "transcript.jsonl"),
  };
}

// Writes a transcript holding one genuine user prompt plus the noise that sits
// beside it: tool results, meta records and a prompt from an earlier turn.
function transcript(ws, promptId, text) {
  const records = [
    {
      type: "user",
      promptId: "an-earlier-turn",
      message: { content: "something else entirely" },
    },
    {
      type: "assistant",
      promptId,
      message: { content: [{ type: "text", text: "working on it" }] },
    },
    { type: "user", promptId, message: { content: text } },
    {
      type: "user",
      promptId,
      isMeta: true,
      message: { content: "injected context, not the user" },
    },
    {
      type: "user",
      promptId,
      toolUseResult: {},
      message: { content: [{ type: "tool_result", content: "output" }] },
    },
  ];
  writeFileSync(
    ws.transcript,
    `${records.map((r) => JSON.stringify(r)).join("\n")}\n`,
  );
  return ws.transcript;
}

function capture(
  ws,
  {
    body,
    promptId = "turn-1",
    transcriptPath = ws.transcript,
    tool = "Write",
  } = {},
) {
  if (body !== undefined) writeFileSync(ws.draft, body);
  const result = spawnSync(CAPTURE, {
    input: JSON.stringify({
      tool_name: tool,
      tool_input: { file_path: ws.draft },
      transcript_path: transcriptPath,
      prompt_id: promptId,
      session_id: "session-abc",
    }),
    encoding: "utf-8",
    env: hookEnv({ state: ws.state }),
  });
  assert.equal(result.error, undefined, `could not run ${CAPTURE}`);
  assert.equal(
    result.status,
    0,
    `capture exited ${result.status}: ${result.stderr}`,
  );
  return result;
}

function log(ws) {
  const path = join(ws.state, "corrections.jsonl");
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf-8")
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l));
}

// The first write of a draft has nothing to diff against. Logging it would
// record the whole draft as a correction, which it is not.
test("first write snapshots and logs nothing", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "write me a draft");
  capture(ws, { body: "the first version\n" });
  assert.deepEqual(log(ws), []);
  assert.equal(existsSync(join(ws.state, "snapshots")), true);
});

// sha256sum and shasum print the same digest, so either tool finds a snapshot
// the other one made.
test("the snapshot is keyed by the path's SHA-256", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "write me a draft");
  capture(ws, { body: "the first version\n" });
  const key = createHash("sha256").update(ws.draft).digest("hex").slice(0, 40);
  assert.equal(existsSync(join(ws.state, "snapshots", key)), true);
});

test("a later write logs the change with the user's instruction as the reason", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "write me a draft");
  capture(ws, { body: "the first version\n" });

  transcript(ws, "turn-2", "stop hedging, say it plainly");
  capture(ws, { body: "the second version\n", promptId: "turn-2" });

  const entries = log(ws);
  assert.equal(entries.length, 1);
  const [e] = entries;
  assert.equal(e.reason, "stop hedging, say it plainly");
  assert.equal(e.profile, "technical");
  assert.equal(e.prompt_id, "turn-2");
  assert.equal(e.session_id, "session-abc");
  assert.equal(e.file, ws.draft);
  assert.match(e.original, /first version/);
  assert.match(e.rewrite, /second version/);
  assert.ok(e.timestamp, "no timestamp");
});

test("a write that changes nothing logs nothing", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "write me a draft");
  capture(ws, { body: "unchanged\n" });
  transcript(ws, "turn-2", "leave it alone");
  capture(ws, { body: "unchanged\n", promptId: "turn-2" });
  assert.deepEqual(log(ws), []);
});

// Every edit in one turn answers the same instruction, so logging each one
// records the same correction two or three times.
test("only the first edit of a turn is logged", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "write me a draft");
  capture(ws, { body: "one\n" });

  transcript(ws, "turn-2", "tighten both paragraphs");
  capture(ws, { body: "two\n", promptId: "turn-2", tool: "Edit" });
  capture(ws, { body: "three\n", promptId: "turn-2", tool: "Edit" });

  const entries = log(ws);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].prompt_id, "turn-2");
  assert.equal(entries[0].reason, "tighten both paragraphs");
});

// A drafting turn is not a correction. Claude often writes a new draft in two
// or three calls, and logging calls 2..n records the topic request as a
// correction. Those content words then cluster and reach the user as a
// candidate voice rule.
test("a draft written in several writes in one turn logs nothing", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "write me a design doc about authentication");
  capture(ws, { body: "# Auth\n" });
  capture(ws, { body: "# Auth\n\nSection one.\n", tool: "Edit" });
  capture(ws, {
    body: "# Auth\n\nSection one.\n\nSection two.\n",
    tool: "Edit",
  });
  assert.deepEqual(log(ws), []);
});

// A correction in the next turn still lands, because the snapshot then
// belongs to an earlier turn.
test("the next turn's first edit is logged", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "write me a draft");
  capture(ws, { body: "one\n" });
  capture(ws, { body: "one and a half\n", tool: "Edit" });

  transcript(ws, "turn-2", "cut the hedging");
  capture(ws, { body: "two\n", promptId: "turn-2", tool: "Edit" });

  const entries = log(ws);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].reason, "cut the hedging");
  assert.match(
    entries[0].original,
    /one and a half/,
    "the diff must span the whole previous turn",
  );
});

// Takes a fresh workspace through a first edit and a second one, and returns
// how long the second took. With staleLock, a lock older than the hook's
// staleness window sits in the way of that second edit.
function timeSecondEdit({ staleLock = false } = {}) {
  const ws = workspace();
  transcript(ws, "turn-1", "first");
  capture(ws, { body: "a\n" });

  if (staleLock) {
    const lock = join(ws.state, ".lock");
    const old = new Date(Date.now() - 600000);
    mkdirSync(lock);
    utimesSync(lock, old, old);
  }

  transcript(ws, "turn-2", "change it");
  const started = Date.now();
  capture(ws, { body: "b\n", promptId: "turn-2" });
  const ms = Date.now() - started;
  assert.equal(log(ws).length, 1, "the change was not logged");
  return ms;
}

// A lock left behind by a killed run would otherwise cost every later edit a
// fixed half second of retries.
//
// The hook spends several hundred milliseconds of its own before it ever
// reaches the lock, and how many depends on the machine, so an absolute budget
// here measures the wrong thing. Compare against a run with no lock instead:
// waiting out the retries would add the whole half second on top.
test("a stale lock is taken over", () => {
  const baseline = timeSecondEdit();
  const stale = timeSecondEdit({ staleLock: true });

  assert.ok(
    stale - baseline < 250,
    `the stale lock was waited on: ${stale - baseline}ms over a ${baseline}ms baseline, against a 500ms retry budget`,
  );
});

// The transcript holds tool results and injected context under the same
// "user" type. Picking the wrong record fills the reason with noise.
test("the reason skips tool results, meta records and other turns", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "first");
  capture(ws, { body: "a\n" });
  transcript(ws, "turn-2", "the real instruction");
  capture(ws, { body: "b\n", promptId: "turn-2" });
  assert.equal(log(ws)[0].reason, "the real instruction");
});

// Served and remote sessions send an empty transcript_path. The edit is still
// worth logging; only the reason is missing.
test("an empty transcript path logs the change with no reason", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "first");
  capture(ws, { body: "a\n" });
  capture(ws, { body: "b\n", promptId: "turn-2", transcriptPath: "" });
  const entries = log(ws);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].reason, "");
});

test("a file outside the draft glob is ignored", () => {
  const ws = workspace();
  const outside = join(ws.root, "notes.md");
  writeFileSync(outside, "not a draft\n");
  const result = spawnSync(CAPTURE, {
    input: JSON.stringify({
      tool_name: "Write",
      tool_input: { file_path: outside },
      prompt_id: "t",
    }),
    encoding: "utf-8",
    env: hookEnv({ state: ws.state }),
  });
  assert.equal(result.status, 0);
  assert.deepEqual(log(ws), []);
});

test("a tool other than Write, Edit or MultiEdit is ignored", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "first");
  capture(ws, { body: "a\n" });
  capture(ws, { body: "b\n", promptId: "turn-2", tool: "Read" });
  assert.deepEqual(log(ws), []);
});

// Two drafts must not share a snapshot, or each write looks like a rewrite of
// the other file.
test("two drafts keep separate snapshots", () => {
  const ws = workspace();
  const other = join(dirname(ws.draft), "other.md");
  transcript(ws, "turn-1", "first");

  capture(ws, { body: "alpha\n" });
  writeFileSync(other, "beta\n");
  spawnSync(CAPTURE, {
    input: JSON.stringify({
      tool_name: "Write",
      tool_input: { file_path: other },
      transcript_path: ws.transcript,
      prompt_id: "turn-1",
    }),
    encoding: "utf-8",
    env: hookEnv({ state: ws.state }),
  });

  assert.deepEqual(
    log(ws),
    [],
    "a first write of either file must log nothing",
  );
});

// A correction is a few lines, not a book. An unbounded field would make the
// log unreadable and slow the promotion hook down.
// Truncating bytes can split a multibyte character. The log line is then
// invalid JSON, and the whole correction is lost.
test("truncation cuts on characters, not bytes", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "first");
  capture(ws, { body: "small\n" });
  transcript(ws, "turn-2", "expand it");
  capture(ws, { body: `${"—".repeat(2500)}\n`, promptId: "turn-2" });
  const [e] = log(ws);
  assert.equal(e.rewrite.length, 2000);
  assert.match(e.rewrite, /^—+$/, "the truncated field is not clean text");
});

test("a very large change is truncated", () => {
  const ws = workspace();
  transcript(ws, "turn-1", "first");
  capture(ws, { body: "small\n" });
  transcript(ws, "turn-2", "expand it");
  capture(ws, { body: `${"x".repeat(50000)}\n`, promptId: "turn-2" });
  const [e] = log(ws);
  assert.ok(e.rewrite.length < 3000, `rewrite was ${e.rewrite.length} chars`);
});
