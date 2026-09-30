#!/usr/bin/env bash
# PreToolUse prefilter for send-lint.py. The hook matcher sends every Bash call
# here, because `gh pr comment` is a Bash call like any other. Starting uv and
# Python costs far more than the lint, so a Bash command that never mentions gh
# leaves here, with no jq and no uv, before anything else runs.
#
# The test is a regex over the raw payload, not a parse. A false positive (gh in
# a description, say) only costs one uv start: send-lint.py decides for real.
#
# Every failure exits 0 with no output. A broken lint must never block a send.
set -uo pipefail

payload=$(cat)

bash_tool='"tool_name"[[:space:]]*:[[:space:]]*"Bash"'
# The payload is raw JSON, so a newline or tab before gh arrives as `\n` or `\t`.
gh_word='(^|[^[:alnum:]_.-]|\\[ntr])gh[[:space:]]'
if [[ $payload =~ $bash_tool ]] && ! [[ $payload =~ $gh_word ]]; then
  exit 0
fi

# uv is mise-managed and may be missing from a non-login PATH. Without it the
# shebang fails loudly, so check first and stay silent.
command -v uv >/dev/null 2>&1 || exit 0

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
printf '%s' "$payload" | "$here/send-lint.py" 2>/dev/null
exit 0
