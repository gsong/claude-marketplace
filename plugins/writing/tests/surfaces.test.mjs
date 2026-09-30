// Keeps hooks.json and the SURFACES table in surfaces.py in step. A tool that
// the table knows but a matcher leaves out never reaches its hook, and nothing
// else would report it.
//
// Each SURFACES row needs a real tool name below. The send-lint matcher must
// take every sample. The smart-quotes matcher must take exactly the samples
// whose row is a `technical` profile outside Bash: canvases, docs, files, and
// artifacts, but not Slack messages or Gmail drafts.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const HOOKS = join(dirname(fileURLToPath(import.meta.url)), "..", "hooks");

const SAMPLE_TOOLS = [
  "mcp__plugin_slack_slack__slack_send_message",
  "mcp__plugin_slack_slack__slack_schedule_message",
  "mcp__plugin_slack_slack__slack_send_message_draft",
  "mcp__plugin_slack_slack__slack_create_canvas",
  "mcp__plugin_slack_slack__slack_update_canvas",
  "mcp__claude_ai_Gmail__create_draft",
  "mcp__claude_ai_Claude_Docs__create",
  "mcp__claude_ai_Claude_Docs__batch",
  "mcp__claude_ai_Claude_Docs__update",
  "mcp__claude_ai_Google_Drive__create_file",
  "Artifact",
  "Bash",
];

// The rows of SURFACES, read from the source so the test needs no Python.
function surfaceRows() {
  const source = readFileSync(join(HOOKS, "surfaces.py"), "utf-8");
  const rows = [
    ...source.matchAll(/^\s*Surface\(r"([^"]+)", "(\w+)", (True|False), /gm),
  ].map(([, pattern, profile]) => ({ pattern: new RegExp(pattern), profile }));
  assert.ok(rows.length > 0, "no SURFACES rows found in surfaces.py");
  return rows;
}

// A matcher is taken to match the whole tool name, the stricter reading.
function matcherFor(script) {
  const config = JSON.parse(readFileSync(join(HOOKS, "hooks.json"), "utf-8"));
  const entry = config.hooks.PreToolUse.find((e) =>
    e.hooks.some((h) => h.command.endsWith(`/hooks/${script}`)),
  );
  assert.ok(entry, `no PreToolUse entry runs ${script}`);
  return new RegExp(`^(?:${entry.matcher})$`);
}

// First hit wins, as in surface_for.
function rowFor(rows, tool) {
  return rows.find((row) => row.pattern.test(tool));
}

test("every SURFACES row has a sample tool name", () => {
  const rows = surfaceRows();
  for (const row of rows) {
    assert.ok(
      SAMPLE_TOOLS.some((tool) => rowFor(rows, tool) === row),
      `add a sample tool name for ${row.pattern}`,
    );
  }
});

test("every sample maps to a SURFACES row", () => {
  const rows = surfaceRows();
  for (const tool of SAMPLE_TOOLS) {
    assert.ok(rowFor(rows, tool), `${tool} matches no SURFACES row`);
  }
});

test("the send-lint matcher takes every surface", () => {
  const matcher = matcherFor("send-lint.sh");
  for (const tool of SAMPLE_TOOLS) {
    assert.match(tool, matcher, `send-lint never sees ${tool}`);
  }
});

test("the smart-quotes matcher takes the technical surfaces outside Bash", () => {
  const rows = surfaceRows();
  const matcher = matcherFor("smart-quotes.sh");
  for (const tool of SAMPLE_TOOLS) {
    const wanted =
      tool !== "Bash" && rowFor(rows, tool).profile === "technical";
    assert.equal(
      matcher.test(tool),
      wanted,
      `smart-quotes ${wanted ? "never sees" : "should not see"} ${tool}`,
    );
  }
});
