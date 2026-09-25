# ai-docs

Full lifecycle AI documentation for Claude Code projects: bootstrap, lookup, update, check, and audit.

## Skills

| Skill             | Description                                                         |
| ----------------- | ------------------------------------------------------------------- |
| `/ai-docs:init`   | Bootstrap `docs-ai/` with auto-populated content from code analysis |
| `/ai-docs:lookup` | Look up project conventions before code changes (read-only, fast)   |
| `/ai-docs:update` | Update specific docs after code changes (targeted, lightweight)     |
| `/ai-docs:check`  | Check documentation freshness and detect drift (read-only)          |
| `/ai-docs:audit`  | Comprehensive audit and cleanup using parallel subagents            |

## Hooks

| Event              | Behavior                                                                                              |
| ------------------ | ----------------------------------------------------------------------------------------------------- |
| `UserPromptSubmit` | Reminds Claude to consult `ai-docs:lookup` before code changes. Silent when no docs directory exists. |

The reminder fires at most once per session (and skips slash commands and very short prompts). When 60% or more of docs still contain `<!-- NEEDS CONTENT` stubs, it instead says most docs need content and suggests populating them before relying on lookups.

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

All skills and the hook recognize these docs directory names, in preference order:

1. `docs-ai/`
2. `docs/ai/`
3. `.claude/docs/`

Skills look for them at the working directory and inside workspace packages, so monorepos
resolve. When several candidates exist, a skill picks by the workspace named in the task, then
by where the changed files are, then by the working directory. It then checks that candidate's
topic index and falls through to the others if the topic is missing. Several docs directories
in a monorepo is normal. A skill warns only when two sit at the same path root. The hook finds
every docs directory up to two levels deep. Its reminder names them all, unless the only one is
`docs-ai/` at the project root.

Full rules: [`resources/docs-dir-resolution.md`](resources/docs-dir-resolution.md).

## Installation

```
/plugin install ai-docs@gsong-marketplace
```
