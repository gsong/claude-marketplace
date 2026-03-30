# ai-docs

Full lifecycle AI documentation for Claude Code projects: bootstrap, lookup, update, check, and audit.

## Skills

| Skill                     | Description                                                         |
| ------------------------- | ------------------------------------------------------------------- |
| `/ai-docs:docs-ai-init`   | Bootstrap `docs-ai/` with auto-populated content from code analysis |
| `/ai-docs:docs-ai-lookup` | Look up project conventions before code changes (read-only, fast)   |
| `/ai-docs:docs-ai-update` | Update specific docs after code changes (targeted, lightweight)     |
| `/ai-docs:docs-ai-check`  | Check documentation freshness and detect drift (read-only)          |
| `/ai-docs:docs-ai-audit`  | Comprehensive audit using coordinated agent teams                   |

## Hooks

| Event              | Behavior                                                                                            |
| ------------------ | --------------------------------------------------------------------------------------------------- |
| `UserPromptSubmit` | Reminds Claude to consult docs-ai-lookup before code changes. Silent when no docs directory exists. |

## Lifecycle

```
docs-ai-init ──creates──▶ docs-ai/
                              │
docs-ai-update ──updates──────┤  (targeted, after code changes)
                              │
docs-ai-audit ──improves──────┤  (comprehensive sweep)
                              │
docs-ai-check ──diagnoses─────┤  (read-only staleness report)
                              │
docs-ai-lookup ◀──reads───────┘  (convention queries)
```

## Path Resolution

All skills and the hook search for docs in this order:

1. `docs-ai/`
2. `docs/ai/`
3. `.claude/docs/`

First match wins. A warning is emitted if multiple directories exist.

## Installation

```
/plugin install ai-docs@gsong-marketplace
```
