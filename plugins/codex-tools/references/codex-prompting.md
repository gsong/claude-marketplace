# Prompting Codex through the rescue runtime

Shared reference for `codex-tools:run` and `codex-tools:discuss`. Both skills dispatch Codex through the `codex:codex-rescue` agent, and both build their prompts the same way.

## Model

Codex picks the model from the user's Codex config. Send no `--model` flag, and do not ask the user to pick a model.

## Parameters to collect

If the user's request already specifies these, use them; only ask for what's missing, via `AskUserQuestion`:

**Reasoning effort** — the level:

- `low` — fast responses
- `medium` — balanced (Recommended)
- `high` — complex problem solving
- `xhigh` — maximum depth

**Sandbox mode** — access level for Codex:

- `read-only` — Codex can only read files (Recommended for review, diagnosis, research, and deliberation)
- `write` — Codex can modify files (for implementation and fix tasks)

## Build a self-contained prompt

**Codex can only access project files in the working directory.** It has no access to external tools, MCP servers, or APIs (Linear, Slack, GitHub issues, Jira, etc.). You MUST inline all relevant external context into the prompt itself.

Before dispatching, gather and embed any context Codex will need:

- **External issue/ticket content**: If the task references a Linear issue, GitHub issue, Jira ticket, etc., fetch the full description, comments, and acceptance criteria yourself, then include them verbatim (or a thorough summary) in the prompt.
- **Conversation context**: If the user discussed requirements, constraints, or decisions earlier in the conversation, summarize the key points in the prompt.
- **API responses / tool output**: If you retrieved data from MCP servers, web searches, or other tools that Codex needs to reason about, paste the relevant content into the prompt.

The prompt Codex receives must be **self-contained** — it should make sense to someone who can only read the prompt text and the project source code, with no other context.

## Dispatch through the rescue agent

All Codex calls go through the Agent tool with `subagent_type: "codex:codex-rescue"`. Pass the assembled prompt as the agent prompt, then:

- If the user chose non-default effort, append `--effort <level>` as a CLI flag
- Sandbox is set through the prompt: for `write`, the rescue agent adds `--write` on its own; for `read-only`, state the read-only intent in the prompt (e.g., "this is a read-only task, no edits")
- For complex or long-running tasks, set `run_in_background: true`
