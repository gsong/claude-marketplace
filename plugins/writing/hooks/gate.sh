#!/usr/bin/env bash
# PostToolUse voice gate for the writing plugin. It checks prose Claude just
# wrote against common.md plus the rule file for a profile, and reports
# violations as advisory feedback. It never blocks: the write has already
# landed, and a gate that stops work gets switched off.
#
# Two kinds of file are checked:
#   - A draft under ai-swap/drafts/<profile>/. The whole file on disk is
#     scanned against that profile.
#   - Human-facing repo markdown. Only the text this call wrote is scanned,
#     against the technical profile. The rest of the file may predate the rules
#     or belong to someone else, and reporting it would bury the new text.
#
# The scan lives in bin/voice-scan.pl. It is perl because the rule files use \b
# and other Perl-style regex. The awk and grep that ship with macOS are POSIX
# and do not support it.
set -uo pipefail

here=${BASH_SOURCE[0]%/*}
[[ $here == "${BASH_SOURCE[0]}" ]] && here=.
# shellcheck source=lib.sh
source "$here/lib.sh" || exit 0

payload=$(cat)

# Starting jq costs far more than the parse: the jq on PATH is a mise shim,
# which starts mise before jq ever sees the input, about 60ms a call. Read
# every field in one run. The new text of a markdown edit spans lines, so the
# fields are NUL-terminated rather than newline-terminated. The third field is
# how many texts follow. A NUL inside a value would shift the fields, so any
# count but the expected one means give up.
#
# Only a markdown path carries its text out of jq. Bash reads a pipe one byte
# at a time, and the content of every large Write would otherwise pay for it.
fields=()
while IFS= read -r -d '' field; do fields+=("$field"); done < <(
  jq -j '
    (.tool_name // "") as $tool
    | (.tool_input.file_path // "") as $file
    | (if ($file | test("\\.(md|markdown)$")) then
         [ if $tool == "Write" then .tool_input.content
           elif $tool == "Edit" then .tool_input.new_string
           elif $tool == "MultiEdit" then (.tool_input.edits // [])[].new_string
           else empty end
           | strings ]
       else [] end) as $texts
    | ([$tool, $file, ($texts | length | tostring)] + $texts)[]
    | . + "\u0000"
  ' <<<"$payload" 2>/dev/null
)
[[ ${#fields[@]} -ge 3 ]] || exit 0
tool=${fields[0]}
file=${fields[1]}
count=${fields[2]}
[[ $count =~ ^[0-9]+$ && ${#fields[@]} -eq $((count + 3)) ]] || exit 0

case $tool in Write | Edit | MultiEdit) ;; *) exit 0 ;; esac

rules_dir=$(writing_rules_dir)
bin_dir=$(writing_bin_dir)
scanner=$bin_dir/voice-scan.pl
[[ -f $scanner ]] || exit 0

# common.md carries the rules that hold for every profile. It is loaded first so
# the profile file, parsed second, wins on maxwords. The guard keeps a draft
# under drafts/common/ from loading the same file twice and double-reporting.
rule_files_for() {
  local rules=$rules_dir/$1.md
  rule_files=()
  [[ -f $rules ]] || return 1
  [[ -f $rules_dir/common.md && $rules != "$rules_dir/common.md" ]] &&
    rule_files+=("$rules_dir/common.md")
  rule_files+=("$rules")
}

emit() {
  local context="$1

$2

Advisory only. Fix what is a real violation. Ignore what the rule misread, and
say so if the same rule misreads twice."
  jq -Rn --arg c "$context" \
    '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $c}}'
  exit 0
}

# --- draft ---------------------------------------------------------------
if [[ $file == */ai-swap/drafts/* ]]; then
  [[ -f $file ]] || exit 0

  # The profile is the directory under drafts/. A file sitting loose in drafts/
  # has no profile, so there is nothing to check it against.
  rest=${file#*/ai-swap/drafts/}
  profile=${rest%%/*}
  [[ $profile != "$rest" ]] || exit 0
  rule_files_for "$profile" || exit 0

  # An HTML draft is markup, not prose. Flatten it before scanning: otherwise the
  # scanner measures CSS declarations, counts `&mdash;` as nothing, and cuts every
  # sentence at the source line wrap. The converter puts each block of prose on
  # the line where that block starts, so the numbers below still point into the
  # file the writer edits.
  scan=$file
  converter=$bin_dir/html-prose.pl
  if [[ $file == *.html || $file == *.htm ]] && [[ -f $converter ]]; then
    # mktemp -t means different things on macOS and GNU. A full template works
    # on both, so the gate runs the same on a Linux CI runner.
    if tmp=$(mktemp "${TMPDIR:-/tmp}/writing-line.XXXXXX"); then
      trap 'rm -f "$tmp"' EXIT
      # A converter failure must not silence the gate, so fall back to the raw file.
      if /usr/bin/perl "$converter" "$file" >"$tmp" 2>/dev/null && [[ -s $tmp ]]; then
        scan=$tmp
      fi
    fi
  fi

  report=$(/usr/bin/perl "$scanner" "${rule_files[@]}" "$scan" 2>/dev/null)
  [[ -z $report ]] && exit 0
  emit "writing gate, profile \"$profile\", on ${file##*/}:" "$report"
fi

# --- repo markdown -------------------------------------------------------
# Human-facing markdown in a repo: a README, a guide, a changelog. Agent docs
# are written for a model, not a reader, so they keep their own conventions.
# ai-swap/ outside drafts/ is scratch until someone decides to share it, and a
# draft meant for sharing already goes through the branch above.
case $file in *.md | *.markdown) ;; *) exit 0 ;; esac
case ${file##*/} in CLAUDE.md | AGENTS.md | SKILL.md) exit 0 ;; esac
# The leading slash lets a relative path match the same patterns.
case /$file in
  */ai-swap/* | */skills/* | */agents/* | */commands/* | */references/* | \
    */.claude/* | */docs-ai/* | */node_modules/*) exit 0 ;;
esac
[[ $count -gt 0 ]] || exit 0
rule_files_for technical || exit 0

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/writing-line.XXXXXX") || exit 0
trap 'rm -rf "$tmp_dir"' EXIT

# Each edit of a MultiEdit is scanned on its own. Joined, an unclosed fence in
# one edit would blank the next, and no line number would point anywhere the
# writer can find.
report=""
for ((i = 1; i <= count; i++)); do
  text=${fields[i + 2]}
  [[ $text =~ [^[:space:]] ]] || continue
  printf '%s\n' "$text" >"$tmp_dir/$i.md" || continue
  out=$(/usr/bin/perl "$scanner" "${rule_files[@]}" "$tmp_dir/$i.md" 2>/dev/null)
  [[ -n $out ]] || continue
  ((count > 1)) && out="edit $i:
$out"
  report+=${report:+$'\n\n'}$out
done
[[ -z $report ]] && exit 0

if ((count > 1)); then
  scope="each edit's new text"
else
  scope="the new text"
fi
emit "writing gate, profile \"technical\", on ${file##*/}.
Only the text this $tool wrote was checked.
Line numbers count from the start of $scope, not from the start of the file:" "$report"
