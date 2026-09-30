---
name: "run"
description: "Assembles a self-contained prompt and delegates it to OpenAI's Codex through the codex:codex-rescue agent. Use when the user asks to run Codex, delegate a task to it, or get its second opinion."
compatibility: "Requires the Codex CLI, reached through the codex:codex-rescue agent."
---

# Run Codex

Delegate tasks to OpenAI's Codex through the codex:codex-rescue agent.

## Process

### 1. Gather parameters

Collect reasoning effort and sandbox mode as `${CLAUDE_PLUGIN_ROOT}/references/codex-prompting.md` describes.

### 2. Get the prompt

If the user's request already contains the task, use it. If absent, use `AskUserQuestion` with a free-form text field to ask what task/prompt to send to Codex. The question should mention the current working directory so the user has context.

### 3. Build the full prompt with context

Build the prompt per `${CLAUDE_PLUGIN_ROOT}/references/codex-prompting.md`; it must be self-contained.

### 4. Delegate to Codex

Dispatch through `Agent(subagent_type: "codex:codex-rescue")` as the reference describes, with `--model gpt-5.6-terra` as a CLI flag.

### 5. Present results

After rescue returns:

- Summarize what Codex found or did
- If Codex proposed code changes, list modified files and evaluate correctness
- If Codex flagged issues, present them clearly
- If rescue returned empty or failed, inform the user and offer to retry
