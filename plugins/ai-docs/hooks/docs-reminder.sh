#!/bin/bash
set -euo pipefail

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

# Skip slash commands — they handle their own context
[[ "$PROMPT" == /* ]] && exit 0

# Skip very short prompts (greetings, acknowledgements)
[[ ${#PROMPT} -lt 10 ]] && exit 0

# Session cooldown — only remind once per session
# Use PPID (Claude Code process) as session identifier
COOLDOWN_FILE="${TMPDIR:-/tmp}/docs-ai-reminder-${PPID}"
if [[ -f "$COOLDOWN_FILE" ]]; then
  exit 0
fi

# Find docs directory — first match wins
DOCS_DIR=""
FOUND_DIRS=()
for candidate in "$CLAUDE_PROJECT_DIR/docs-ai" "$CLAUDE_PROJECT_DIR/docs/ai" "$CLAUDE_PROJECT_DIR/.claude/docs"; do
  if [[ -d "$candidate" ]]; then
    FOUND_DIRS+=("$candidate")
    [[ -z "$DOCS_DIR" ]] && DOCS_DIR="$candidate"
  fi
done

# No docs directory found — stay silent
[[ -z "$DOCS_DIR" ]] && exit 0

# Warn if multiple roots found
WARNING=""
if [[ ${#FOUND_DIRS[@]} -gt 1 ]]; then
  WARNING="Note: Multiple docs directories found: ${FOUND_DIRS[*]}. Using $DOCS_DIR."$'\n'
fi

# Check if most docs are stubs (NEEDS CONTENT markers)
TOTAL_DOCS=0
STUB_DOCS=0
for f in "$DOCS_DIR"/*.md; do
  [[ "$(basename "$f")" == "README.md" ]] && continue
  [[ "$(basename "$f")" == "quick-reference.md" ]] && continue
  [[ -f "$f" ]] || continue
  TOTAL_DOCS=$((TOTAL_DOCS + 1))
  if grep -q '<!-- NEEDS CONTENT' "$f" 2>/dev/null; then
    STUB_DOCS=$((STUB_DOCS + 1))
  fi
done

# If most docs are stubs, suggest populating first
if [[ $TOTAL_DOCS -gt 0 && $STUB_DOCS -gt 0 ]]; then
  STUB_RATIO=$((STUB_DOCS * 100 / TOTAL_DOCS))
  if [[ $STUB_RATIO -ge 60 ]]; then
    touch "$COOLDOWN_FILE"
    echo "${WARNING}docs-ai/ exists but most docs need content. Consider running /gs:ai-docs:update or editing docs manually before relying on lookups."
    exit 0
  fi
fi

# Mark cooldown so we don't remind again this session
touch "$COOLDOWN_FILE"

echo "${WARNING}Before writing or modifying code, use Skill(\"gs:ai-docs:lookup\", \"your question\") to check project conventions. Skip for: conversation, trivial fixes, topics already looked up this session, or git/shell operations."
