# shellcheck shell=bash
# Answers the Chrome questions that browser-start, scratch-chrome and ports
# share. Each script sources this file and keeps only its own decisions.

# How long chrome_wait waits for Chrome to answer, in seconds.
chrome_wait_seconds=${CHROME_WAIT_SECONDS:-15}

# Succeeds when Chrome's DevTools endpoint answers on the port.
chrome_answers() {
  curl -sf --max-time 1 "http://127.0.0.1:$1/json/version" >/dev/null
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
