# codex-tools

OpenAI Codex CLI integration for Claude Code — parallel PR reviews, task delegation, and multi-round consensus discussions via codex:rescue runtime.

## Skills

| Skill                    | Trigger                                                                          | Description                                                                                              |
| ------------------------ | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `gs:codex-tools:discuss` | "discuss with Codex", "reach consensus with Codex", `/gs:codex-tools:discuss`    | Multi-round, two-model dialogue between Claude and Codex toward consensus on a topic                     |
| `gs:codex-tools:review`  | "Codex code review", "GPT-based review", `/gs:codex-tools:review`                | Launch 3 parallel Codex adversarial reviews for a PR — correctness, integration safety, and test quality |
| `gs:codex-tools:run`     | "run Codex", "use Codex CLI", "second opinion from Codex", `/gs:codex-tools:run` | Delegate tasks to Codex via codex:rescue runtime                                                         |

## Prerequisites

- [OpenAI Codex CLI](https://github.com/openai/codex) — the `codex` command must be available in your PATH
- codex plugin — provides the runtime all three skills depend on: review shells out to `node <companion> adversarial-review` (the review engine), while discuss and run dispatch the `codex:codex-rescue` agent. Install from the `openai-codex` marketplace.
- For the review skill only: the [GitHub CLI](https://cli.github.com) (`gh`, authenticated) to fetch PR metadata and diffs, and [uv](https://docs.astral.sh/uv/) to run the findings validator. The validator itself is a symlink into the gh-tools sibling plugin, so the marketplace clone must include the `gh-tools` directory.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install codex-tools@gsong-marketplace
```
