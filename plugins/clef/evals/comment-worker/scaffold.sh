#!/usr/bin/env bash
# Copy the fixture into the run's working directory.
set -euo pipefail
# The eval sandbox puts a .git in the run's home directory, above this one.
# Make this directory the git root, so the record lands where the graders look.
git init --quiet .
case_dir=$(cd "$(dirname "$0")" && pwd)
cp -R "$case_dir/fixture/." .
# A grader reads a file by a fixed path, but the record's name holds the run's
# date. This link gives the graders a fixed path to the record.
ln -s "clef-opportunities/moderate-comments-$(date +%F).md" .eval-record.md
