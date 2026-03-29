---
name: run-codex
description: Use when the user asks to run Codex, use Codex CLI, get a second opinion from Codex, or delegate a task to OpenAI's Codex agent. Also use when the user invokes /run-codex.
---

# Run Codex CLI

Run OpenAI's Codex CLI in headless mode (`codex exec`) from within Claude Code.

## Process

### 1. Gather parameters

Use `AskUserQuestion` to collect:

**Reasoning effort** — ask the level:

- `low` — fast responses
- `medium` — balanced (Recommended)
- `high` — complex problem solving
- `xhigh` — maximum depth

**Sandbox mode** — ask the access level:

- `read-only` — can only read files (Recommended)
- `workspace-write` — can write to workspace
- `danger-full-access` — unrestricted (use with caution)

### 2. Get the prompt

Use `AskUserQuestion` with a free-form text field to ask what task/prompt to send to Codex. The question should mention the current working directory so the user has context.

### 3. Build the full prompt with context

**Codex can only access project files in the working directory.** It has no access to external tools, MCP servers, or APIs (Linear, Slack, GitHub issues, Jira, etc.). You MUST inline all relevant external context into the prompt itself.

Before executing, gather and embed any context Codex will need:

- **External issue/ticket content**: If the task references a Linear issue, GitHub issue, Jira ticket, etc., fetch the full description, comments, and acceptance criteria yourself, then include them verbatim (or a thorough summary) in the prompt.
- **Conversation context**: If the user discussed requirements, constraints, or decisions earlier in the conversation, summarize the key points in the prompt.
- **API responses / tool output**: If you retrieved data from MCP servers, web searches, or other tools that Codex needs to reason about, paste the relevant content into the prompt.

The prompt Codex receives should be **self-contained** — it should make sense to someone who can only read the prompt text and the project source code, with no other context.

### 4. Execute

Run via Bash:

```
codex exec -m gpt-5.4 -c model_reasoning_effort="<level>" -s <sandbox> --ephemeral "<prompt>"
```

Key flags:

- `-m` sets the model
- `-s` sets sandbox policy
- `--ephemeral` prevents session persistence to disk
- The prompt should be shell-escaped properly

### 5. Interpret results

Use the `Agent` tool to analyze the Codex output in context. The subagent should:

- Read the Codex output and any files it referenced or modified
- Compare Codex's suggestions against the actual codebase
- Summarize findings: what Codex found, whether its suggestions are valid, and any caveats
- If Codex proposed code changes, evaluate correctness and highlight anything questionable

This gives the user a synthesized view rather than raw output.
