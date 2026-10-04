// Drives hooks/gate.sh as a subprocess, the way Claude Code invokes it: the
// PostToolUse payload arrives on stdin, advisory feedback comes back on stdout.
// Nothing is imported from the script, so these tests pin the contract.
//
// Most tests run against a fixture rules directory, so growing the shipped
// rules cannot break them. The smoke tests read the plugin's default rules
// instead.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { hookEnv } from "./helpers.mjs";

const PLUGIN = join(dirname(fileURLToPath(import.meta.url)), "..");
const GATE = join(PLUGIN, "hooks", "gate.sh");
const SHIPPED_RULES = join(PLUGIN, "defaults", "rules");

const FIXTURE_RULES = mkdtempSync(join(tmpdir(), "wl-rules-"));
writeFileSync(
  join(FIXTURE_RULES, "technical.md"),
  [
    "## Greppable",
    "",
    "```rules",
    "# a comment line is skipped",
    "maxwords\t8\ttoo long",
    "re\tbanned\tthe word banned",
    "density\t—\t4\t4\ttoo many em dashes",
    "```",
    "",
  ].join("\n"),
);

// Prose long enough for a rate to mean anything. Each line is 10 words.
function padding(lines) {
  return Array.from(
    { length: lines },
    () => "one two three. four five six. seven eight nine ten.",
  ).join("\n");
}

// Writes a draft at <tmp>/ai-swap/drafts/<profile>/draft.md and returns its path.
function draft(profile, body) {
  const root = mkdtempSync(join(tmpdir(), "wl-draft-"));
  const dir = join(root, "ai-swap", "drafts", profile);
  mkdirSync(dir, { recursive: true });
  const path = join(dir, "draft.md");
  writeFileSync(path, body);
  return path;
}

// The gate reports only when it has something to say. Silence is the pass case,
// and Claude Code reads it as an ordinary write with no feedback.
function gate(payload, rules = FIXTURE_RULES, { home } = {}) {
  const result = spawnSync(GATE, {
    input: JSON.stringify(payload),
    encoding: "utf-8",
    env: hookEnv({ rules, home }),
  });

  assert.equal(result.error, undefined, `could not run ${GATE}`);
  assert.equal(
    result.status,
    0,
    `gate exited ${result.status}: ${result.stderr}`,
  );

  if (result.stdout.trim() === "") return null;
  return JSON.parse(result.stdout).hookSpecificOutput.additionalContext;
}

function onWrite(path, rules) {
  return gate({ tool_name: "Write", tool_input: { file_path: path } }, rules);
}

// The gate speaks only for drafts and repo markdown written by a file-writing
// tool. Everything else passes through untouched.
test("predicate: a file that is neither a draft nor markdown is ignored", () => {
  const root = mkdtempSync(join(tmpdir(), "wl-other-"));
  const path = join(root, "notes.txt");
  writeFileSync(path, "banned banned banned");
  assert.equal(
    gate({
      tool_name: "Write",
      tool_input: { file_path: path, content: "banned banned banned" },
    }),
    null,
  );
});

test("predicate: a tool other than Write, Edit or MultiEdit is ignored", () => {
  const path = draft("technical", "banned");
  assert.equal(
    gate({ tool_name: "Read", tool_input: { file_path: path } }),
    null,
  );
});

test("predicate: Edit and MultiEdit are both checked", () => {
  const path = draft("technical", "banned");
  for (const tool_name of ["Edit", "MultiEdit"]) {
    const out = gate({ tool_name, tool_input: { file_path: path } });
    assert.match(out ?? "", /the word banned/, `${tool_name} was not checked`);
  }
});

test("predicate: a profile with no rule file is ignored", () => {
  const path = draft("nosuchprofile", "banned");
  assert.equal(onWrite(path), null);
});

test("predicate: a file sitting directly in drafts/ is ignored", () => {
  const root = mkdtempSync(join(tmpdir(), "wl-bare-"));
  const dir = join(root, "ai-swap", "drafts");
  mkdirSync(dir, { recursive: true });
  const path = join(dir, "loose.md");
  writeFileSync(path, "banned");
  assert.equal(onWrite(path), null);
});

test("predicate: a missing file is ignored", () => {
  assert.equal(onWrite("/no/such/ai-swap/drafts/technical/gone.md"), null);
});

// Violations carry the line number so Claude can fix the right line without
// re-reading the file.
test("report: a regex violation names the line and the rule", () => {
  const out = onWrite(draft("technical", "fine line\nthis one is banned\n"));
  assert.match(out, /line 2: the word banned/);
});

test("report: every offending line is listed", () => {
  const out = onWrite(draft("technical", "banned\nok\nbanned\n"));
  assert.match(out, /line 1: /);
  assert.match(out, /line 3: /);
});

test("report: a clean draft says nothing", () => {
  assert.equal(onWrite(draft("technical", "short and clean\n")), null);
});

test("report: sentence length is counted per sentence, not per line", () => {
  const nine = "one two three four five six seven eight nine.";
  assert.match(onWrite(draft("technical", nine)), /line 1: too long/);
  // Two short sentences on one line stay under the limit.
  assert.equal(
    onWrite(draft("technical", "one two three. four five six.")),
    null,
  );
});

// A code sample is not prose. Checking it produces noise that trains the reader
// to ignore the gate.
test("skip: fenced code blocks are not checked", () => {
  const body = [
    "prose is fine",
    "```js",
    "const banned = 1;",
    "```",
    "more prose",
  ].join("\n");
  assert.equal(onWrite(draft("technical", body)), null);
});

test("skip: YAML front matter is not checked", () => {
  const body = ["---", "title: banned", "---", "", "clean prose"].join("\n");
  assert.equal(onWrite(draft("technical", body)), null);
});

test("skip: headings and table rows are exempt from sentence length", () => {
  const long = "one two three four five six seven eight nine ten";
  const body = [`# ${long}`, `| ${long} |`, `> ${long}`].join("\n");
  assert.equal(onWrite(draft("technical", body)), null);
});

// An em dash is allowed. Using one where a period belongs, over and over, is
// the habit the rule is after, so the gate counts them instead of banning them.
test("density: one em dash in a long draft is not reported", () => {
  const out = onWrite(draft("technical", `a single — mark\n${padding(20)}`));
  assert.equal(out, null);
});

test("density: a high rate is reported once, with the count", () => {
  const dashes = Array.from({ length: 12 }, () => "a — b").join("\n");
  const out = onWrite(draft("technical", `${dashes}\n${padding(20)}`));
  const reported = (out.match(/too many em dashes/g) ?? []).length;
  assert.equal(reported, 1, `expected one report, got ${reported}: ${out}`);
  assert.match(out, /draft: too many em dashes \(12 in \d+ words\)/);
});

// Counting in list context returns capture groups instead of matches, which
// silently inflates or deflates the rate.
test("density: a rule with a capture group still counts matches", () => {
  const rules = mkdtempSync(join(tmpdir(), "wl-rules-cap-"));
  writeFileSync(
    join(rules, "technical.md"),
    // Two groups per match, so a list-context count reports double.
    [
      "## Greppable",
      "",
      "```rules",
      "density\t(f)(oo)\t2\t2\ttoo many",
      "```",
      "",
    ].join("\n"),
  );
  const body = `${Array.from({ length: 6 }, () => "foo here").join("\n")}\n${padding(20)}`;
  const out = onWrite(draft("technical", body), rules);
  assert.match(out, /too many \(6 in \d+ words\)/);
});

test("density: a short draft is never rated", () => {
  const dashes = Array.from({ length: 8 }, () => "a — b").join("\n");
  assert.equal(onWrite(draft("technical", dashes)), null);
});

// The shipped rules must load and fire. These are the only tests that read
// them, so adding a rule cannot break the rest of the file.
test("shipped rules: a hyphen between numbers is flagged as a range", () => {
  const out = onWrite(
    draft("technical", "the run took 15-30 minutes\n"),
    SHIPPED_RULES,
  );
  assert.match(out, /line 1: number range/);
});

test("shipped rules: a short range with a hyphen is flagged", () => {
  const out = onWrite(
    draft("technical", "expect 5-10 retries\n"),
    SHIPPED_RULES,
  );
  assert.match(out, /line 1: number range/);
});

// MM-DD and a range like 10-20 cannot be told apart by shape. Docs that write
// dates as MM-DD hit the rule on every date, so that shape goes unflagged.
test("shipped rules: an MM-DD date is not read as a range", () => {
  for (const line of [
    "the review is Thu 10-15",
    "after George’s 09-29 review",
    "box zero (10-18) closes",
    "land it by 12-31",
  ]) {
    assert.equal(
      onWrite(draft("technical", `${line}\n`), SHIPPED_RULES),
      null,
      line,
    );
  }
});

test("shipped rules: a hyphen range outside MM-DD bounds is flagged", () => {
  for (const line of ["pages 13-20 cover it", "pick 10-32 of them"]) {
    const out = onWrite(draft("technical", `${line}\n`), SHIPPED_RULES);
    assert.match(out ?? "", /line 1: number range/, line);
  }
});

test("shipped rules: an ISO date is not read as a range", () => {
  assert.equal(
    onWrite(
      draft("technical", "shipped on 2026-08-27 as planned\n"),
      SHIPPED_RULES,
    ),
    null,
  );
});

test("shipped rules: an en dash range passes", () => {
  assert.equal(
    onWrite(draft("technical", "the run took 10–20 minutes\n"), SHIPPED_RULES),
    null,
  );
});

test("shipped rules: a weekday range with a hyphen is flagged", () => {
  const out = onWrite(
    draft("technical", "the window is Mon-Fri each week\n"),
    SHIPPED_RULES,
  );
  assert.match(out, /line 1: date range/);
});

test("shipped rules: a single em dash is not reported", () => {
  const out = onWrite(
    draft("technical", `an em dash — right here\n${padding(20)}`),
    SHIPPED_RULES,
  );
  assert.equal(out, null);
});

// The rules files hold multi-byte characters. Read as bytes, a character class
// like [-—] matches one byte of the em dash rather than the character, so the
// rule silently never fires.
test("utf-8: an em dash range is caught, like a hyphen range", () => {
  const out = onWrite(
    draft("technical", "the window is 10—20 items wide\n"),
    SHIPPED_RULES,
  );
  assert.match(out ?? "", /line 1: number range/);
});

test("utf-8: an em dash date range is caught", () => {
  const out = onWrite(
    draft("technical", "the window is Mon—Fri each week\n"),
    SHIPPED_RULES,
  );
  assert.match(out ?? "", /line 1: date range/);
});

// A bare --- is a thematic break, not front matter. Reading to the end of the
// file looking for a close blanks the whole draft and disables the gate.
test("front matter: an unterminated --- does not blank the draft", () => {
  const body = [
    "---",
    "We should utilize the delve landscape here.",
    "This is important to note.",
  ].join("\n");
  const out = onWrite(draft("technical", body), SHIPPED_RULES);
  assert.match(out ?? "", /line 2: "utilize"/);
});

test("front matter: a block closed with ... does not blank the draft", () => {
  const body = ["---", "title: x", "...", "We should utilize this.", ""].join(
    "\n",
  );
  const out = onWrite(draft("technical", body), SHIPPED_RULES);
  assert.match(out ?? "", /line 4: "utilize"/);
});

// A table's separator row is punctuation, like a thematic break. Its dashes
// are not a double hyphen, but the cells around it are still prose.
test("table: the separator row is not checked, its cells are", () => {
  const body = [
    "| Model | Limit |",
    "| ----- | :---: |",
    "|-------|-------|",
    "| clef -- big | 10 |",
  ].join("\n");
  const out = onWrite(draft("technical", body), SHIPPED_RULES) ?? "";
  assert.doesNotMatch(out, /line [23]: double hyphen/);
  assert.match(out, /line 4: double hyphen/);
});

// The technical profile is the one that names flags and code most often. A
// semicolon inside `a = 1; b = 2` is code, not a run-on sentence.
test("inline code: a span in backticks is not checked", () => {
  const out = onWrite(
    draft("technical", "Run `node --test` and set `a = 1; b = 2` in place.\n"),
    SHIPPED_RULES,
  );
  assert.equal(out, null);
});

test("inline code: prose around a span is still checked", () => {
  const out = onWrite(
    draft("technical", "We should utilize `a = 1; b = 2` here.\n"),
    SHIPPED_RULES,
  );
  assert.match(out ?? "", /line 1: "utilize"/);
  assert.doesNotMatch(out ?? "", /semicolon/);
});

// One number cannot serve as both a floor and a rate. Overloading it exempts
// long drafts: 15 em dashes in 5,000 words scored exactly at the limit.
test("density: a long draft is not exempt from the rate", () => {
  const rules = mkdtempSync(join(tmpdir(), "wl-rules-rate-"));
  writeFileSync(
    join(rules, "technical.md"),
    [
      "## Greppable",
      "",
      "```rules",
      "density\t—\t4\t4\ttoo many",
      "```",
      "",
    ].join("\n"),
  );
  // 500 words, 5 marks: 10 per thousand, well over the rate.
  const body = `${Array.from({ length: 5 }, () => "a — b").join("\n")}\n${padding(50)}`;
  assert.match(
    onWrite(draft("technical", body), rules) ?? "",
    /too many \(5 in \d+ words\)/,
  );
});

test("density: the floor still exempts a handful of marks", () => {
  const rules = mkdtempSync(join(tmpdir(), "wl-rules-floor-"));
  writeFileSync(
    join(rules, "technical.md"),
    [
      "## Greppable",
      "",
      "```rules",
      "density\t—\t4\t4\ttoo many",
      "```",
      "",
    ].join("\n"),
  );
  const body = `${Array.from({ length: 3 }, () => "a — b").join("\n")}\n${padding(20)}`;
  assert.equal(onWrite(draft("technical", body), rules), null);
});

// The promotion hook tells Claude to append rules to these files. A rule
// written with spaces instead of tabs looks present and never fires.
test("malformed rules: a bad line is reported, not swallowed", () => {
  const rules = mkdtempSync(join(tmpdir(), "wl-rules-bad-"));
  writeFileSync(
    join(rules, "technical.md"),
    [
      "## Greppable",
      "",
      "```rules",
      "re banned the word banned",
      "re\tfine\tthe word fine",
      "```",
      "",
    ].join("\n"),
  );
  const out = onWrite(draft("technical", "this is fine\n"), rules);
  assert.match(
    out ?? "",
    /the word fine/,
    "the well-formed rule must still fire",
  );
  assert.match(
    out ?? "",
    /rules\/technical\.md.*malformed|malformed.*line 4/i,
    `no malformed notice: ${out}`,
  );
});

test("shipped rules: all three profiles parse", () => {
  for (const profile of ["technical", "mixed", "comms"]) {
    const out = onWrite(draft(profile, "clean prose here\n"), SHIPPED_RULES);
    assert.equal(out, null, `${profile} reported on clean prose: ${out}`);
  }
});

// common.md holds the rules that apply to every profile. The gate loads it
// alongside the profile file, so a rule written once has to fire everywhere.
function withCommon(common, profile) {
  const dir = mkdtempSync(join(tmpdir(), "wl-rules-common-"));
  const block = (lines) =>
    ["## Greppable", "", "```rules", ...lines, "```", ""].join("\n");
  writeFileSync(join(dir, "common.md"), block(common));
  writeFileSync(join(dir, "technical.md"), block(profile));
  return dir;
}

test("common: a rule in common.md fires for a profile that lacks it", () => {
  const rules = withCommon(
    ["re\tbanned\tthe word banned"],
    ["maxwords\t8\ttoo long"],
  );
  const out = onWrite(draft("technical", "this one is banned\n"), rules);
  assert.match(out ?? "", /line 1: the word banned/);
});

test("common: the profile keeps its own rules alongside", () => {
  const rules = withCommon(
    ["re\tbanned\tthe word banned"],
    ["re\tlocal\tthe word local"],
  );
  const out = onWrite(draft("technical", "banned\nlocal\n"), rules);
  assert.match(out ?? "", /line 1: the word banned/);
  assert.match(out ?? "", /line 2: the word local/);
});

// maxwords changes with the audience, so the profile has to win. It is parsed
// second for exactly this reason.
test("common: the profile's maxwords overrides one set in common.md", () => {
  const rules = withCommon(
    ["maxwords\t3\tcommon limit"],
    ["maxwords\t8\tprofile limit"],
  );
  const nine = "one two three four five six seven eight nine.";
  const out = onWrite(draft("technical", nine), rules);
  assert.match(out ?? "", /profile limit/);
  assert.doesNotMatch(out ?? "", /common limit/);
});

test("common: a malformed line names the file it came from", () => {
  const rules = withCommon(
    ["re banned the word banned"],
    ["re\tfine\tthe word fine"],
  );
  const out = onWrite(draft("technical", "this is fine\n"), rules);
  assert.match(
    out ?? "",
    /the word fine/,
    "the well-formed rule must still fire",
  );
  assert.match(
    out ?? "",
    /common\.md line 4/,
    `no file-qualified notice: ${out}`,
  );
});

// A draft under drafts/common/ would otherwise load common.md as both the
// shared file and the profile file, reporting every violation twice.
test("common: a profile named common is not loaded twice", () => {
  const dir = mkdtempSync(join(tmpdir(), "wl-rules-self-"));
  writeFileSync(
    join(dir, "common.md"),
    [
      "## Greppable",
      "",
      "```rules",
      "re\tbanned\tthe word banned",
      "```",
      "",
    ].join("\n"),
  );
  const out = onWrite(draft("common", "this one is banned\n"), dir);
  const reported = (out?.match(/the word banned/g) ?? []).length;
  assert.equal(reported, 1, `expected one report, got ${reported}: ${out}`);
});

test("shipped rules: a common rule fires for every profile", () => {
  for (const profile of ["technical", "mixed", "comms"]) {
    const out = onWrite(
      draft(profile, "We should utilize this.\n"),
      SHIPPED_RULES,
    );
    assert.match(
      out ?? "",
      /line 1: "utilize"/,
      `${profile} did not load common.md`,
    );
  }
});

// html-prose.pl needs HTML::Parser, which macOS perl ships and a bare Linux
// perl may not.
const HAS_HTML_PARSER =
  spawnSync("/usr/bin/perl", ["-MHTML::Parser", "-e", "1"]).status === 0;

function htmlDraft() {
  const root = mkdtempSync(join(tmpdir(), "wl-html-"));
  const dir = join(root, "ai-swap", "drafts", "technical");
  mkdirSync(dir, { recursive: true });
  const path = join(dir, "page.html");
  writeFileSync(
    path,
    [
      "<html><head><style>p { color: red; margin: 0; }</style></head>",
      "<body>",
      "<p>This one is banned.</p>",
      "</body></html>",
      "",
    ].join("\n"),
  );
  return path;
}

// An HTML draft is flattened before the scan, so CSS is not read as prose.
// The flattening goes through a temp file, whose template has to work on the
// mktemp of both macOS and GNU.
test(
  "html: a draft is scanned as prose, not markup",
  { skip: !HAS_HTML_PARSER && "perl has no HTML::Parser" },
  () => {
    const out = onWrite(htmlDraft(), commonPlusBanned());
    assert.match(out ?? "", /line 3: the word banned/);
    assert.doesNotMatch(out ?? "", /semicolon/);
  },
);

// A converter failure must not silence the gate. The raw file is scanned
// instead, noise and all.
test("html: a failing converter falls back to the raw file", () => {
  const bin = mkdtempSync(join(tmpdir(), "wl-bin-broken-"));
  symlinkSync(join(PLUGIN, "bin", "voice-scan.pl"), join(bin, "voice-scan.pl"));
  writeFileSync(join(bin, "html-prose.pl"), "exit 1;\n");
  const result = spawnSync(GATE, {
    input: JSON.stringify({
      tool_name: "Write",
      tool_input: { file_path: htmlDraft() },
    }),
    encoding: "utf-8",
    env: { ...hookEnv({ rules: commonPlusBanned() }), WRITING_LINE_BIN: bin },
  });
  assert.equal(result.status, 0, result.stderr);
  const out = JSON.parse(result.stdout).hookSpecificOutput.additionalContext;
  assert.match(out, /line 3: the word banned/);
  assert.match(out, /line 1: semicolon/, "the raw markup was not scanned");
});

// The shipped common.md plus a fixture rule, so one test can show both that a
// real rule stays quiet on CSS and that the prose is still read.
function commonPlusBanned() {
  const dir = mkdtempSync(join(tmpdir(), "wl-rules-html-"));
  writeFileSync(
    join(dir, "common.md"),
    readFileSync(join(SHIPPED_RULES, "common.md"), "utf-8"),
  );
  writeFileSync(
    join(dir, "technical.md"),
    ["```rules", "re\tbanned\tthe word banned", "```", ""].join("\n"),
  );
  return dir;
}

// --- rules resolution ------------------------------------------------------
// With no override, the user's directory wins if it exists, and replaces the
// plugin defaults whole. Without it, the defaults load.

test("rules: with no override and no user directory, the defaults load", () => {
  const home = mkdtempSync(join(tmpdir(), "wl-home-"));
  const out = gate(
    {
      tool_name: "Write",
      tool_input: {
        file_path: draft("technical", "We should utilize this.\n"),
      },
    },
    null,
    { home },
  );
  assert.match(out ?? "", /line 1: "utilize"/);
});

test("rules: a user directory replaces the defaults whole", () => {
  const home = mkdtempSync(join(tmpdir(), "wl-home-"));
  const user = join(home, ".claude", "writing-line", "rules");
  mkdirSync(user, { recursive: true });
  writeFileSync(
    join(user, "technical.md"),
    ["```rules", "re\tbanned\tthe word banned", "```", ""].join("\n"),
  );
  const out = gate(
    {
      tool_name: "Write",
      tool_input: {
        file_path: draft("technical", "We should utilize this banned idea.\n"),
      },
    },
    null,
    { home },
  );
  assert.match(out ?? "", /line 1: the word banned/);
  assert.doesNotMatch(
    out ?? "",
    /utilize/,
    "the default common.md loaded beside the user's rules",
  );
});

// --- repo markdown ---------------------------------------------------------
// Human-facing markdown outside ai-swap/. The gate checks only the text the
// call wrote, never the whole file, and always against the technical profile.

// Writes a file at <tmp>/repo/<rel> and returns its path. The file on disk
// holds a violation of its own, so a test can tell whether the gate read the
// file or the payload.
function repoFile(rel, onDisk = "this line on disk is banned\n") {
  const root = mkdtempSync(join(tmpdir(), "wl-repo-"));
  const path = join(root, "repo", rel);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, onDisk);
  return path;
}

function onRepoWrite(path, content, rules) {
  return gate(
    { tool_name: "Write", tool_input: { file_path: path, content } },
    rules,
  );
}

test("repo markdown: a Write's content is checked", () => {
  const path = repoFile("docs/guide.md");
  const out = onRepoWrite(path, "fine line\nthis one is banned\n");
  assert.match(out ?? "", /line 2: the word banned/);
  assert.match(out ?? "", /profile "technical", on guide\.md/);
});

test("repo markdown: the report says line numbers count from the new text", () => {
  const out = onRepoWrite(repoFile("README.md"), "banned\n");
  assert.match(out ?? "", /count from the start of the new text/);
  assert.match(out ?? "", /not from the start of the file/);
});

test("repo markdown: clean content says nothing", () => {
  assert.equal(onRepoWrite(repoFile("README.md"), "short and clean\n"), null);
});

test("repo markdown: a .markdown file is checked", () => {
  const out = onRepoWrite(repoFile("docs/guide.markdown"), "banned\n");
  assert.match(out ?? "", /line 1: the word banned/);
});

test("repo markdown: an Edit checks only new_string", () => {
  const path = repoFile("README.md");
  const clean = gate({
    tool_name: "Edit",
    tool_input: {
      file_path: path,
      old_string: "on disk",
      new_string: "a clean line",
    },
  });
  assert.equal(clean, null, "a violation elsewhere in the file was reported");

  const dirty = gate({
    tool_name: "Edit",
    tool_input: {
      file_path: path,
      old_string: "on disk",
      new_string: "ok\nnow banned",
    },
  });
  assert.match(dirty ?? "", /line 2: the word banned/);
  assert.doesNotMatch(dirty ?? "", /edit \d+:/);
});

test("repo markdown: a MultiEdit checks each edit's new_string on its own", () => {
  const out = gate({
    tool_name: "MultiEdit",
    tool_input: {
      file_path: repoFile("README.md"),
      edits: [
        { old_string: "a", new_string: "a clean edit" },
        { old_string: "b", new_string: "ok\nthis one is banned" },
      ],
    },
  });
  assert.match(out ?? "", /edit 2:\nline 2: the word banned/);
  assert.doesNotMatch(out ?? "", /edit 1:/, "a clean edit was reported");
  assert.match(out ?? "", /each edit's new text/);
});

// An unclosed fence in one edit must not blank the next one.
test("repo markdown: a fence in one edit does not carry into the next", () => {
  const out = gate({
    tool_name: "MultiEdit",
    tool_input: {
      file_path: repoFile("README.md"),
      edits: [
        { old_string: "a", new_string: "```js\nconst x = 1;" },
        { old_string: "b", new_string: "banned" },
      ],
    },
  });
  assert.match(out ?? "", /edit 2:\nline 1: the word banned/);
});

test("repo markdown: an Edit that deletes text says nothing", () => {
  const out = gate({
    tool_name: "Edit",
    tool_input: {
      file_path: repoFile("README.md"),
      old_string: "on disk",
      new_string: "",
    },
  });
  assert.equal(out, null);
});

// The branch always uses the technical profile, whatever other rule files sit
// beside it.
test("repo markdown: only the technical profile applies", () => {
  const rules = mkdtempSync(join(tmpdir(), "wl-rules-repo-"));
  const block = (lines) => ["```rules", ...lines, "```", ""].join("\n");
  writeFileSync(
    join(rules, "technical.md"),
    block(["re\ttech\tthe word tech"]),
  );
  writeFileSync(join(rules, "comms.md"), block(["re\tchat\tthe word chat"]));
  const out = onRepoWrite(repoFile("README.md"), "tech\nchat\n", rules);
  assert.match(out ?? "", /line 1: the word tech/);
  assert.doesNotMatch(out ?? "", /the word chat/);
});

test("repo markdown: no technical rule file means no check", () => {
  const rules = mkdtempSync(join(tmpdir(), "wl-rules-none-"));
  writeFileSync(
    join(rules, "comms.md"),
    ["```rules", "re\tbanned\tthe word banned", "```", ""].join("\n"),
  );
  assert.equal(onRepoWrite(repoFile("README.md"), "banned\n", rules), null);
});

// Agent docs are written for a model and keep their own conventions. ai-swap/
// outside drafts/ is scratch until someone decides to share it.
const EXCLUDED = [
  "CLAUDE.md",
  "AGENTS.md",
  "SKILL.md",
  "docs/CLAUDE.md",
  "skills/draft/guide.md",
  "agents/reviewer.md",
  "commands/ship.md",
  "plugins/x/references/terms.md",
  ".claude/notes.md",
  "docs-ai/overview.md",
  "node_modules/pkg/README.md",
  "ai-swap/plan.md",
  "ai-swap/task/notes.md",
];

for (const rel of EXCLUDED) {
  test(`repo markdown: ${rel} is excluded`, () => {
    const path = repoFile(rel);
    assert.equal(onRepoWrite(path, "banned\n"), null);
    assert.equal(
      gate({
        tool_name: "Edit",
        tool_input: { file_path: path, old_string: "x", new_string: "banned" },
      }),
      null,
    );
  });
}

// A segment named like an excluded one, but not equal to it, is still linted.
test("repo markdown: a near-miss segment name is still checked", () => {
  const out = onRepoWrite(repoFile("docs/skills-guide/intro.md"), "banned\n");
  assert.match(out ?? "", /line 1: the word banned/);
});

test("repo markdown: a non-markdown file is ignored", () => {
  for (const rel of ["src/app.js", "notes.txt", "page.html", "README"]) {
    assert.equal(onRepoWrite(repoFile(rel), "banned\n"), null, rel);
  }
});

test("repo markdown: a tool other than Write, Edit or MultiEdit is ignored", () => {
  assert.equal(
    gate({
      tool_name: "NotebookEdit",
      tool_input: { file_path: repoFile("README.md"), new_source: "banned" },
    }),
    null,
  );
});
