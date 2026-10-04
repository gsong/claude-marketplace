# codex-tools

OpenAI Codex CLI integration for Claude Code — parallel PR reviews, task delegation, and multi-round consensus discussions via the codex plugin.

## Skills

| Skill                 | Invoked by                                                                        | Description                                                                                                                   |
| --------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `codex-tools:discuss` | "discuss with Codex", "reach consensus with Codex", `/codex-tools:discuss`        | Multi-round, two-model dialogue between Claude and Codex toward consensus on a topic; writes consensus.md                     |
| `codex-tools:review`  | you, `/codex-tools:review <pr>`                                                   | Review a PR with 3 parallel Codex adversarial reviews (correctness, integration, tests); write findings for `gh-tools:triage` |
| `codex-tools:run`     | "run Codex", "delegate to Codex", "second opinion from Codex", `/codex-tools:run` | Delegate a task to Codex with a self-contained prompt through the codex:codex-rescue agent                                    |

`run` and `discuss` share `references/codex-prompting.md`: the model rule, the effort and sandbox menus, how to inline external context, and how to dispatch through `codex:codex-rescue`.

## Prerequisites

- [OpenAI Codex CLI](https://github.com/openai/codex) — the `codex` command must be available in your PATH
- codex plugin — provides the runtime all three skills depend on: review shells out to `node <companion> adversarial-review` (the review engine), while discuss and run dispatch the `codex:codex-rescue` agent. codex-tools declares it as a dependency, so installing codex-tools also installs `codex` from the `openai-codex` marketplace when it is missing. Add that marketplace first (see [Installation](#installation)); without it, codex-tools installs but fails to load.
- For the review skill only: the [GitHub CLI](https://cli.github.com) (`gh`, authenticated) to fetch PR metadata and linked issues and check out the PR branch, and [uv](https://docs.astral.sh/uv/) to run the findings validator. The validator itself is a symlink into the gh-tools sibling plugin, so the marketplace clone must include the `gh-tools` directory.

## Installation

```
/plugin marketplace add openai/codex-plugin-cc
/plugin marketplace add gsong/claude-marketplace
/plugin install codex-tools@gsong-marketplace
```
