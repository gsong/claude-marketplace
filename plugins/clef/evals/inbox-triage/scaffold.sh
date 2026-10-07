#!/usr/bin/env bash
# The input is prose in the prompt, so this case has no fixture to copy.
set -euo pipefail
# The eval sandbox puts a .git in the run's home directory, above this one.
# Make this directory the git root, so the record lands where the graders look.
git init --quiet .
# A grader reads a file by a fixed path, but the record's name holds the run's
# date. This link gives the graders a fixed path to the record.
ln -s "clef-opportunities/inbox-triage-$(date +%F).md" .eval-record.md
