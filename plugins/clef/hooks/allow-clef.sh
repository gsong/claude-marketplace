#!/usr/bin/env bash
# PreToolUse hook: approve a plain call of this plugin's clef.py, so the clef:ask
# skill runs it with no Bash prompt.
#
# The skill's `allowed-tools` rule should do this alone. Claude Code 2.1.289
# drops that rule in most turns: see #62. Remove this hook once the
# rule holds.
#
# This pattern decides which commands skip the prompt. It approves two shapes:
#
#   <root>/skills/ask/scripts/clef.py [flags] [< file]
#   printf '%s' '<text>' | <root>/skills/ask/scripts/clef.py [flags]
#
# Flags come from a whitelist of clef.py's own. `--out` writes a file, so it is
# left out, and so is any shortened flag. A flag value is a plain word or
# single-quoted text. Every other command, and every failure, exits 0 with no
# output, which leaves Claude Code's normal prompt.
set -uo pipefail

payload=$(cat)
# Most Bash calls never mention clef.py. They leave here before jq runs.
[[ $payload == *clef.py* ]] || exit 0
[[ -n ${CLAUDE_PLUGIN_ROOT:-} ]] || exit 0
command -v jq >/dev/null || exit 0
cmd=$(jq -r '.tool_input.command // empty' <<<"$payload" 2>/dev/null) || exit 0

script="$CLAUDE_PLUGIN_ROOT/skills/ask/scripts/clef.py"
apos="'"
word='[A-Za-z0-9_.:/][-A-Za-z0-9_.:/]*'
value="($word|${apos}[^${apos}-][^${apos}]*${apos})"
flag="(--(model|image|state-file|timeout|guess|batch)(=$value| +$value)|-h|--help)"
flags="( +$flag)*"
# Single-quoted text, where '\'' stands for an apostrophe.
text="${apos}([^${apos}]|${apos}\\\\${apos}${apos})*${apos}"
redirect="( +< *$word)?"
pipe_in="^printf +${apos}%s${apos} +${text}[[:blank:]]*\\|[[:space:]]*"
end='$'

# A quoted "$script" matches literally; the unquoted parts are regexes.
if [[ $cmd =~ ^"$script"$flags$redirect$end ]] ||
  [[ $cmd =~ $pipe_in"$script"$flags$end ]]; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"clef:ask call of clef.py"}}'
fi
exit 0
