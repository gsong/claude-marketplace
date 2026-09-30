#!/usr/bin/env bash
# PostToolUse capture for the writing plugin. Pairs each edit Claude makes
# inside a draft with the instruction that caused it, and appends the pair to a
# log. Nothing is classified here. Recurrence sorts style from content later.
#
# Only drafts under ai-swap/drafts/<profile>/ are captured. The profile in the
# path is what tells the Stop hook which rule file a recurring correction
# belongs to.
#
# The hook is silent on stdout. Its whole output is the log line and the fresh
# snapshot it leaves behind.
set -uo pipefail

here=${BASH_SOURCE[0]%/*}
[[ $here == "${BASH_SOURCE[0]}" ]] && here=.
# shellcheck source=lib.sh
source "$here/lib.sh" || exit 0

payload=$(cat)

# Starting jq costs far more than the parse it does here: the jq on PATH is a
# mise shim, which starts mise before jq ever sees the input, about 55ms a
# call. Read every field the hook needs in one run.
#
# A newline inside a value would shift the fields onto each other. Five values
# go in, so any other count means give up rather than log the wrong thing.
fields=()
while IFS= read -r line; do fields+=("$line"); done < <(
  jq -r '.tool_name // "", .tool_input.file_path // "", .prompt_id // "",
         .session_id // "", .transcript_path // ""' <<<"$payload" 2>/dev/null
)
[[ ${#fields[@]} -eq 5 ]] || exit 0
tool=${fields[0]}
file=${fields[1]}
prompt_id=${fields[2]}
session_id=${fields[3]}
transcript=${fields[4]}

case $tool in Write | Edit | MultiEdit) ;; *) exit 0 ;; esac

profile=$(draft_profile "$file") || exit 0

state=$(writing_state_dir)
snapshots=$state/snapshots
mkdir -p "$snapshots" || exit 0

# The snapshot is keyed by path, so two drafts never read as edits of each
# other. The hash keeps the key flat and safe as a filename.
key=$(printf '%s' "$file" | shasum -a 256 | cut -c1-40)
snapshot=$snapshots/$key
snapshot_turn=$snapshots/$key.turn

# Nothing can recover the draft's path from a hash. The Stop hook needs that
# path to tell a snapshot whose draft is still there from one whose draft was
# deleted. Written on every call, so a snapshot taken before this existed
# gains its path the next time the draft is touched.
printf '%s' "$file" >"$snapshots/$key.path" 2>/dev/null

# The first write of a draft has nothing to compare against. Logging it would
# record the whole draft as a correction.
if [[ ! -f $snapshot ]]; then
  cp "$file" "$snapshot" 2>/dev/null
  printf '%s' "$prompt_id" >"$snapshot_turn" 2>/dev/null
  exit 0
fi

cmp -s "$snapshot" "$file" && exit 0

# Claude often writes a draft in two or three calls. Those later calls answer
# the same instruction as the first, so logging them records the topic request
# as a correction, and its words then cluster into a candidate voice rule.
# Only the first change of a turn is a correction. The snapshot still moves
# forward, so the next turn's diff starts from what the user actually read.
if [[ -f $snapshot_turn && $(cat "$snapshot_turn" 2>/dev/null) == "$prompt_id" ]]; then
  cp "$file" "$snapshot" 2>/dev/null
  exit 0
fi

# The removed and added lines, not the whole file. A correction is a few lines,
# and an unbounded field makes the log unreadable.
diff_out=$(diff "$snapshot" "$file" 2>/dev/null)
original=$(sed -n 's/^< //p' <<<"$diff_out")
rewrite=$(sed -n 's/^> //p' <<<"$diff_out")

# The reason is the user's own instruction for this turn. prompt_id holds
# steady from one user prompt to the next, so every edit in a turn pairs with
# the same words. Records of type "user" also carry tool results and injected
# context, which are not the user speaking.
reason=""
if [[ -n $transcript && -f $transcript && -n $prompt_id ]]; then
  reason=$(jq -rn --arg pid "$prompt_id" '
    [ inputs
      | select(.type == "user" and .promptId == $pid)
      | select(has("toolUseResult") | not)
      | select(.isMeta != true)
      | .message.content
      | if type == "string" then .
        else ([.[] | select(.type == "text") | .text] | join("\n"))
        end
      | select(. != null and . != "")
    ] | (first // "")' "$transcript" 2>/dev/null) || reason=""
fi

# Two tool calls in one turn can land together. A directory is the one lock
# primitive that is atomic everywhere and needs no flock binary.
# A run killed between mkdir and its trap leaves the lock behind, and every
# later edit then pays the full retry budget before giving up.
lock=$state/.lock
if [[ -d $lock ]] && [[ -z $(find "$lock" -maxdepth 0 -mmin -1 2>/dev/null) ]]; then
  rmdir "$lock" 2>/dev/null
fi
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if mkdir "$lock" 2>/dev/null; then
    trap 'rmdir "$lock" 2>/dev/null' EXIT
    break
  fi
  sleep 0.05
done

jq -cn \
  --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg session_id "$session_id" \
  --arg prompt_id "$prompt_id" \
  --arg profile "$profile" \
  --arg file "$file" \
  --arg reason "$reason" \
  --arg original "$original" \
  --arg rewrite "$rewrite" \
  '{$timestamp, $session_id, $prompt_id, $profile, $file}
   + {reason: $reason[:2000], original: $original[:2000], rewrite: $rewrite[:2000]}' \
  >>"$state/corrections.jsonl"

cp "$file" "$snapshot" 2>/dev/null
printf '%s' "$prompt_id" >"$snapshot_turn" 2>/dev/null
exit 0
