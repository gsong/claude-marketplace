# codex-tools

OpenAI Codex CLI integration for Claude Code — parallel PR reviews and headless task delegation.

## Skills

| Skill          | Trigger                                                                 | Description                                                                                    |
| -------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `codex-review` | "Codex code review", "GPT-based review", `/codex-review`                | Launch 3 parallel Codex agents to review a PR for CLAUDE.md compliance, bugs, and test quality |
| `run-codex`    | "run Codex", "use Codex CLI", "second opinion from Codex", `/run-codex` | Run Codex CLI in headless mode to delegate tasks or get a second opinion                       |

## Prerequisites

- [OpenAI Codex CLI](https://github.com/openai/codex) — the `codex` command must be available in your PATH

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install codex-tools@gsong-marketplace
```
