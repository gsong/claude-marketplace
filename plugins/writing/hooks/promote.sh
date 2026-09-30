#!/usr/bin/env bash
# Stop hook for the writing plugin. Counts the corrections the capture hook
# logged and stays silent until one pattern has recurred. Then it surfaces that
# pattern once and asks the user where it belongs.
#
# One decision per pattern, not per correction. A one-off never recurs, so it
# never costs the user a decision.
set -uo pipefail

here=${BASH_SOURCE[0]%/*}
[[ $here == "${BASH_SOURCE[0]}" ]] && here=.
# shellcheck source=lib.sh
source "$here/lib.sh" || exit 0

payload=$(cat)

# The Stop hook fires again after it blocks. Without this the hook loops.
[[ $(jq -r '.stop_hook_active // false' <<<"$payload" 2>/dev/null) == "true" ]] && exit 0

state=$(writing_state_dir)

# A draft that is written and then deleted leaves its snapshot behind. The next
# draft at that path is a fresh start, but the stale snapshot makes the capture
# hook diff the new draft against the old one and log the whole thing as a
# correction. Those words then feed the pattern count below and invent a rule
# out of a file that was never corrected. Sweeping here rather than in the
# capture hook is what makes it work: PostToolUse fires after the write, when
# the path exists again, so only the end of the turn sees the draft gone.
for path_file in "$state"/snapshots/*.path; do
  [[ -f $path_file ]] || continue
  draft=$(cat "$path_file" 2>/dev/null)
  # An unreadable or empty sidecar proves nothing. Leave that snapshot alone.
  [[ -n $draft && ! -e $draft ]] || continue
  key=${path_file%.path}
  rm -f "$key" "$key.turn" "$path_file"
done

log=$state/corrections.jsonl
[[ -f $log ]] || exit 0

# A new rule goes where the gate will read it. The plugin's own defaults are
# the one exception: an update of the plugin replaces them, and the rule with
# them. So when the defaults are in use, the rule goes to the user's directory,
# seeded with a copy of the defaults. That directory replaces the defaults
# whole, so a lone profile file there would drop every other rule.
rules_dir=$(writing_rules_dir)
seed_from=""
if [[ $rules_dir == "$plugin_root/defaults/rules" ]]; then
  seed_from=$rules_dir
  rules_dir=$HOME/.claude/writing-line/rules
fi

reason=$("$(writing_perl)" "$(writing_bin_dir)/promote.pl" \
  "$log" "$state/surfaced.txt" "$rules_dir" "$seed_from")

[[ -z $reason ]] && exit 0

jq -Rn --arg r "$reason" '{decision: "block", reason: $r}'
exit 0
