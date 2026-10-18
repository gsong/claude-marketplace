// Shared by the script suites. Not a test file: CI runs *.test.mjs only.
//
// Each test runs a script as a subprocess with stand-ins for the commands
// that touch the Mac: uname, curl, ps and open. The stand-ins read and write
// a state directory, so a test decides which ports answer and which Chrome
// processes ps lists, then reads back what open was asked to start.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPTS = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "skills",
  "chrome",
  "scripts",
);

export const CHROME =
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const STUBS = {
  uname: `echo "\${STUB_UNAME:-Darwin}"`,
  // Logs its arguments, one call per line. Knows two probes: Chrome's
  // DevTools endpoint, /json/version, and the bare port, /. Answers as the
  // test, or the open stand-in, set the port: up, or timed out (exit 28). A
  // port with no state refuses the connection (exit 7).
  curl: `
echo "$*" >>"$STUB_STATE/curl.log"
url='http://127\\.0\\.0\\.1:([0-9]+)'
devtools="^-sf --max-time 1 $url/json/version\\$"
bare="^-s --max-time 1 $url/\\$"
if [[ $* =~ $devtools ]]; then
  reply='{"Browser": "Chrome"}'
elif [[ $* =~ $bare ]]; then
  reply=
else
  unexpected "$@"
fi
case $(cat "$STUB_STATE/port-\${BASH_REMATCH[1]}" 2>/dev/null) in
  up) [ -z "$reply" ] || echo "$reply" ;;
  timeout) exit 28 ;;
  *) exit 7 ;;
esac`,
  // Lists the processes the test set up, when asked for the columns the test
  // wrote them in. A list with no processes looks the same in any columns.
  ps: `
[ $# -eq 2 ] && [ "$1" = -axo ] || unexpected "$@"
[ -e "$STUB_STATE/ps" ] || exit 0
[ "$2" = "$(cat "$STUB_STATE/ps-columns")" ] || unexpected "$@"
cat "$STUB_STATE/ps"`,
  // Logs its arguments, one per line, with a blank line after each call.
  // When the test allows it, Chrome comes up on the port it was given.
  open: `
printf '%s\\n' "$@" >>"$STUB_STATE/open.log"
echo >>"$STUB_STATE/open.log"
[ -e "$STUB_STATE/open-starts" ] || exit 0
for arg; do
  case $arg in --remote-debugging-port=*) echo up >"$STUB_STATE/port-\${arg#*=}" ;; esac
done`,
};

// A fresh world: a home directory, a working directory, and the stand-ins.
export function world() {
  // The physical path: macOS reaches the temp directory through a symlink.
  const root = realpathSync(mkdtempSync(join(tmpdir(), "browser-test-")));
  const dirs = { home: "home", cwd: "repo", bin: "bin", state: "state" };
  for (const [key, name] of Object.entries(dirs)) {
    dirs[key] = join(root, name);
    mkdirSync(dirs[key]);
  }
  for (const [name, body] of Object.entries(STUBS)) {
    const path = join(dirs.bin, name);
    // A call no test set up goes to a log that run() turns into a failure.
    // The script under test may ignore the stand-in's exit status, so the
    // exit status, 99, only stops the stand-in.
    const unexpected = `unexpected() { echo "${name} $*" >>"$STUB_STATE/unexpected"; exit 99; }`;
    writeFileSync(path, `#!/usr/bin/env bash\n${unexpected}\n${body}\n`);
    chmodSync(path, 0o755);
  }
  return {
    ...dirs,
    sidecar(json) {
      writeFileSync(join(dirs.cwd, "agent-browser.json"), json);
    },
    portUp(port) {
      writeFileSync(join(dirs.state, `port-${port}`), "up");
    },
    // A program holds the port but never replies.
    portTimesOut(port) {
      writeFileSync(join(dirs.state, `port-${port}`), "timeout");
    },
    isUp(port) {
      const file = join(dirs.state, `port-${port}`);
      return existsSync(file) && readFileSync(file, "utf8").trim() === "up";
    },
    chromeStartsOnOpen() {
      writeFileSync(join(dirs.state, "open-starts"), "");
    },
    // The command lines ps -axo command= lists.
    psLists(...lines) {
      psShows(dirs.state, "command=", lines);
    },
    // The "<pid> <command line>" lines ps -axo pid=,command= lists.
    psListsWithPids(...lines) {
      psShows(dirs.state, "pid=,command=", lines);
    },
    // The port registry, ~/.agent-browser/ports: one "<port> <profile>" line
    // per repo.
    registryHolds(...lines) {
      mkdirSync(join(dirs.home, ".agent-browser"), { recursive: true });
      writeFileSync(
        join(dirs.home, ".agent-browser", "ports"),
        lines.map((l) => `${l}\n`).join(""),
      );
    },
    registry() {
      const file = join(dirs.home, ".agent-browser", "ports");
      if (!existsSync(file)) return [];
      return readFileSync(file, "utf8").split("\n").filter(Boolean);
    },
    // The argument lists open was called with, one array per call.
    openCalls() {
      const log = join(dirs.state, "open.log");
      if (!existsSync(log)) return [];
      return readFileSync(log, "utf8")
        .split("\n\n")
        .filter((call) => call.trim())
        .map((call) => call.split("\n").filter(Boolean));
    },
    // The argument lists curl was called with, one string per call.
    curlCalls() {
      const log = join(dirs.state, "curl.log");
      if (!existsSync(log)) return [];
      return readFileSync(log, "utf8").split("\n").filter(Boolean);
    },
    // Runs a script by its name in the scripts directory, or by its full
    // path. Fails the test when the script called a stand-in in a way the
    // test did not set up.
    run(script, args = [], env = {}) {
      const result = spawnSync(resolve(SCRIPTS, script), args, {
        cwd: dirs.cwd,
        encoding: "utf8",
        env: {
          ...process.env,
          HOME: dirs.home,
          PATH: `${dirs.bin}:${process.env.PATH}`,
          STUB_STATE: dirs.state,
          ...env,
        },
      });
      const log = join(dirs.state, "unexpected");
      if (existsSync(log)) {
        assert.fail(`unexpected call: ${readFileSync(log, "utf8").trim()}`);
      }
      return result;
    },
  };
}

// Sets what ps -axo <columns> lists. The ps stand-in refuses other columns.
function psShows(state, columns, lines) {
  writeFileSync(join(state, "ps-columns"), columns);
  writeFileSync(join(state, "ps"), lines.map((l) => `${l}\n`).join(""));
}
