# codex-tools

OpenAI Codex CLI integration for Claude Code — parallel PR reviews and headless task delegation.

## Skills

| Skill                   | Trigger                                                                          | Description                                                                                              |
| ----------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `gs:codex-tools:review` | "Codex code review", "GPT-based review", `/gs:codex-tools:review`                | Launch 3 parallel Codex adversarial reviews for a PR — correctness, integration safety, and test quality |
| `gs:codex-tools:run`    | "run Codex", "use Codex CLI", "second opinion from Codex", `/gs:codex-tools:run` | Run Codex CLI in headless mode to delegate tasks or get a second opinion                                 |

## Prerequisites

- [OpenAI Codex CLI](https://github.com/openai/codex) — the `codex` command must be available in your PATH
- codex plugin — the `codex:adversarial-review` command must be installed (provides the review engine). Install from the `openai-codex` marketplace.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install codex-tools@gsong-marketplace
```
