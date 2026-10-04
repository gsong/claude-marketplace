#!/usr/bin/env bash
# PreToolUse hook: approve a plain call of this plugin's clef.py, so the clef:ask
# skill runs it with no Bash prompt.
#
# Claude Code 2.1.289 drops a skill's `allowed-tools` rule in most turns. So
# this hook approves the calls. #62 tracks when the rule can take over. The
# plugin README says why clef:ask has no `allowed-tools` line: see #66.
#
# This pattern decides which commands skip the prompt. It approves two shapes:
#
#   <root>/skills/ask/scripts/clef.py [flags] [< file]
#   printf '%s' '<text>' | <root>/skills/ask/scripts/clef.py [flags]
#
# Flags come from a whitelist of clef.py's own. `--out` writes a file, so it is
# left out, and so is any shortened flag. A flag value is a plain word or
# single-quoted text. Neither a redirect nor a path flag may name a file under
# /dev/ or /proc/. bash opens a network connection for a redirect from
# /dev/tcp/HOST/PORT, and clef.py can read a device forever or block on it.
# Every other command, and every failure, exits 0 with no output, which leaves
# Claude Code's normal prompt.
set -uo pipefail
# Character classes match ASCII only. In a UTF-8 locale, [[:space:]] matches a
# no-break space, which bash does not split words on.
LC_ALL=C

payload=$(cat)
# Most Bash calls never mention clef.py. They leave here before jq runs.
[[ $payload == *clef.py* ]] || exit 0
# The command holds the root unquoted, so a root with a space or a shell
# character would not run as the path it names.
[[ ${CLAUDE_PLUGIN_ROOT:-} =~ ^[-A-Za-z0-9_.@+/]+$ ]] || exit 0
command -v jq >/dev/null || exit 0
# $(…) drops a NUL, so a command that holds one yields nothing.
cmd=$(jq -r 'select(.tool_name == "Bash") | .tool_input.command | strings
  | select(explode | all(. != 0))' <<<"$payload" 2>/dev/null) || exit 0

script="$CLAUDE_PLUGIN_ROOT/skills/ask/scripts/clef.py"
apos="'"
word='[A-Za-z0-9_.:/][-A-Za-z0-9_.:/]*'
value="($word|${apos}[^${apos}-][^${apos}]*${apos})"
flag="(--(model|image|state-file|timeout|guess|batch|ids|lines)(=$value| +$value)|-h|--help)"
flags="( +$flag)*"
# Single-quoted text, where '\'' stands for an apostrophe.
text="${apos}([^${apos}]|${apos}\\\\${apos}${apos})*${apos}"
redirect="( +< *($word))?"
pipe_in="^printf +${apos}%s${apos} +${text}[[:blank:]]*\\|[[:space:]]*"
end='$'
# A redirect or path flag whose file is under /dev/ or /proc/, also by way of
# //, /./ or ../ at its start. This may match inside quoted text too, which only
# costs a prompt.
device="(<|--(image|state-file|batch)=?) *${apos}?(/|(\\./)*\\.\\./)[./]*(dev|proc)/"

approve() {
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"clef:ask call of clef.py"}}'
}

# A quoted "$script" matches literally; the unquoted parts are regexes.
[[ ${cmd#*"$script"} =~ $device ]] && exit 0
if [[ $cmd =~ ^"$script"$flags$redirect$end || $cmd =~ $pipe_in"$script"$flags$end ]]; then
  approve
fi
exit 0
