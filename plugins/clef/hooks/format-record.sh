#!/usr/bin/env bash
# PostToolUse hook for the clef plugin. After a write to a record under
# clef-opportunities/, it formats the record with prettier, so a repo that
# checks formatting in CI accepts the record as written.
#
# It runs only a prettier that is already installed: the one in
# node_modules/.bin of the directory that holds clef-opportunities/, else one
# on PATH. It never fetches one. Without prettier or jq it does nothing, and
# it never blocks the write.
set -uo pipefail

command -v jq &>/dev/null || exit 0

file=$(jq -r '.tool_input.file_path // empty')
# The leading slash lets a relative path such as clef-opportunities/x.md match.
[[ /$file == */clef-opportunities/*.md ]] || exit 0
[[ -f $file ]] || exit 0

root=${file%/clef-opportunities/*}
[[ $root == "$file" ]] && root=.
prettier="$root/node_modules/.bin/prettier"
if [[ ! -x $prettier ]]; then
  prettier=$(command -v prettier) || exit 0
fi

# The project's prettier config and .prettierignore still apply.
"$prettier" --write --log-level warn "$file" >/dev/null 2>&1
exit 0
