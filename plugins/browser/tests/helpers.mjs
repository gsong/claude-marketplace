// Shared by the script suites. Not a test file: CI runs *.test.mjs only.
//
// Each test runs a script as a subprocess with stand-ins for the commands
// that touch the Mac: uname, curl, ps and open. The stand-ins read and write
// a state directory, so a test decides which ports answer and which Chrome
// processes ps lists, then reads back what open was asked to start.

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
import { dirname, join } from "node:path";
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
  // Answers when the test, or the open stand-in, marked the port as up.
  curl: `
for arg; do url=$arg; done
port=\${url##*:}
port=\${port%%/*}
[ -e "$STUB_STATE/up-$port" ] || exit 7
echo '{}'`,
  ps: `cat "$STUB_STATE/ps" 2>/dev/null; exit 0`,
  // Logs its arguments, one per line, with a blank line after each call.
  // When the test allows it, Chrome comes up on the port it was given.
  open: `
printf '%s\\n' "$@" >>"$STUB_STATE/open.log"
echo >>"$STUB_STATE/open.log"
[ -e "$STUB_STATE/open-starts" ] || exit 0
for arg; do
  case $arg in --remote-debugging-port=*) touch "$STUB_STATE/up-\${arg#*=}" ;; esac
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
    writeFileSync(path, `#!/usr/bin/env bash\n${body}\n`);
    chmodSync(path, 0o755);
  }
  return {
    ...dirs,
    sidecar(json) {
      writeFileSync(join(dirs.cwd, "agent-browser.json"), json);
    },
    portUp(port) {
      writeFileSync(join(dirs.state, `up-${port}`), "");
    },
    isUp(port) {
      return existsSync(join(dirs.state, `up-${port}`));
    },
    chromeStartsOnOpen() {
      writeFileSync(join(dirs.state, "open-starts"), "");
    },
    psLists(...lines) {
      writeFileSync(
        join(dirs.state, "ps"),
        lines.map((l) => `${l}\n`).join(""),
      );
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
    run(script, args = [], env = {}) {
      return spawnSync(join(SCRIPTS, script), args, {
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
    },
  };
}
