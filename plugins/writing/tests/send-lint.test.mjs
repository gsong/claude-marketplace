// Drives hooks/send-lint.sh as a subprocess, the way Claude Code invokes it:
// the PreToolUse payload arrives on stdin, and a report or a deny comes back on
// stdout. Nothing is imported from the scripts, so these tests pin the contract.
//
// Every test runs against a fixture rules directory with one banned word per
// file, so the shipped rules can grow without breaking a test, and a temp state
// directory, so a bounce file never leaks into the user's real state.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  symlinkSync,
  utimesSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const HOOK = join(HERE, "..", "hooks", "send-lint.sh");

const SLACK = "mcp__plugin_slack_slack__slack_";
const DOCS = "mcp__claude_ai_Claude_Docs__";

// One word per file, so a finding names the file its rule came from.
const FIXTURE_RULES = mkdtempSync(join(tmpdir(), "wl-send-rules-"));
for (const [name, word] of [
  ["common", "banned"],
  ["technical", "techword"],
  ["comms", "commsword"],
]) {
  writeFileSync(
    join(FIXTURE_RULES, `${name}.md`),
    ["```rules", `re\t\\b${word}\\b\tthe word ${word}`, "```", ""].join("\n"),
  );
}

function freshState() {
  return mkdtempSync(join(tmpdir(), "wl-send-state-"));
}

// Returns the parsed hookSpecificOutput, or null when the hook says nothing.
// Silence is the pass case: Claude Code runs the tool as if no hook existed.
function lint(
  payload,
  { state = freshState(), rules = FIXTURE_RULES, env = {} } = {},
) {
  const result = spawnSync(HOOK, {
    input: typeof payload === "string" ? payload : JSON.stringify(payload),
    encoding: "utf-8",
    env: {
      ...process.env,
      WRITING_LINE_RULES: rules,
      WRITING_LINE_STATE: state,
      ...env,
    },
  });
  assert.equal(result.error, undefined, `could not run ${HOOK}`);
  assert.equal(
    result.status,
    0,
    `hook exited ${result.status}: ${result.stderr}`,
  );
  if (result.stdout.trim() === "") return null;
  return JSON.parse(result.stdout).hookSpecificOutput;
}

function call(tool_name, tool_input, extra = {}) {
  return {
    session_id: "sess-1",
    cwd: tmpdir(),
    tool_name,
    tool_input,
    ...extra,
  };
}

function bash(command, extra) {
  return call("Bash", { command }, extra);
}

// A soft report: advisory context, never a decision.
function assertAdvisory(out, pattern) {
  assert.ok(out, "expected an advisory report");
  assert.equal(out.hookEventName, "PreToolUse");
  assert.equal(
    out.permissionDecision,
    undefined,
    "a soft surface must never deny",
  );
  assert.match(out.additionalContext, pattern);
  assert.match(out.additionalContext, /Advisory only\./);
}

function assertDeny(out, pattern) {
  assert.ok(out, "expected a deny");
  assert.equal(out.permissionDecision, "deny");
  assert.match(out.permissionDecisionReason, pattern);
  assert.match(out.permissionDecisionReason, /bounced once/);
  assert.match(out.permissionDecisionReason, /The retry goes through\./);
}

function tempDir() {
  return mkdtempSync(join(tmpdir(), "wl-send-files-"));
}

// --- extraction, surface by surface -------------------------------------

test("slack send_message: message is linted with the comms profile", () => {
  const out = lint(
    call(`${SLACK}send_message`, {
      channel_id: "C1",
      message: "a commsword here",
    }),
  );
  assertDeny(out, /profile "comms"/);
  assert.match(
    out.permissionDecisionReason,
    /\[message\]\nline 1: the word commsword/,
  );
});

test("slack: the comms profile does not load technical rules", () => {
  const out = lint(
    call(`${SLACK}send_message`, {
      channel_id: "C1",
      message: "a techword here",
    }),
  );
  assert.equal(out, null);
});

test("slack: common rules load alongside the profile", () => {
  const out = lint(
    call(`${SLACK}send_message`, {
      channel_id: "C1",
      message: "a banned word",
    }),
  );
  assertDeny(out, /the word banned/);
});

test("slack schedule_message is hard", () => {
  const out = lint(
    call(`${SLACK}schedule_message`, {
      channel_id: "C1",
      message: "commsword",
      post_at: 1,
    }),
  );
  assertDeny(out, /the word commsword/);
});

test("slack send_message_draft is soft", () => {
  const out = lint(
    call(`${SLACK}send_message_draft`, {
      channel_id: "C1",
      message: "commsword",
    }),
  );
  assertAdvisory(out, /profile "comms", on slack_send_message_draft/);
});

test("slack create_canvas: content, technical profile", () => {
  const out = lint(
    call(`${SLACK}create_canvas`, {
      title: "T",
      content: "# Head\n\nsome techword",
    }),
  );
  assertAdvisory(out, /profile "technical"/);
  assert.match(out.additionalContext, /\[content\]\nline 3: the word techword/);
});

test("slack update_canvas: each section's content, deletes skipped", () => {
  const out = lint(
    call(`${SLACK}update_canvas`, {
      canvas_id: "F1",
      sections: [
        { edit_type: "replace", section_id: "a", content: "clean text" },
        { edit_type: "append", section_id: "b", content: "a techword" },
        { edit_type: "delete", section_id: "c", content: "banned" },
      ],
    }),
  );
  assertAdvisory(out, /\[sections\[1\]\.content\]\nline 1: the word techword/);
  assert.doesNotMatch(out.additionalContext, /banned|sections\[2\]/);
});

test("gmail create_draft: body, comms profile", () => {
  const out = lint(
    call("mcp__claude_ai_Gmail__create_draft", { body: "one commsword" }),
  );
  assertAdvisory(
    out,
    /profile "comms"[\s\S]*\[body\]\nline 1: the word commsword/,
  );
});

test("gmail create_draft: htmlBody with tags stripped when body is absent", () => {
  const out = lint(
    call("mcp__claude_ai_Gmail__create_draft", {
      htmlBody:
        '<style>.commsword{}</style><p class="commsword">Hello</p>\n<p>one commsword</p>',
    }),
  );
  assertAdvisory(out, /\[htmlBody\]\nline 2: the word commsword/);
  assert.doesNotMatch(
    out.additionalContext,
    /line 1:/,
    "markup was scanned as prose",
  );
});

test("gmail create_draft: body wins over htmlBody, so findings are not doubled", () => {
  const out = lint(
    call("mcp__claude_ai_Gmail__create_draft", {
      body: "one commsword",
      htmlBody: "<p>one commsword</p>",
    }),
  );
  assert.doesNotMatch(out.additionalContext, /htmlBody/);
});

test("claude docs batch: nested markdown", () => {
  const out = lint(
    call(`${DOCS}batch`, {
      container: {
        kind: "project",
        create: {
          name: "Doc",
          doc: { markdown: "# Doc\n\n<?claude block s1?>\n\nA techword." },
        },
      },
      batch: [],
    }),
  );
  assertAdvisory(
    out,
    /\[\$\.container\.create\.doc\.markdown\]\nline 5: the word techword/,
  );
});

test("claude docs update: content deep in ops, find targets ignored", () => {
  const out = lint(
    call(`${DOCS}update`, {
      ref: { object: "node", id: "n1" },
      payload: {
        ops: [
          {
            op: "delete",
            target: { kind: "find", text: " a techword already there" },
          },
          {
            op: "insert",
            target: { kind: "root" },
            source: {
              as: "markdown",
              from: { kind: "inline", content: "new techword text" },
            },
          },
        ],
      },
    }),
  );
  assertAdvisory(
    out,
    /ops\[1\]\.source\.from\.content\]\nline 1: the word techword/,
  );
  assert.doesNotMatch(out.additionalContext, /target/);
});

test("claude docs create: a comment body", () => {
  const out = lint(
    call(`${DOCS}create`, {
      object: "utterance",
      payload: { body: "techword" },
    }),
  );
  assertAdvisory(out, /\$\.payload\.body/);
});

test("google drive create_file: textContent", () => {
  const out = lint(
    call("mcp__claude_ai_Google_Drive__create_file", {
      title: "T",
      contentMimeType: "text/plain",
      textContent: "some techword",
    }),
  );
  assertAdvisory(out, /\[textContent\]\nline 1: the word techword/);
});

test("google drive create_file: a CSV upload is data, not prose", () => {
  const out = lint(
    call("mcp__claude_ai_Google_Drive__create_file", {
      title: "T",
      contentMimeType: "text/csv",
      textContent: "a,techword",
    }),
  );
  assert.equal(out, null);
});

test("artifact: published .md and .html files, HTML flattened", () => {
  const dir = tempDir();
  writeFileSync(join(dir, "page.md"), "# Page\n\nOne techword.\n");
  writeFileSync(
    join(dir, "extra.html"),
    '<!doctype html>\n<style>.techword { color: red }</style>\n<p title="techword">\nHi techword\n</p>\n',
  );
  const out = lint(
    call(
      "Artifact",
      { file_path: "page.md", files: { "extra.html": { from: "extra.html" } } },
      { cwd: dir },
    ),
  );
  assertAdvisory(out, /page\.md\]\nline 3: the word techword/);
  // html-prose.pl reports the line a block starts on (3), the fallback the line
  // the word sits on (4). Which one runs depends on HTML::Parser being present.
  assert.match(
    out.additionalContext,
    /extra\.html\]\nline [34]: the word techword/,
  );
  assert.doesNotMatch(
    out.additionalContext,
    /line 2:/,
    "CSS was scanned as prose",
  );
});

test("artifact: without html-prose.pl, HTML is still stripped of markup", () => {
  const bin = tempDir();
  symlinkSync(
    join(HERE, "..", "bin", "voice-scan.pl"),
    join(bin, "voice-scan.pl"),
  );
  const dir = tempDir();
  writeFileSync(
    join(dir, "page.html"),
    '<style>\n.techword { color: red }\n</style>\n<p title="techword">\nHi &amp; techword\n</p>\n',
  );
  const out = lint(call("Artifact", { file_path: "page.html" }, { cwd: dir }), {
    env: { WRITING_LINE_BIN: bin },
  });
  assertAdvisory(out, /page\.html\]\nline 5: the word techword/);
  assert.doesNotMatch(
    out.additionalContext,
    /line [1-4]:/,
    "markup was scanned as prose",
  );
});

test("artifact: a non-publish action and an asset upload are ignored", () => {
  const dir = tempDir();
  writeFileSync(join(dir, "page.md"), "techword\n");
  assert.equal(
    lint(
      call("Artifact", { action: "read", file_path: "page.md" }, { cwd: dir }),
    ),
    null,
  );
  assert.equal(
    lint(
      call(
        "Artifact",
        { url: "u", asset: true, file_path: "page.md" },
        { cwd: dir },
      ),
    ),
    null,
  );
});

test("gh pr comment --body", () => {
  const out = lint(bash('gh pr comment 12 --body "a techword here"'));
  assertDeny(out, /profile "technical", on gh pr comment #12/);
  assert.match(
    out.permissionDecisionReason,
    /\[--body\]\nline 1: the word techword/,
  );
});

test("gh pr review -b and --body= forms", () => {
  assertDeny(
    lint(bash("gh pr review 3 --comment -b 'techword'")),
    /the word techword/,
  );
  assertDeny(
    lint(bash("gh issue comment 4 --body='techword'")),
    /on gh issue comment #4/,
  );
});

test("gh pr comment --body-file reads the file", () => {
  const dir = tempDir();
  writeFileSync(join(dir, "reply.md"), "Line one.\nA techword.\n");
  const out = lint(bash("gh pr comment 12 --body-file reply.md", { cwd: dir }));
  assertDeny(out, /\[--body-file reply\.md\]\nline 2: the word techword/);
});

test("gh pr comment with the body in a $(cat <<EOF) heredoc", () => {
  const command = [
    "gh pr comment 12 --body \"$(cat <<'EOF'",
    "First line.",
    "A techword here.",
    "EOF",
    ')"',
  ].join("\n");
  const out = lint(bash(command));
  assertDeny(out, /\[heredoc 1\]\nline 2: the word techword/);
  assert.doesNotMatch(out.permissionDecisionReason, /\[--body\]/);
});

test("gh api -f body=", () => {
  const out = lint(
    bash(
      "gh api repos/o/r/issues/7/comments -f body='a techword' -f other=banned",
    ),
  );
  assertDeny(out, /on gh api repos\/o\/r\/issues\/7\/comments/);
  assert.match(
    out.permissionDecisionReason,
    /\[body=\]\nline 1: the word techword/,
  );
  assert.doesNotMatch(out.permissionDecisionReason, /banned/);
});

test("gh api heredoc JSON: every body, including comments[].body", () => {
  const review = {
    event: "COMMENT",
    body: "Top techword.",
    comments: [
      { path: "a.js", line: 1, body: "fine" },
      { path: "b.js", line: 2, body: "Inline banned." },
    ],
  };
  const command = [
    "gh api repos/o/r/pulls/9/reviews --method POST --input - <<'EOF'",
    JSON.stringify(review, null, 2),
    "EOF",
  ].join("\n");
  const out = lint(bash(command));
  assertDeny(out, /\[heredoc 1 \$\.body\]\nline 1: the word techword/);
  assert.match(
    out.permissionDecisionReason,
    /\[heredoc 1 \$\.comments\[1\]\.body\]\nline 1: the word banned/,
  );
  assert.doesNotMatch(out.permissionDecisionReason, /a\.js|COMMENT/);
});

test("gh api heredoc that is not JSON is linted as raw text", () => {
  const command = [
    "gh pr comment 5 --body-file - <<EOF",
    "raw techword",
    "EOF",
  ].join("\n");
  assertDeny(lint(bash(command)), /\[heredoc 1\]\nline 1: the word techword/);
});

test("gh api --input file reads its JSON body strings", () => {
  const dir = tempDir();
  writeFileSync(
    join(dir, "review.json"),
    JSON.stringify({ body: "x", comments: [{ body: "techword" }] }),
  );
  const out = lint(
    bash("gh api -X POST repos/o/r/pulls/9/reviews --input review.json", {
      cwd: dir,
    }),
  );
  assertDeny(
    out,
    /\[--input review\.json \$\.comments\[0\]\.body\]\nline 1: the word techword/,
  );
});

test("gh after other commands in the same Bash call", () => {
  const out = lint(bash("cd /tmp && gh pr comment 8 --body 'techword' | cat"));
  assertDeny(out, /on gh pr comment #8/);
});

// --- clean, silent, and out of scope ------------------------------------

test("clean text gives no output on every kind of surface", () => {
  assert.equal(
    lint(
      call(`${SLACK}send_message`, { channel_id: "C1", message: "all fine" }),
    ),
    null,
  );
  assert.equal(
    lint(call(`${SLACK}create_canvas`, { title: "T", content: "all fine" })),
    null,
  );
  assert.equal(lint(bash("gh pr comment 1 --body 'all fine'")), null);
});

test("a non-gh Bash command produces nothing", () => {
  assert.equal(lint(bash("echo techword banned")), null);
});

test("read-only gh commands produce nothing", () => {
  assert.equal(lint(bash("gh pr view 12 --comments")), null);
  assert.equal(lint(bash("gh api repos/o/r/pulls/12/comments")), null);
  assert.equal(
    lint(bash("gh api -X GET repos/o/r/issues -f body=techword")),
    null,
  );
});

test("gh api on a path that is not a comment surface produces nothing", () => {
  assert.equal(
    lint(bash("gh api -X POST repos/o/r/releases -f body=techword")),
    null,
  );
});

test("gh pr edit without a body produces nothing", () => {
  assert.equal(lint(bash("gh pr edit 12 --add-label techword")), null);
});

test("a tool the table does not know produces nothing", () => {
  assert.equal(
    lint(call("Write", { file_path: "/x.md", content: "techword" })),
    null,
  );
});

test("a profile with no rule file produces nothing", () => {
  const rules = mkdtempSync(join(tmpdir(), "wl-send-empty-"));
  assert.equal(
    lint(
      call(`${SLACK}send_message`, { channel_id: "C1", message: "banned" }),
      { rules },
    ),
    null,
  );
});

test("a malformed payload exits 0 with no output", () => {
  assert.equal(lint("not json"), null);
  assert.equal(lint("[1, 2]"), null);
  assert.equal(lint(""), null);
  assert.equal(
    lint({ tool_name: `${SLACK}send_message`, tool_input: "string" }),
    null,
  );
  assert.equal(
    lint({
      tool_name: "Bash",
      tool_input: { command: "gh pr comment 1 --body 'unclosed" },
    }),
    null,
  );
});

// --- bounce once --------------------------------------------------------

test("hard slack: deny first, allow the retry, deny a different thread", () => {
  const state = freshState();
  const send = (thread_ts) =>
    lint(
      call(`${SLACK}send_message`, {
        channel_id: "C1",
        thread_ts,
        message: "commsword",
      }),
      {
        state,
      },
    );
  assertDeny(send("1.1"), /commsword/);
  assert.equal(send("1.1"), null, "the retry must go through");
  assertDeny(send("2.2"), /commsword/);
  assertDeny(send("1.1"), /commsword/);
});

test("hard gh: deny first, allow the retry, deny a different PR", () => {
  const state = freshState();
  const comment = (n) =>
    lint(bash(`gh pr comment ${n} --body 'techword'`), { state });
  assertDeny(comment(12), /#12/);
  assert.equal(comment(12), null);
  assertDeny(comment(13), /#13/);
});

test("a PR URL and a bare number are the same gh target", () => {
  const state = freshState();
  assertDeny(
    lint(bash("gh pr comment https://github.com/o/r/pull/12 --body techword"), {
      state,
    }),
    /#12/,
  );
  assert.equal(lint(bash("gh pr comment 12 --body techword"), { state }), null);
});

test("the bounce is per session", () => {
  const state = freshState();
  const send = (session_id) =>
    lint(
      call(
        `${SLACK}send_message`,
        { channel_id: "C1", message: "commsword" },
        { session_id },
      ),
      { state },
    );
  assertDeny(send("a"), /commsword/);
  assertDeny(send("b"), /commsword/);
});

test("a bounce older than 30 minutes denies again", () => {
  const state = freshState();
  const send = () =>
    lint(
      call(`${SLACK}send_message`, { channel_id: "C1", message: "commsword" }),
      { state },
    );
  assertDeny(send(), /commsword/);
  const bounces = join(state, "bounces");
  const [key] = readdirSync(bounces);
  const old = Date.now() / 1000 - 31 * 60;
  utimesSync(join(bounces, key), old, old);
  assertDeny(send(), /commsword/);
  assert.equal(send(), null);
});

test("a clean retry clears the bounce, so the next dirty send bounces again", () => {
  const state = freshState();
  const send = (message) =>
    lint(call(`${SLACK}send_message`, { channel_id: "C1", message }), {
      state,
    });
  assertDeny(send("commsword"), /commsword/);
  assert.equal(send("all fine"), null);
  assert.equal(readdirSync(join(state, "bounces")).length, 0);
  assertDeny(send("commsword"), /commsword/);
});

test("a soft surface never writes bounce state", () => {
  const state = freshState();
  lint(
    call(`${SLACK}send_message_draft`, {
      channel_id: "C1",
      message: "commsword",
    }),
    { state },
  );
  assert.equal(existsSync(join(state, "bounces")), false);
});

test("a malformed rule file alone does not bounce a send", () => {
  const rules = mkdtempSync(join(tmpdir(), "wl-send-bad-"));
  mkdirSync(rules, { recursive: true });
  writeFileSync(join(rules, "comms.md"), "```rules\nre spaces not tabs\n```\n");
  assert.equal(
    lint(call(`${SLACK}send_message`, { channel_id: "C1", message: "fine" }), {
      rules,
    }),
    null,
  );
});
