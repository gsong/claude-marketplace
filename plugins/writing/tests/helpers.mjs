// Shared by the hook suites. Not a test file: CI runs *.test.mjs only.

import { existsSync, mkdtempSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PLUGIN = join(dirname(fileURLToPath(import.meta.url)), "..");

// A jq reached through a mise shim reads its trust list from HOME, so it
// fails under the stand-in HOME some tests use. Those runs get a directory
// first on PATH that holds only the first jq on PATH that is not a shim.
export const JQ_DIR = (() => {
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

// The environment a hook sees. Any WRITING_LINE_* the caller has set is
// dropped, so only the test decides where state and rules come from. Leaving
// state or rules out, or passing rules as null, leaves that variable unset.
// The rules then resolve through HOME, which such a test points at a
// directory it controls.
export function hookEnv({ state, rules, home } = {}) {
  const env = { ...process.env, CLAUDE_PLUGIN_ROOT: PLUGIN };
  for (const key of Object.keys(env)) {
    if (key.startsWith("WRITING_LINE_")) delete env[key];
  }
  if (state !== undefined) env.WRITING_LINE_STATE = state;
  if (rules !== undefined && rules !== null) env.WRITING_LINE_RULES = rules;
  if (home !== undefined) {
    env.HOME = home;
    if (JQ_DIR) env.PATH = `${JQ_DIR}:${env.PATH}`;
  }
  return env;
}
