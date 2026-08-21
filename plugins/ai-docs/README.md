# ai-docs

Full lifecycle AI documentation for Claude Code projects: bootstrap, lookup, update, check, and audit.

## Skills

| Skill                | Description                                                         |
| -------------------- | ------------------------------------------------------------------- |
| `/gs:ai-docs:init`   | Bootstrap `docs-ai/` with auto-populated content from code analysis |
| `/gs:ai-docs:lookup` | Look up project conventions before code changes (read-only, fast)   |
| `/gs:ai-docs:update` | Update specific docs after code changes (targeted, lightweight)     |
| `/gs:ai-docs:check`  | Check documentation freshness and detect drift (read-only)          |
| `/gs:ai-docs:audit`  | Comprehensive audit using coordinated agent teams                   |

## Hooks

| Event              | Behavior                                                                                                 |
| ------------------ | -------------------------------------------------------------------------------------------------------- |
| `UserPromptSubmit` | Reminds Claude to consult `gs:ai-docs:lookup` before code changes. Silent when no docs directory exists. |

## Lifecycle

```
init ──creates──▶ docs-ai/
                       │
update ──updates───────┤  (targeted, after code changes)
                       │
audit ──improves───────┤  (comprehensive sweep)
                       │
check ──diagnoses──────┤  (read-only staleness report)
                       │
lookup ◀──reads────────┘  (convention queries)
```

## Verification Stamp

Every generated doc starts with `<!-- verified-against: [full-commit-sha] -->`. The stamp
records the commit the doc was last generated or verified against. `init`, `update`, and
`audit` write it; `check` and `lookup` use it as the staleness baseline, with the doc's git
timestamp as fallback for unstamped docs.

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
