#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

# Skip slash commands — they handle their own context
[[ "$PROMPT" == /* ]] && exit 0

# Skip if no docs-ai/ directory exists in the project
[[ ! -d "$CLAUDE_PROJECT_DIR/docs-ai" ]] && exit 0

echo 'Before writing or modifying code, use Skill("docs-lookup", "your question") to check project conventions. Skip for: pure conversation, trivial one-line fixes, or topics already looked up this session.'
