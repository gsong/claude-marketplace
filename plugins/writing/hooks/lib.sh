# shellcheck shell=bash
# Sourced by the writing hooks. Resolves where the rules and the state live,
# so every hook agrees on one answer.
#
# The rules come from the first directory that exists: an explicit override,
# the user's own copy, then the defaults this plugin ships. The first one found
# replaces the others whole. Merging per file would let a user's comms.md sit
# beside the plugin's common.md, and nobody could tell which rule came from where.

plugin_root=${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}

writing_rules_dir() {
  if [[ -n ${WRITING_LINE_RULES:-} ]]; then
    printf '%s' "$WRITING_LINE_RULES"
  elif [[ -d $HOME/.claude/writing-line/rules ]]; then
    printf '%s' "$HOME/.claude/writing-line/rules"
  else
    printf '%s' "$plugin_root/defaults/rules"
  fi
}

# Prints the profile of a draft under ai-swap/drafts/<profile>/, and fails for
# any other path. The profile is the directory under drafts/. A file sitting
# loose in drafts/ has no profile, so there is nothing to check it against.
draft_profile() {
  local file=$1 rest
  [[ $file == */ai-swap/drafts/* && -f $file ]] || return 1
  rest=${file#*/ai-swap/drafts/}
  [[ ${rest%%/*} != "$rest" ]] || return 1
  printf '%s' "${rest%%/*}"
}

# State lives outside the plugin on purpose. CLAUDE_PLUGIN_DATA is deleted when
# the plugin is uninstalled, and the correction log is the user's history.
writing_state_dir() {
  printf '%s' "${WRITING_LINE_STATE:-$HOME/.claude/state/writing-line}"
}

writing_bin_dir() {
  printf '%s' "${WRITING_LINE_BIN:-$plugin_root/bin}"
}

# Hooks may run without a login shell, where a perl that mise or Homebrew put
# on PATH is missing. /usr/bin/perl needs no PATH, so it comes first. PATH is
# the fallback where it is absent, as on some Linux images.
writing_perl() {
  if [[ -x /usr/bin/perl ]]; then
    printf '%s' /usr/bin/perl
  else
    printf '%s' perl
  fi
}
