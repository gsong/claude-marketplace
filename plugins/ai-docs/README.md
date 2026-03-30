# ai-docs

AI documentation bootstrapping and review for Claude Code projects.

## Skills

| Skill                     | Description                                                     |
| ------------------------- | --------------------------------------------------------------- |
| `/ai-docs:init-docs-ai`   | Bootstrap a `docs-ai/` directory for AI-optimized documentation |
| `/ai-docs:review-docs-ai` | Review documentation using coordinated agent teams              |
| `/ai-docs:docs-lookup`    | Look up project conventions from docs-ai/ before code changes   |

## Hooks

| Event              | Behavior                                                                                     |
| ------------------ | -------------------------------------------------------------------------------------------- |
| `UserPromptSubmit` | Reminds Claude to consult docs-lookup before code changes. Silent when no `docs-ai/` exists. |

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install ai-docs@gsong-marketplace
```
