# codex-tools

OpenAI Codex CLI integration for Claude Code — parallel PR reviews, task delegation, and multi-round consensus discussions via the codex plugin.

## Skills

| Skill                 | Invoked by                                                                        | Description                                                                                                                   |
| --------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `codex-tools:discuss` | "discuss with Codex", "reach consensus with Codex", `/codex-tools:discuss`        | Multi-round, two-model dialogue between Claude and Codex toward consensus on a topic; writes consensus.md                     |
| `codex-tools:review`  | you, `/codex-tools:review <pr>`                                                   | Review a PR with 3 parallel Codex adversarial reviews (correctness, integration, tests); write findings for `gh-tools:triage` |
| `codex-tools:run`     | "run Codex", "delegate to Codex", "second opinion from Codex", `/codex-tools:run` | Delegate a task to Codex with a self-contained prompt via the codex:rescue runtime                                            |

`run` and `discuss` share `references/codex-prompting.md`: the model pin, the effort and sandbox menus, how to inline external context, and how to dispatch through `codex:codex-rescue`.

## Prerequisites

- [OpenAI Codex CLI](https://github.com/openai/codex) — the `codex` command must be available in your PATH
- codex plugin — provides the runtime all three skills depend on: review shells out to `node <companion> adversarial-review` (the review engine), while discuss and run dispatch the `codex:codex-rescue` agent. Install from the `openai-codex` marketplace.
- For the review skill only: the [GitHub CLI](https://cli.github.com) (`gh`, authenticated) to fetch PR metadata and diffs, and [uv](https://docs.astral.sh/uv/) to run the findings validator. The validator itself is a symlink into the gh-tools sibling plugin, so the marketplace clone must include the `gh-tools` directory.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install codex-tools@gsong-marketplace
```
