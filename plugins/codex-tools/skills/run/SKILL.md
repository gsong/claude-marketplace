---
name: gs:codex-tools:run
description: Use when the user asks to run Codex, use Codex CLI, get a second opinion from Codex, or delegate a task to OpenAI's Codex agent. Also use when the user invokes /gs:codex-tools:run.
---

# Run Codex

Delegate tasks to OpenAI's Codex agent through the codex:rescue runtime.

## Process

### 1. Gather parameters

Use `AskUserQuestion` to collect:

**Model** — ask which Codex model to use:

- `gpt-5.5` — frontier model for complex work (Recommended)
- `gpt-5.4` — everyday coding

**Reasoning effort** — ask the level:

- `low` — fast responses
- `medium` — balanced (Recommended)
- `high` — complex problem solving
- `xhigh` — maximum depth

**Sandbox mode** — ask the access level:

- `read-only` — Codex can only read files (Recommended for review/diagnosis/research)
- `write` — Codex can modify files (for implementation/fix tasks)

### 2. Get the prompt

Use `AskUserQuestion` with a free-form text field to ask what task/prompt to send to Codex. The question should mention the current working directory so the user has context.

### 3. Build the full prompt with context

**Codex can only access project files in the working directory.** It has no access to external tools, MCP servers, or APIs (Linear, Slack, GitHub issues, Jira, etc.). You MUST inline all relevant external context into the prompt itself.

Before executing, gather and embed any context Codex will need:

- **External issue/ticket content**: If the task references a Linear issue, GitHub issue, Jira ticket, etc., fetch the full description, comments, and acceptance criteria yourself, then include them verbatim (or a thorough summary) in the prompt.
- **Conversation context**: If the user discussed requirements, constraints, or decisions earlier in the conversation, summarize the key points in the prompt.
- **API responses / tool output**: If you retrieved data from MCP servers, web searches, or other tools that Codex needs to reason about, paste the relevant content into the prompt.

The prompt Codex receives should be **self-contained** — it should make sense to someone who can only read the prompt text and the project source code, with no other context.

### 4. Delegate to Codex

Use the Agent tool to hand the task to Codex:

- Set `subagent_type` to `"codex:codex-rescue"`
- Pass the assembled self-contained prompt as the agent prompt
- Append `--model <slug>` as a CLI flag matching the user's choice (not in the prompt text — rescue passes it through to the companion script's argument parser)
- If the user chose non-default effort, append `--effort <level>` as a CLI flag
- If the user chose `write` sandbox mode, the rescue agent adds `--write` by default — no action needed
- If the user chose `read-only`, clearly state the read-only intent in the prompt (e.g., "this is a read-only task, no edits") so rescue omits `--write`
- For complex or long-running tasks, set `run_in_background: true`

Do NOT shell out to `codex exec` directly.

### 5. Present results

After rescue returns:

- Summarize what Codex found or did
- If Codex proposed code changes, list modified files and evaluate correctness
- If Codex flagged issues, present them clearly
- If rescue returned empty or failed, inform the user and offer to retry
