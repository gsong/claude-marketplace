# shellcheck shell=bash
# Answers the Chrome questions that browser-start, scratch-chrome, ports and
# setup share. Each script sources this file and keeps only its own decisions.

# How long chrome_wait waits for Chrome to answer, in seconds.
chrome_wait_seconds=${CHROME_WAIT_SECONDS:-15}

# The port registry: one "<port> <chromeProfile>" line per repo. ports keeps
# it, and setup reads it before it claims a port.
registry=$HOME/.agent-browser/ports

# Says what check_name allows, for a message.
# shellcheck disable=SC2034 # the scripts that source this file read it
name_rule='A profile name holds only lowercase letters, digits, ".", "_" and "-", such as "people-matcher".'

# Succeeds when the name may name a profile. The name becomes a directory
# under ~/.agent-browser/profiles, so it is neither . nor .. and holds no
# slash. It is a field in a registry line, so it holds no space. It holds no
# capitals, because the Mac's disk ignores case: MyRepo and myrepo would share
# one profile directory, but get two registry lines and two ports.
check_name() {
  case $1 in
    "" | . | .. | *[!abcdefghijklmnopqrstuvwxyz0123456789._-]*) return 1 ;;
  esac
}

# Prints the port the registry gives the profile, or nothing.
port_for_name() {
  [ ! -f "$registry" ] || awk -v name="$1" '$2 == name { print $1; exit }' "$registry"
}

# Prints the profile the registry gives the port to, or nothing.
name_for_port() {
  [ ! -f "$registry" ] || awk -v port="$1" '$1 == port { print $2; exit }' "$registry"
}

# Fails, with a message, when jq is missing. jq reads and writes every JSON
# file the scripts touch.
need_jq() {
  command -v jq >/dev/null && return 0
  echo "jq is missing. macOS 15 and later ship it as /usr/bin/jq. On an older Mac, install it, such as with: brew install jq" >&2
  return 1
}

# Reads agent-browser.json, the file at $1, into sidecar_port and
# sidecar_name. cdp may be a string or a number. Fails, with the reason on
# stderr, when the file is not a JSON object, names no cdp port, or names a
# chromeProfile that fails check_name.
read_sidecar() {
  need_jq || return 1
  if ! sidecar_port=$(jq -r '.cdp // "" | tostring' "$1" 2>/dev/null); then
    echo "$1 is not a JSON object." >&2
    return 1
  fi
  sidecar_name=$(jq -r '.chromeProfile // "" | tostring' "$1")
  case $sidecar_port in
    "" | *[!0123456789]*)
      echo "$1 names no cdp port." >&2
      return 1
      ;;
  esac
  if ! check_name "$sidecar_name"; then
    echo "$1 needs a chromeProfile that names one directory under ~/.agent-browser/profiles. $name_rule" >&2
    return 1
  fi
}

# Writes agent-browser.json, the file at $1, for the port $2 and the profile
# $3. agent-browser reads contentBoundary; the scripts read the other two.
write_sidecar() {
  jq -n --arg cdp "$2" --arg name "$3" \
    '{cdp: $cdp, contentBoundary: true, chromeProfile: $name}' >"$1"
}

# Succeeds when the session runs in the container, not on the Mac: when
# AGENT_BROWSER_CDP is set, even to nothing, or the OS is not macOS. The
# container reaches the Mac's Chrome through AGENT_BROWSER_CDP, and never
# launches Chrome itself.
in_container() {
  [ -n "${AGENT_BROWSER_CDP+set}" ] || [ "$(uname)" != Darwin ]
}

# Says why in_container counts the session as the container, for a message.
# shellcheck disable=SC2034 # the scripts that source this file read it
container_rule="this session counts as the container: AGENT_BROWSER_CDP is set, or the OS is not macOS"

# Succeeds when Chrome's DevTools endpoint answers on the port.
chrome_answers() {
  cdp_answers "http://127.0.0.1:$1"
}

# Succeeds when Chrome's DevTools endpoint answers at the base URL, such as
# http://host.docker.internal:10082.
cdp_answers() {
  curl -sf --max-time 1 "$1/json/version" >/dev/null
}

# Succeeds when no program at all holds the port. curl exits 7 only when
# nothing accepts the connection. Any other exit means a program holds the
# port, even one that times out or replies without HTTP.
port_unused() {
  local status=0
  curl -s --max-time 1 "http://127.0.0.1:$1/" >/dev/null || status=$?
  [ "$status" -eq 7 ]
}

# Prints the command line of the Chrome browser process on the port, or fails
# when none shows in ps.
chrome_on_port() {
  local line
  line=$(chrome_processes command= | lines_with_flag "--remote-debugging-port=$1" | head -n 1)
  [ -n "$line" ] && echo "$line"
}

# Succeeds when the command line runs Chrome on the profile directory. It
# matches the path exactly, so a path that contains " --" still matches.
chrome_runs_profile() {
  [ -n "$(echo "$1" | lines_with_flag "--user-data-dir=$2" "--user-data-dir=$2/")" ]
}

# Prints the profile directory a command line names, for a message. It prints
# nothing for Chrome's default profile. A path that contains " --" comes out
# cut short, so compare paths with chrome_runs_profile instead.
chrome_profile_of() {
  case $1 in
    *--user-data-dir=*)
      local profile=${1#*--user-data-dir=}
      echo "${profile%% --*}"
      ;;
  esac
}

# Prints the PID of each Chrome browser process on the profile directory.
chrome_pids_on_profile() {
  chrome_processes pid=,command= | lines_with_flag "--user-data-dir=$1" | awk '{ print $1 }'
}

# Prints each port that a running Chrome debugs on.
chrome_debug_ports() {
  chrome_processes command= | grep -oE -- '--remote-debugging-port=[0-9]+' | cut -d= -f2 || true
}

# Opens a new Chrome on the port and profile directory. Further arguments are
# extra Chrome flags. agent-browser skips chrome://newtab and chrome://intro.
# Finding no other tab, its first session opens two blank tabs and abandons
# one, so Chrome starts on a tab it uses. --no-first-run keeps a new profile
# off chrome://intro.
chrome_open() {
  local port=$1 profile=$2
  shift 2
  open -na "Google Chrome" --args --remote-debugging-port="$port" \
    --user-data-dir="$profile" --no-first-run "$@" about:blank
}

# Waits until Chrome answers on the port. Fails after chrome_wait_seconds; the
# caller says why.
chrome_wait() {
  local deadline=$(($(date +%s) + chrome_wait_seconds))
  until chrome_answers "$1"; do
    [ "$(date +%s)" -lt "$deadline" ] || return 1
    sleep 0.5
  done
}

# Prints ps lines, in the given ps format, for each Chrome browser process.
# Chrome's helper processes carry the browser's flags too, plus --type=.
# pgrep cannot print the whole command line, which holds the flags.
chrome_processes() {
  # shellcheck disable=SC2009
  ps -axo "$1" | grep -v -- ' --type=' || true
}

# Keeps the lines from stdin that hold one of the given flags whole: preceded
# by a space, and followed by a space or the end of the line. So port 10082
# does not match --remote-debugging-port=100820.
# The flags reach awk through the environment: as arguments, awk would read
# them as its own options, and -v would expand backslashes in a path.
lines_with_flag() {
  CHROME_FLAGS=$(printf '%s\n' "$@") awk '
    BEGIN {
      n = split(ENVIRON["CHROME_FLAGS"], flags, "\n")
      for (f = 1; f <= n; f++) flags[f] = " " flags[f]
    }
    {
      for (f = 1; f <= n; f++) {
        rest = $0
        while ((i = index(rest, flags[f]))) {
          after = substr(rest, i + length(flags[f]), 1)
          if (after == "" || after == " ") { print; next }
          rest = substr(rest, i + length(flags[f]))
        }
      }
    }'
}
