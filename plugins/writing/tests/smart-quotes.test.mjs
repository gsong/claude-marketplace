// Drives hooks/smart-quotes.py as a subprocess, the way Claude Code invokes it:
// the PreToolUse payload arrives on stdin, and a deny comes back on stdout when
// visible text holds a straight quote. Silence means the call goes through.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const HOOK = join(HERE, "..", "hooks", "smart-quotes.py");

const CANVAS = "mcp__plugin_slack_slack__slack_create_canvas";
const CANVAS_UPDATE = "mcp__plugin_slack_slack__slack_update_canvas";
const DOCS = "mcp__claude_ai_Claude_Docs__batch";
const DRIVE = "mcp__claude_ai_Google_Drive__create_file";

// Returns the deny reason, or null when the hook lets the call through.
function guard(payload) {
  const result = spawnSync(HOOK, {
    input: typeof payload === "string" ? payload : JSON.stringify(payload),
    encoding: "utf-8",
  });
  assert.equal(result.error, undefined, `could not run ${HOOK}`);
  assert.equal(
    result.status,
    0,
    `hook exited ${result.status}: ${result.stderr}`,
  );
  if (result.stdout.trim() === "") return null;
  const out = JSON.parse(result.stdout).hookSpecificOutput;
  assert.equal(out.permissionDecision, "deny");
  return out.permissionDecisionReason;
}

function artifact(files, tool_input = {}) {
  const dir = mkdtempSync(join(tmpdir(), "sq-art-"));
  for (const [name, body] of Object.entries(files))
    writeFileSync(join(dir, name), body);
  return guard({ tool_name: "Artifact", cwd: dir, tool_input });
}

// --- Artifact: unchanged from the original guard -------------------------

test("artifact: straight quotes in Markdown prose are denied", () => {
  const reason = artifact(
    { "page.md": 'Line one.\nShe said "hi".\n' },
    { file_path: "page.md" },
  );
  assert.match(reason, /Straight quotes in visible artifact text/);
  assert.match(reason, /page\.md:2: She said "hi"\./);
});

test("artifact: smart quotes pass", () => {
  assert.equal(
    artifact(
      { "page.md": "She said “hi” and it’s fine.\n" },
      { file_path: "page.md" },
    ),
    null,
  );
});

test("artifact: Markdown code spans, fences, link targets and inline HTML are exempt", () => {
  const body = [
    "Run `echo 'x'` first.",
    "```",
    'const a = "b";',
    "```",
    '[link](https://x.test/?q="a")',
    '<span class="c">plain</span>',
    "",
  ].join("\n");
  assert.equal(artifact({ "page.md": body }, { file_path: "page.md" }), null);
});

test("artifact: HTML text is checked, attributes and <code> are exempt", () => {
  const html = '<p class="a">Fine</p>\n<code>"x"</code>\n<p>It\'s here</p>\n';
  const reason = artifact({ "page.html": html }, { file_path: "page.html" });
  assert.match(reason, /page\.html:3: It's here/);
  assert.doesNotMatch(reason, /page\.html:[12]:/);
});

test("artifact: files map sources and JSON string values are checked", () => {
  const reason = artifact(
    {
      "index.html": "<p>ok</p>",
      "data.json": JSON.stringify({ title: "Bob's" }),
    },
    { file_path: "index.html", files: { "data.json": { from: "data.json" } } },
  );
  assert.match(reason, /data\.json \$\.title: Bob's/);
});

test("artifact: non-publish actions and asset uploads pass", () => {
  assert.equal(
    artifact({ "page.md": '"x"' }, { action: "read", file_path: "page.md" }),
    null,
  );
  assert.equal(
    artifact({ "page.md": '"x"' }, { asset: true, file_path: "page.md" }),
    null,
  );
});

// --- MCP surfaces ---------------------------------------------------------

test("slack create_canvas: content is checked", () => {
  const reason = guard({
    tool_name: CANVAS,
    tool_input: { title: "T", content: "# H\n\nIt's here" },
  });
  assert.match(reason, /Straight quotes in visible text/);
  assert.match(reason, /content:3: It's here/);
});

test("slack update_canvas: sections[].content is checked", () => {
  const reason = guard({
    tool_name: CANVAS_UPDATE,
    tool_input: {
      canvas_id: "F1",
      sections: [
        { edit_type: "replace", section_id: "a", content: "fine" },
        { edit_type: "append", section_id: "b", content: 'a "quote"' },
      ],
    },
  });
  assert.match(reason, /sections\[1\]\.content:1: a "quote"/);
});

test("slack canvas: code spans and fences are exempt", () => {
  const content = [
    "Use `it's` here.",
    "```",
    'x = "y"',
    "```",
    "![](@U123) and ![](#C1)",
  ].join("\n");
  assert.equal(
    guard({ tool_name: CANVAS, tool_input: { title: "T", content } }),
    null,
  );
});

test("claude docs: nested markdown is checked, block directives are not text", () => {
  const reason = guard({
    tool_name: DOCS,
    tool_input: {
      container: {
        kind: "project",
        create: {
          name: "Doc",
          doc: { markdown: '# Doc\n\n<?claude block s1?>\n\nIt\'s "done".' },
        },
      },
      batch: [],
    },
  });
  assert.match(reason, /\$\.container\.create\.doc\.markdown:5: It's "done"\./);
  assert.doesNotMatch(reason, /:3:/);
});

test("claude docs: a code span is exempt", () => {
  const tool_input = {
    ref: { object: "node", id: "n" },
    payload: {
      ops: [
        { op: "insert", source: { from: { content: 'Set `a="b"` now.' } } },
      ],
    },
  };
  assert.equal(
    guard({ tool_name: "mcp__claude_ai_Claude_Docs__update", tool_input }),
    null,
  );
});

test("google drive create_file: textContent is checked", () => {
  const reason = guard({
    tool_name: DRIVE,
    tool_input: {
      title: "T",
      contentMimeType: "text/plain",
      textContent: "It's here",
    },
  });
  assert.match(reason, /textContent:1: It's here/);
});

test("google drive create_file: HTML attributes are exempt, a CSV is not prose", () => {
  assert.equal(
    guard({
      tool_name: DRIVE,
      tool_input: {
        title: "T",
        contentMimeType: "text/html",
        textContent: '<p class="a">fine</p>',
      },
    }),
    null,
  );
  assert.equal(
    guard({
      tool_name: DRIVE,
      tool_input: {
        title: "T",
        contentMimeType: "text/csv",
        textContent: '"a","b"',
      },
    }),
    null,
  );
});

test("a malformed payload passes silently", () => {
  assert.equal(guard("not json"), null);
  assert.equal(guard(""), null);
  assert.equal(guard({ tool_name: CANVAS, tool_input: { content: 42 } }), null);
});
