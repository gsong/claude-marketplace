#!/usr/bin/env bash
# Scan the skills for security risks with Cisco skill-scanner. Run it through
# `mise run scan:skills`, which installs the scanner. Pass a path to also write
# a SARIF report.
set -euo pipefail

report=()
if [[ $# -gt 0 ]]; then
  out=$1
  if [[ $out != /* ]]; then out=${MISE_ORIGINAL_CWD:-$PWD}/$out; fi
  report=(--format sarif --output-sarif "$out")
fi
policy=$PWD/skill-scanner-policy.yaml

# Scan a copy that holds only the files git tracks or does not ignore. The
# scanner reads ignored files such as __pycache__, which a CI checkout does
# not have, and reports their bytecode as critical.
copy=$(mktemp -d)
trap 'rm -rf "$copy"' EXIT
git ls-files -z --cached --others --exclude-standard plugins .claude/skills |
  while IFS= read -r -d '' f; do if [[ -e $f ]]; then printf '%s\0' "$f"; fi; done |
  tar --null -T - -cf - | tar -xf - -C "$copy"

# SARIF paths are relative to the working directory, so scan from the copy's root.
cd "$copy"
skill-scanner scan-all . --recursive --policy "$policy" \
  --fail-on-severity high --format summary ${report[@]+"${report[@]}"}
