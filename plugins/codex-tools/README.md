# codex-tools

OpenAI Codex CLI integration for Claude Code — parallel PR reviews and task delegation via codex:rescue runtime.

## Skills

| Skill                   | Trigger                                                                          | Description                                                                                              |
| ----------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `gs:codex-tools:review` | "Codex code review", "GPT-based review", `/gs:codex-tools:review`                | Launch 3 parallel Codex adversarial reviews for a PR — correctness, integration safety, and test quality |
| `gs:codex-tools:run`    | "run Codex", "use Codex CLI", "second opinion from Codex", `/gs:codex-tools:run` | Delegate tasks to Codex via codex:rescue runtime                                                         |

## Prerequisites

- [OpenAI Codex CLI](https://github.com/openai/codex) — the `codex` command must be available in your PATH
- codex plugin — the `codex:adversarial-review` command must be installed (provides the review engine). Install from the `openai-codex` marketplace.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install codex-tools@gsong-marketplace
```
