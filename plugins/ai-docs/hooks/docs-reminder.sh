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

# Find docs directories. A monorepo keeps them per workspace (apps/woody/docs-ai), so
# searching only the project root would stay silent in exactly the repos that need the
# reminder most. Walk two levels, skipping directories that never hold project docs.
DOCS_DIRS=()

collect_at() {
  local base=$1
  local candidate
  for candidate in "$base/docs-ai" "$base/docs/ai" "$base/.claude/docs"; do
    if [[ -d "$candidate" ]]; then
      DOCS_DIRS+=("$candidate")
    fi
  done
  return 0
}

# True when the directory is worth descending into. Named positively so callers can write
# `searchable || continue` — under `set -e`, a bare `cmd && continue` that fails exits the hook.
searchable() {
  case "$(basename "$1")" in
    node_modules | vendor | dist | build | target | .git | .venv | .next | .turbo | .cache) return 1 ;;
    *) return 0 ;;
  esac
}

collect_at "$CLAUDE_PROJECT_DIR"
for lvl1 in "$CLAUDE_PROJECT_DIR"/*; do
  [[ -d "$lvl1" ]] || continue
  searchable "$lvl1" || continue
  collect_at "$lvl1"
  for lvl2 in "$lvl1"/*; do
    [[ -d "$lvl2" ]] || continue
    searchable "$lvl2" || continue
    collect_at "$lvl2"
  done
done

# No docs directory found — stay silent
[[ ${#DOCS_DIRS[@]} -eq 0 ]] && exit 0

# Name the locations unless the only one is the conventional project-root docs-ai/, so
# lookup can resolve a per-workspace directory without searching for it.
LOCATIONS=""
if [[ ${#DOCS_DIRS[@]} -gt 1 || ${DOCS_DIRS[0]} != "$CLAUDE_PROJECT_DIR/docs-ai" ]]; then
  REL=()
  for d in "${DOCS_DIRS[@]}"; do
    REL+=("${d#"$CLAUDE_PROJECT_DIR"/}")
  done
  LOCATIONS=" Docs live in: ${REL[*]}."
fi

# Check if most docs are stubs (NEEDS CONTENT markers)
TOTAL_DOCS=0
STUB_DOCS=0
for d in "${DOCS_DIRS[@]}"; do
  for f in "$d"/*.md; do
    [[ "$(basename "$f")" == "README.md" ]] && continue
    [[ "$(basename "$f")" == "quick-reference.md" ]] && continue
    [[ -f "$f" ]] || continue
    TOTAL_DOCS=$((TOTAL_DOCS + 1))
    if grep -q '<!-- NEEDS CONTENT' "$f" 2>/dev/null; then
      STUB_DOCS=$((STUB_DOCS + 1))
    fi
  done
done

# If most docs are stubs, suggest populating first
if [[ $TOTAL_DOCS -gt 0 && $STUB_DOCS -gt 0 ]]; then
  STUB_RATIO=$((STUB_DOCS * 100 / TOTAL_DOCS))
  if [[ $STUB_RATIO -ge 60 ]]; then
    touch "$COOLDOWN_FILE"
    echo "Docs exist but most need content.${LOCATIONS} Consider running /gs:ai-docs:update or editing docs manually before relying on lookups."
    exit 0
  fi
fi

# Mark cooldown so we don't remind again this session
touch "$COOLDOWN_FILE"

echo "Before writing or modifying code, use Skill(\"gs:ai-docs:lookup\", \"your question\") to check project conventions.${LOCATIONS} Skip for: conversation, trivial fixes, topics already looked up this session, or git/shell operations."
