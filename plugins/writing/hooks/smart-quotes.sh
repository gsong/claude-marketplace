#!/usr/bin/env bash
# PreToolUse wrapper for smart-quotes.py. uv is mise-managed and may be missing
# from a non-login PATH. Without it the shebang fails on every publish, so check
# first and stay silent.
command -v uv >/dev/null 2>&1 || exit 0
exec "$(dirname "${BASH_SOURCE[0]}")/smart-quotes.py"
