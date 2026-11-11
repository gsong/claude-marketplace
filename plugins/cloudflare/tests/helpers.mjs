// Shared by the script suites. Not a test file: CI runs *.test.mjs only.
//
// Each test runs a script as a subprocess with stand-ins for curl, op and
// security. The stand-ins read and write a state directory, so a test
// decides which tokens Cloudflare accepts, what 1Password holds and what the
// Keychain caches, then reads back what each stand-in was asked.

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
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SKILLS = join(dirname(fileURLToPath(import.meta.url)), "..", "skills");
export const CF_API = join(SKILLS, "api", "scripts", "cf-api");
export const SAVE_TOKEN = join(SKILLS, "setup", "scripts", "save-token");

export const GOOD = "good_token_0123456789abcdefghijklmnopqrstuvwxyz";
export const STALE = "stale_token_0123456789abcdefghijklmnopqrstuvwxy";
export const ACCOUNT = "0123456789abcdef0123456789abcdef";
export const REF = "op://Private/item123/credential";

const STUBS = {
  // Reads the Authorization header from the config on stdin, as cf-api
  // sends it. Logs "<method> <url> <token>" and the whole argument list.
  // A token the test did not mark good gets Cloudflare's bad-token answer:
  // 400 with code 9106. A good token gets the reply the test set for
  // "<method> <url>", or 200 with an empty result.
  curl: `
tok=$(sed -n 's/^header = "Authorization: Bearer \\(.*\\)"$/\\1/p')
method=GET url= status_fmt=
while [ $# -gt 0 ]; do
  case $1 in
    -X) method=$2; shift ;;
    -w) status_fmt=1; shift ;;
    -H) shift ;;
    --data-raw) echo "$2" >>"$STUB_STATE/curl-bodies"; shift ;;
    --data|-d|--data-binary) unexpected "$1 $2" ;;
    https://*) url=$1 ;;
  esac
  shift
done
echo "$method $url $tok" >>"$STUB_STATE/curl.log"
if grep -qxF -- "$tok" "$STUB_STATE/good-tokens" 2>/dev/null; then
  reply=$(jq -c --arg k "$method $url" '.[$k] // {status: 200, body: {success: true, result: {}}}' "$STUB_STATE/replies.json")
else
  reply='{"status": 400, "body": {"success": false, "errors": [{"code": 9106, "message": "Authentication failed"}]}}'
fi
printf '%s' "$(jq -c .body <<<"$reply")"
[ -z "$status_fmt" ] || printf '\\n%s' "$(jq -r .status <<<"$reply")"`,
  // read: prints what the test put at the reference.
  // item create: records the template and its mode, answers with an id.
  op: `
echo "$*" >>"$STUB_STATE/op.log"
case "$1 $2" in
  "read "*)
    jq -er --arg r "$2" '.[$r] // empty' "$STUB_STATE/op-secrets.json" || exit 1 ;;
  "item create")
    [ ! -e "$STUB_STATE/op-fails" ] || exit 1
    shift 2
    while [ $# -gt 0 ]; do
      case $1 in
        --vault) vault=$2; shift ;;
        --template) template=$2; shift ;;
      esac
      shift
    done
    jq --arg v "$vault" '. + {vault: $v}' "$template" >"$STUB_STATE/op-created.json"
    stat -c %a "$template" 2>/dev/null >"$STUB_STATE/op-template-mode" || stat -f %Lp "$template" >"$STUB_STATE/op-template-mode"
    echo "$template" >"$STUB_STATE/op-template-path"
    echo '{"id": "newitem456"}' ;;
  *) unexpected "$@" ;;
esac`,
  // A Keychain of one file per service. Logs each argument list, so a test
  // can check the token never reached one. -i reads commands on stdin.
  security: `
echo "$*" >>"$STUB_STATE/security.log"
item="$STUB_STATE/keychain"
case $1 in
  find-generic-password)
    [ -e "$item" ] || exit 44
    [ "\${!#}" != -w ] || cat "$item" ;;
  delete-generic-password)
    [ -e "$item" ] || exit 44
    rm -f "$item" ;;
  -i)
    read -r cmd rest
    [ "$cmd" = add-generic-password ] || unexpected "-i $cmd"
    printf '%s' "\${rest##* -w }" >"$item" ;;
  *) unexpected "$@" ;;
esac`,
};

// A fresh world: a home directory, a working directory, and the stand-ins.
export function world() {
  const root = realpathSync(mkdtempSync(join(tmpdir(), "cloudflare-test-")));
  const dirs = { home: "home", cwd: "repo", bin: "bin", state: "state" };
  for (const [key, name] of Object.entries(dirs)) {
    dirs[key] = join(root, name);
    mkdirSync(dirs[key]);
  }
  for (const [name, body] of Object.entries(STUBS)) {
    const path = join(dirs.bin, name);
    const unexpected = `unexpected() { echo "${name} $*" >>"$STUB_STATE/unexpected"; exit 99; }`;
    writeFileSync(path, `#!/usr/bin/env bash\n${unexpected}\n${body}\n`);
    chmodSync(path, 0o755);
  }
  writeFileSync(join(dirs.state, "replies.json"), "{}");
  writeFileSync(join(dirs.state, "op-secrets.json"), "{}");
  const configFile = join(dirs.home, ".config", "cloudflare-api", "config");
  const read = (name) => {
    const file = join(dirs.state, name);
    return existsSync(file) ? readFileSync(file, "utf8") : "";
  };
  const lines = (name) => read(name).split("\n").filter(Boolean);

  return {
    ...dirs,
    configFile,
    // Cloudflare accepts these tokens.
    acceptsTokens(...tokens) {
      writeFileSync(
        join(dirs.state, "good-tokens"),
        tokens.map((t) => `${t}\n`).join(""),
      );
    },
    // Cloudflare answers "<method> <url>" with this status and body.
    replies(key, status, body) {
      const file = join(dirs.state, "replies.json");
      const all = JSON.parse(readFileSync(file, "utf8"));
      all[key] = { status, body };
      writeFileSync(file, JSON.stringify(all));
    },
    // 1Password holds this value at the reference.
    opHolds(ref, value) {
      const file = join(dirs.state, "op-secrets.json");
      const all = JSON.parse(readFileSync(file, "utf8"));
      all[ref] = value;
      writeFileSync(file, JSON.stringify(all));
    },
    opCreateFails() {
      writeFileSync(join(dirs.state, "op-fails"), "");
    },
    config(text) {
      mkdirSync(dirname(configFile), { recursive: true });
      writeFileSync(configFile, text);
    },
    readConfig() {
      return existsSync(configFile) ? readFileSync(configFile, "utf8") : "";
    },
    cache(token) {
      writeFileSync(join(dirs.state, "keychain"), token);
    },
    cached() {
      return read("keychain") || null;
    },
    curlCalls: () => lines("curl.log"),
    curlBodies: () => lines("curl-bodies"),
    opCalls: () => lines("op.log"),
    securityCalls: () => lines("security.log"),
    opCreated() {
      const text = read("op-created.json");
      return text ? JSON.parse(text) : null;
    },
    opTemplateMode: () => read("op-template-mode").trim(),
    opTemplatePath: () => read("op-template-path").trim(),
    file(path, text) {
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, text);
    },
    // Runs a script with the stand-ins first on PATH. Fails the test when a
    // stand-in was called in a way no test set up.
    run(script, args = [], { env = {}, input = "", cwd = dirs.cwd } = {}) {
      const {
        CLOUDFLARE_API_TOKEN: _t,
        CF_ACCOUNT_ID: _a,
        XDG_CONFIG_HOME: _x,
        ...inherited
      } = process.env;
      const result = spawnSync(script, args, {
        cwd,
        input,
        encoding: "utf8",
        env: {
          ...inherited,
          HOME: dirs.home,
          USER: "tester",
          PATH: `${dirs.bin}:${process.env.PATH}`,
          STUB_STATE: dirs.state,
          ...env,
        },
      });
      const unexpected = read("unexpected");
      assert.equal(unexpected, "", `unexpected stand-in calls:\n${unexpected}`);
      return result;
    },
  };
}
